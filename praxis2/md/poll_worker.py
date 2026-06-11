"""后台 30s 轮询 worker — 检查本地 PID 状态 + ledger 扣费。

local: 前缀(LocalJobRunner):检查 job.status sentinel 文件 / PID 存活。
SLURM 路径已弃用(.53 无 squeue),保留函数签名兼容性但路由到 local_runner。
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from praxis2.accounting.ledger import Ledger
from praxis2.md import local_runner as _lr
from praxis2.md.pricing import compute_md_cost_li
from praxis2.md.repo import MdJobRepo

if TYPE_CHECKING:
    from praxis2.md.ssh import SshConfig

log = logging.getLogger(__name__)


async def run_poll_loop(
    *, cfg: SshConfig, repo: MdJobRepo, ledger: Ledger, pg_pool,
    interval_s: int, free_cpu_h: float,
    price_gpu: int, price_cpu: int,
) -> None:
    """无限循环,每 interval_s 跑一次 poll_tick。任何异常 log 不退出。"""
    while True:
        try:
            await poll_tick(
                cfg=cfg, repo=repo, ledger=ledger, pg_pool=pg_pool,
                free_cpu_h=free_cpu_h,
                price_gpu=price_gpu, price_cpu=price_cpu,
            )
        except Exception:  # noqa: BLE001
            log.exception("poll_tick failed")
        await asyncio.sleep(interval_s)


async def poll_tick(
    *, cfg: SshConfig, repo: MdJobRepo, ledger: Ledger, pg_pool,
    free_cpu_h: float, price_gpu: int, price_cpu: int,
) -> None:
    """单次扫描所有 active jobs,更新状态或 finalize。"""
    active = await repo.list_active()
    if not active:
        return

    for job in active:
        sid = job.get("slurm_job_id") or ""
        pid = _lr.parse_local_job_id(sid)
        if pid is None:
            log.warning("job %s has non-local slurm_job_id %r, skipping", job["id"], sid)
            continue
        await _poll_local_job(cfg, repo, ledger, pg_pool, job, pid,
                              free_cpu_h, price_gpu, price_cpu)


async def _poll_local_job(
    cfg: SshConfig, repo: MdJobRepo, ledger: Ledger, pg_pool,
    job: dict, pid: str,
    free_cpu_h: float, price_gpu: int, price_cpu: int,
) -> None:
    """轮询单个 local 任务。"""
    job_id = job["id"]
    work_dir = f"/home/{cfg.user}/praxis-md/{job_id}"

    try:
        status = await _lr.poll_status(cfg, work_dir, pid)
    except Exception as exc:  # noqa: BLE001
        log.warning("poll_status failed for job %s: %s", job_id, exc)
        return

    if status == "running" and job["status"] != "running":
        await repo.update_status(job_id, "running", gpu_host=cfg.host)
        return

    if status in ("done", "failed", "cancelled"):
        # 从 work_dir/mdrun.log 估算运行时间
        elapsed_s = await _estimate_elapsed(cfg, work_dir)
        gpu_h = elapsed_s / 3600.0
        cpu_h = (18 * elapsed_s) / 3600.0  # 18 线程

        if status == "done":
            cost = compute_md_cost_li(gpu_h, cpu_h, free_cpu_h, price_gpu, price_cpu)
            err = None
        else:
            cost = 0
            err = f"local_{status}"

        async with pg_pool.acquire() as conn:
            async with conn.transaction():
                await repo.finalize(
                    conn, job_id, status=status,
                    cpu_hours=cpu_h, gpu_hours=gpu_h, cost_li=cost, error=err,
                )
                if cost > 0:
                    await ledger.record(
                        conn, job["user_id"], -cost,
                        kind="md_consume", ref_type="md_job", ref_id=job_id,
                        meta={"gpu_hours": gpu_h, "cpu_hours": cpu_h},
                    )
        log.info("job %s finalized: %s (cost %d li)", job_id, status, cost)


async def _estimate_elapsed(cfg: SshConfig, work_dir: str) -> int:
    """从 stdout.log 或 mdrun.log 的时间戳估算 wall time(秒)。简化实现。"""
    from praxis2.md.ssh import ssh_run as _ssh_run  # noqa: PLC0415
    try:
        # 读 job.pid mtime 与当前时间差(粗估)
        out = await _ssh_run(
            cfg,
            f"[ -f {work_dir}/job.pid ] && "
            f"echo $(($(date +%s) - $(stat -c %Y {work_dir}/job.pid 2>/dev/null || echo $(date +%s)))) "
            f"|| echo 0",
        )
        return max(0, int(out.strip()))
    except Exception:  # noqa: BLE001
        return 0


# ---- 保留 SLURM 解析函数(已不走主路径,维持旧测试兼容) ----

def _parse_scontrol(out: str, slurm_id: str) -> "tuple[str, int, int, int] | None":
    if not out or not out.strip():
        return None
    d: dict[str, str] = {}
    for line in out.strip().splitlines():
        for token in line.split():
            if "=" in token:
                k, v = token.split("=", 1)
                d[k] = v
    if not d.get("JobId", "").startswith(slurm_id):
        return None
    state = d.get("JobState", "UNKNOWN")
    try:
        num_cpus = int(d.get("NumCPUs", "1"))
    except ValueError:
        num_cpus = 1
    elapsed_seconds = _parse_elapsed(d.get("RunTime", "00:00:00"))
    n_gpus = _parse_gpus_from_scontrol(d)
    return state, num_cpus, elapsed_seconds, n_gpus


def _parse_elapsed(s: str) -> int:
    if not s:
        return 0
    days = 0
    if "-" in s:
        d, s = s.split("-", 1)
        try:
            days = int(d)
        except ValueError:
            return 0
    parts = s.split(":")
    if len(parts) != 3:
        return 0
    try:
        h, m, sec = (int(x) for x in parts)
    except ValueError:
        return 0
    return days * 86400 + h * 3600 + m * 60 + sec


def _parse_gpus_from_scontrol(d: dict) -> int:
    tpn = d.get("TresPerNode", "")
    if tpn.startswith("gres:gpu:"):
        try:
            return max(1, int(tpn.split(":")[2]))
        except (IndexError, ValueError):
            pass
    tres = d.get("TRES", "")
    for part in tres.split(","):
        if part.startswith("gres/gpu="):
            try:
                return max(1, int(part.split("=")[1]))
            except (IndexError, ValueError):
                pass
    return 1
