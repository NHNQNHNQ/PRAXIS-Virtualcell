"""5 个 md ASGI handler。

挂在 server/app.py 的静态 _routes 和动态 dispatch:
- POST /api/md/submit                       handle_md_submit
- GET  /api/md/runs                         handle_md_runs
- GET  /api/md/jobs/{job_id}                handle_md_get
- POST /api/md/jobs/{job_id}/cancel         handle_md_cancel
- GET  /api/md/gpu-pool                     handle_md_gpu_pool
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from praxis2.md import local_runner
from praxis2.md.gpu_pool import fetch_gpu_pool
from praxis2.md.sbatch import render_sbatch
from praxis2.md.sim_params import validate_sim_params
from praxis2.md.ssh import ssh_run, ssh_write_file

log = logging.getLogger(__name__)


async def _json(send, status: int, body: dict) -> None:
    data = json.dumps(body, ensure_ascii=False, default=str).encode()
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json; charset=utf-8")]})
    await send({"type": "http.response.body", "body": data})


async def _read_body(receive) -> dict:
    chunks = b""
    while True:
        msg = await receive()
        chunks += msg.get("body", b"")
        if not msg.get("more_body"):
            break
    if not chunks:
        return {}
    try:
        return json.loads(chunks)
    except ValueError:
        return {}


def _require_user(scope) -> tuple[str, Any]:
    user = scope.get("user")
    if not user:
        return ("unauthorized", None)
    return ("ok", user)


async def _read_file_to_bytes(fs_store, user_id: str, storage_fid: str) -> bytes:
    """聚合 fs_store.read_stream 流为整 bytes。MD input 一般 <10MB,内存可承受。
    storage_fid 是 files.storage_key 解析后 `fs:{uid}/{fid}` 的 fid 部分,跟 DB id 不同。
    """
    chunks: list[bytes] = []
    async for chunk in fs_store.read_stream(user_id, storage_fid):
        chunks.append(chunk)
    return b"".join(chunks)


def _storage_fid(file_meta: dict) -> str | None:
    """从 files 行的 storage_key 'fs:{uid}/{storage_fid}' 拆 storage_fid."""
    storage_key = file_meta.get("storage_key", "") or ""
    if not storage_key.startswith("fs:"):
        return None
    _, _, storage_fid = storage_key[3:].partition("/")
    return storage_fid or None


_REQUIRED_TOP_FIELDS = [
    "structure_file_id", "force_field", "water_model", "ensemble",
    "temperature_k", "time_ns", "timestep_fs",
]


async def handle_md_submit(scope, receive, send, deps) -> None:
    status, user = _require_user(scope)
    if status != "ok":
        await _json(send, 401, {"error": "unauthorized"})
        return

    body = await _read_body(receive)
    sim_type = body.get("sim_type") or "standard"
    sim_params = body.get("sim_params") or {}

    # 顶级字段必填
    for f in _REQUIRED_TOP_FIELDS:
        if f not in body:
            await _json(send, 400, {"error": "missing_field", "field": f})
            return

    # sim_type 必填校验
    err = validate_sim_params(sim_type, sim_params)
    if err:
        if err == "unsupported_sim_type":
            await _json(send, 400, {"error": "unsupported_sim_type",
                                    "sim_type": sim_type})
        elif err.startswith("missing: "):
            await _json(send, 400, {"error": "missing_sim_param",
                                    "field": err[len("missing: "):]})
        else:
            await _json(send, 400, {"error": "bad_sim_param",
                                    "field": err[len("type: "):]})
        return

    user_id = user["user_id"]
    repo = deps["md_repo"]

    # concurrent 限
    active = await repo.count_active(user_id)
    if active >= deps["max_concurrent_per_user"]:
        await _json(send, 429, {"error": "too_many_active",
                                "active": active,
                                "limit": deps["max_concurrent_per_user"]})
        return

    # quota 预检
    async with deps["pg_pool"].acquire() as conn:
        bal = await conn.fetchval(
            "SELECT balance_li FROM users WHERE id=$1", uuid.UUID(user_id),
        )
    if bal is None or bal <= 0:
        await _json(send, 402, {"error": "insufficient_balance", "balance": bal})
        return

    # 拉 structure 文件
    files_repo = deps["files_repo"]
    structure_fid = body["structure_file_id"]
    file_meta = await files_repo.get(structure_fid)
    if file_meta is None or str(file_meta["user_id"]) != user_id:
        await _json(send, 404, {"error": "structure_file_not_found"})
        return
    structure_storage_fid = _storage_fid(file_meta)
    if not structure_storage_fid:
        await _json(send, 500, {"error": "invalid_storage_key", "file_id": structure_fid})
        return
    structure_bytes = await _read_file_to_bytes(
        deps["fs_store"], user_id, structure_storage_fid,
    )

    plumed_bytes: bytes | None = None
    if sim_type == "metadynamics":
        pf_id = sim_params["plumed_file_id"]
        pf_meta = await files_repo.get(pf_id)
        if pf_meta is None or str(pf_meta["user_id"]) != user_id:
            await _json(send, 404, {"error": "plumed_file_not_found"})
            return
        plumed_storage_fid = _storage_fid(pf_meta)
        if not plumed_storage_fid:
            await _json(send, 500, {"error": "invalid_storage_key", "file_id": pf_id})
            return
        plumed_bytes = await _read_file_to_bytes(
            deps["fs_store"], user_id, plumed_storage_fid,
        )

    # 组 params
    params = {f: body[f] for f in _REQUIRED_TOP_FIELDS}
    params["notes"] = body.get("notes", "")
    params["sim_params"] = sim_params
    params["structure_file_id"] = structure_fid

    # 创 PG row
    async with deps["pg_pool"].acquire() as conn:
        job_id = await repo.create(conn, user_id, sim_type, params)

    # ssh 走全套 stage + sbatch
    cfg = deps["ssh_cfg"]
    # 绝对路径:asyncssh SFTP 不展开 ~ (protocol-level 字面 char),只能 /home/{user}/...
    work_dir = f"/home/{cfg.user}/praxis-md/{job_id}"
    account = deps["hpc_account"]
    plumed_load_cmd = deps.get("md_plumed_load_cmd", "")
    mpi_load_cmd = deps.get("md_mpi_load_cmd", "")

    try:
        await ssh_run(cfg, f"mkdir -p {work_dir}")
        await ssh_write_file(cfg, f"{work_dir}/input.pdb", structure_bytes)
        if plumed_bytes is not None:
            # gmx mdrun -plumed 要求 .dat 扩展名(见 sbatch._build_extra_mdrun)
            await ssh_write_file(cfg, f"{work_dir}/plumed.dat", plumed_bytes)
        script = render_sbatch(
            sim_type=sim_type, params=params, sim_params=sim_params,
            work_dir=work_dir, account=account,
            gromacs_load_cmd=deps["md_gromacs_load_cmd"],
            plumed_load_cmd=plumed_load_cmd or deps["md_gromacs_load_cmd"],
            mpi_load_cmd=mpi_load_cmd or deps["md_gromacs_load_cmd"],
        )
        # 本地执行:nohup bash job.sh,不用 sbatch
        pid = await local_runner.submit(cfg, work_dir, script.encode())
    except Exception as exc:  # noqa: BLE001
        log.exception("md submit local runner failed")
        await repo.update_cancelled(job_id)
        await _json(send, 502, {"error": "hpc_unreachable", "reason": repr(exc)[:300]})
        return

    local_job_id = f"local:{pid}"
    await repo.update_submitted(job_id, slurm_job_id=local_job_id)

    await _json(send, 200, {"id": job_id, "status": "queued",
                            "local_pid": pid, "work_dir": work_dir})


async def handle_md_runs(scope, receive, send, deps) -> None:
    status, user = _require_user(scope)
    if status != "ok":
        await _json(send, 401, {"error": "unauthorized"})
        return
    rows = await deps["md_repo"].list_recent(user["user_id"], limit=100)
    await _json(send, 200, {"runs": rows})


async def handle_md_get(scope, receive, send, deps) -> None:
    status, user = _require_user(scope)
    if status != "ok":
        await _json(send, 401, {"error": "unauthorized"})
        return
    job_id = scope.get("path_params", {}).get("job_id", "")
    if not job_id:
        await _json(send, 400, {"error": "missing_job_id"})
        return
    row = await deps["md_repo"].get(job_id)
    if row is None:
        await _json(send, 404, {"error": "not_found"})
        return
    if row["user_id"] != user["user_id"] and user.get("role") != "admin":
        await _json(send, 404, {"error": "not_found"})
        return
    await _json(send, 200, row)


async def handle_md_cancel(scope, receive, send, deps) -> None:
    status, user = _require_user(scope)
    if status != "ok":
        await _json(send, 401, {"error": "unauthorized"})
        return
    job_id = scope.get("path_params", {}).get("job_id", "")
    if not job_id:
        await _json(send, 400, {"error": "missing_job_id"})
        return
    repo = deps["md_repo"]
    row = await repo.get(job_id)
    if row is None or (row["user_id"] != user["user_id"]
                       and user.get("role") != "admin"):
        await _json(send, 404, {"error": "not_found"})
        return
    if row["status"] not in ("queued", "running"):
        await _json(send, 409, {"error": "not_active", "status": row["status"]})
        return

    if row["slurm_job_id"]:
        pid = local_runner.parse_local_job_id(row["slurm_job_id"])
        if pid:
            try:
                # setsid 后 job.sh 是进程组 leader,负 PID 杀整组(含 mdrun 子进程);
                # 回退单 PID kill。.53 无 SLURM,不用 scancel。
                await ssh_run(
                    deps["ssh_cfg"],
                    f"kill -TERM -- -{pid} 2>/dev/null || "
                    f"kill -TERM {pid} 2>/dev/null || true",
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("kill local job %s failed: %s", pid, exc)
    await repo.update_cancelled(job_id)
    await _json(send, 200, {"ok": True})


async def handle_md_gpu_pool(scope, receive, send, deps) -> None:
    status, user = _require_user(scope)
    if status != "ok":
        await _json(send, 401, {"error": "unauthorized"})
        return
    pool = await fetch_gpu_pool(
        cfg=deps["ssh_cfg"], script_path=deps["check_gpus_script_path"],
    )
    await _json(send, 200, pool)
