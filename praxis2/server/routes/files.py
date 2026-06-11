"""M10 files routes:5 file endpoint + 1 agents/profile (T10 加)。

依赖 deps dict:
  repo            — 复用 auth_deps 的 repo(查 user)
  files_repo      — FilesRepo
  fs_store        — FsStore
  settings        — Settings
"""

from __future__ import annotations

import json
import uuid
from urllib.parse import parse_qs

from praxis2.files.mime import detect as detect_mime
from praxis2.files.multipart_stream import MultipartError, parse_upload
from praxis2.files.security import sanitize_filename

# spec §0 #5 五个枚举(必须与 DB CHECK 约束 files_purpose_check 一致,否则插入 500)
_PURPOSES = {"pdb", "config", "report", "md_input", "other"}


async def _json(send, status: int, body: dict, extra_headers=()) -> None:
    data = json.dumps(body, ensure_ascii=False).encode()
    headers = [(b"content-type", b"application/json; charset=utf-8")]
    headers.extend(extra_headers)
    await send({"type": "http.response.start", "status": status,
                "headers": headers})
    await send({"type": "http.response.body", "body": data})


def _qs_purpose(scope) -> str | None:
    qs = scope.get("query_string", b"")
    if not qs:
        return None
    parsed = parse_qs(qs.decode("ascii", errors="replace"))
    vals = parsed.get("purpose", [])
    return vals[0] if vals else None


def _qs_limit(scope, default: int = 50, lo: int = 1, hi: int = 200) -> int:
    """解析 ?limit=N,非法/缺省 → default,clamp 到 [lo, hi]。"""
    qs = scope.get("query_string", b"")
    if not qs:
        return default
    parsed = parse_qs(qs.decode("ascii", errors="replace"))
    vals = parsed.get("limit", [])
    if not vals:
        return default
    try:
        n = int(vals[0])
    except (ValueError, TypeError):
        return default
    return max(lo, min(hi, n))


def _path_file_id(scope) -> str:
    pp = scope.get("path_params")
    if pp and "file_id" in pp:
        return pp["file_id"]
    path = scope.get("path", "")
    parts = path.split("/")
    if len(parts) >= 4 and parts[1] == "api" and parts[2] == "files":
        return parts[3]
    return ""


async def handle_files_list(scope, receive, send, deps) -> None:
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    purpose = _qs_purpose(scope)
    if purpose is not None and purpose not in _PURPOSES:
        await _json(send, 400, {
            "error": "invalid_purpose",
            "allowed": sorted(_PURPOSES),
        })
        return
    rows = await deps["files_repo"].list_files(
        user_id=user["user_id"], purpose=purpose,
    )
    await _json(send, 200, {"files": [
        {
            "id": r["id"], "filename": r["filename"],
            "size_bytes": r["size_bytes"], "mime": r["mime"],
            "purpose": r["purpose"],
            "created_at": (
                r["created_at"].isoformat()
                if hasattr(r["created_at"], "isoformat")
                else r["created_at"]
            ),
        }
        for r in rows
    ]})


async def handle_storage_biggest(scope, receive, send, deps) -> None:
    """v0.7.2 Storage "📦 最大文件" tab:当前 user 所有文件按 size_bytes 降序取前 N。

    复用 files_repo.list_files(purpose=None) 拿全量,Python 侧排序 + 截断。
    返回 {files:[...]},字段同 handle_files_list,另带前端 BiggestFile 期望的
    path/mtime 别名(StorageModal 渲染 f.path / f.mtime)。
    """
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    limit = _qs_limit(scope)
    rows = await deps["files_repo"].list_files(
        user_id=user["user_id"], purpose=None,
    )
    rows = sorted(rows, key=lambda r: r["size_bytes"], reverse=True)[:limit]

    def _iso(v):
        return v.isoformat() if hasattr(v, "isoformat") else v

    await _json(send, 200, {"files": [
        {
            "id": r["id"], "filename": r["filename"],
            "size_bytes": r["size_bytes"], "mime": r["mime"],
            "purpose": r["purpose"],
            "created_at": _iso(r["created_at"]),
            # 前端 BiggestFile 渲染用别名(StorageModal: f.path / f.mtime)
            "path": r["filename"],
            "mtime": _iso(r["created_at"]),
        }
        for r in rows
    ]})


async def handle_files_usage(scope, receive, send, deps) -> None:
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    usage = await deps["files_repo"].usage(user_id=user["user_id"])
    settings = deps["settings"]
    await _json(send, 200, {
        "used_bytes": usage["used_bytes"],
        "quota_bytes": settings.files_quota_bytes,
        "count": usage["count"],
        "max_per_file_bytes": settings.files_max_per_file_bytes,
    })


async def handle_files_delete(scope, receive, send, deps) -> None:
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    file_id = _path_file_id(scope)
    deleted = await deps["files_repo"].soft_delete(
        user_id=user["user_id"], file_id=file_id,
    )
    if deleted is None:
        await _json(send, 404, {"error": "not_found"})
        return
    await _json(send, 200, {"ok": True})


class _UploadLimit(Exception):
    def __init__(self, code: str, detail: dict) -> None:
        self.code = code
        self.detail = detail


async def handle_files_upload(scope, receive, send, deps) -> None:
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    purpose = _qs_purpose(scope)
    if purpose is None or purpose not in _PURPOSES:
        await _json(send, 400, {
            "error": "invalid_purpose", "allowed": sorted(_PURPOSES),
        })
        return

    settings = deps["settings"]
    fs_store = deps["fs_store"]
    repo = deps["files_repo"]
    uid = user["user_id"]
    fid = str(uuid.uuid4())
    max_size = settings.files_max_per_file_bytes
    quota = settings.files_quota_bytes

    usage = await repo.usage(user_id=uid)
    used = usage["used_bytes"]

    try:
        parsed = await parse_upload(receive, scope["headers"])
    except MultipartError as e:
        await _json(send, 400, {"error": "bad_multipart", "reason": str(e)})
        return

    filename = sanitize_filename(parsed["filename"] or "unnamed")
    storage_key = f"fs:{uid}/{fid}"

    # spec §5.1 carry:同用户并发 upload 应取 pg_advisory_xact_lock
    # (hashtext('upload:'||user_id)) 防 quota 绕过。M10 单 worker
    # gunicorn = 2 workers,真有并发概率低,M10.5 carry。

    async def gated_chunks():
        written = 0
        async for chunk in parsed["body_iter"]:
            written += len(chunk)
            if written > max_size:
                raise _UploadLimit("file_too_large", {"limit_bytes": max_size})
            if used + written > quota:
                raise _UploadLimit("quota_exceeded", {
                    "used_bytes": used, "quota_bytes": quota,
                })
            yield chunk

    try:
        size = await fs_store.write_stream(uid, fid, gated_chunks())
    except _UploadLimit as ul:
        await _json(send, 413, {"error": ul.code, **ul.detail})
        return
    except MultipartError as e:
        await _json(send, 400, {"error": "bad_multipart", "reason": str(e)})
        return
    except Exception as e:
        await _json(send, 500, {"error": "upload_failed", "reason": repr(e)})
        return

    final_path = fs_store._final_path(uid, fid)
    mime = detect_mime(str(final_path))

    try:
        row = await repo.create_file(
            user_id=uid, filename=filename, size_bytes=size,
            mime=mime, purpose=purpose, storage_key=storage_key,
        )
    except Exception as e:
        await fs_store.delete(uid, fid)
        await _json(send, 500, {"error": "upload_failed", "reason": repr(e)})
        return

    await _json(send, 200, {
        "id": row["id"], "filename": row["filename"],
        "size_bytes": row["size_bytes"], "mime": row["mime"],
        "purpose": row["purpose"],
        "created_at": (
            row["created_at"].isoformat()
            if hasattr(row["created_at"], "isoformat")
            else row["created_at"]
        ),
    })


async def handle_files_download(scope, receive, send, deps) -> None:
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized", "reason": "未登录"})
        return
    file_id = _path_file_id(scope)
    row = await deps["files_repo"].get_file(
        user_id=user["user_id"], file_id=file_id,
    )
    if row is None:
        await _json(send, 404, {"error": "not_found"})
        return
    # storage_key 格式: "fs:{user_id}/{storage_fid}"
    # DB 中 row["id"] 是公开 UUID,fs 中实际文件名是 upload 时生成的 fid
    storage_key = row.get("storage_key", "")
    if storage_key.startswith("fs:"):
        _sk_uid, _, storage_fid = storage_key[3:].partition("/")
    else:
        storage_fid = file_id  # 兜底(理论上不会走到)
    fs_store = deps["fs_store"]
    if not fs_store.exists(user["user_id"], storage_fid):
        await _json(send, 404, {"error": "not_found"})
        return
    size = fs_store.get_size(user["user_id"], storage_fid)
    mime = (row["mime"] or "application/octet-stream").encode("ascii", "replace")
    filename = sanitize_filename(row["filename"])

    range_h = None
    for k, v in scope.get("headers", []):
        if k.lower() == b"range":
            range_h = v.decode("ascii", "replace")
            break

    if range_h:
        start, end = _parse_range(range_h, size)
        if start is None:
            await _json(send, 416, {"error": "range_not_satisfiable",
                                    "size_bytes": size})
            return
        status = 206
        headers = [
            (b"content-type", mime),
            (b"content-length", str(end - start + 1).encode()),
            (b"content-range",
             f"bytes {start}-{end}/{size}".encode("ascii")),
            (b"accept-ranges", b"bytes"),
            (b"content-disposition",
             f'attachment; filename="{filename}"'.encode()),
        ]
        body_start, body_end = start, end
    else:
        status = 200
        headers = [
            (b"content-type", mime),
            (b"content-length", str(size).encode()),
            (b"accept-ranges", b"bytes"),
            (b"content-disposition",
             f'attachment; filename="{filename}"'.encode()),
        ]
        body_start, body_end = 0, size - 1

    await send({"type": "http.response.start", "status": status,
                "headers": headers})
    async for chunk in fs_store.read_stream(
        user["user_id"], storage_fid, start=body_start, end=body_end,
    ):
        await send({"type": "http.response.body", "body": chunk,
                    "more_body": True})
    await send({"type": "http.response.body", "body": b"", "more_body": False})


def _parse_range(header: str, size: int) -> tuple[int | None, int | None]:
    """解 'bytes=N-M' 或 'bytes=N-'。返 (start, end) 或 (None, None) 表 416。"""
    if not header.startswith("bytes="):
        return (None, None)
    try:
        spec = header[len("bytes="):]
        if "," in spec:
            return (None, None)   # 多 range 不支持
        a, _, b = spec.partition("-")
        if a == "" and b != "":
            n = int(b)
            if n == 0 or n > size:
                return (None, None)
            return (size - n, size - 1)
        start = int(a)
        end = int(b) if b else size - 1
        if start > end or end >= size or start < 0:
            return (None, None)
        return (start, end)
    except (ValueError, TypeError):
        return (None, None)


async def handle_agents_profile(scope, receive, send, deps) -> None:
    """M10:返 13 学科 brain 资料卡。public endpoint(不要求登录)。"""
    from praxis2.brains.migrate import DISCIPLINE_SLUGS
    from praxis2.brains.profile import load_all_profiles
    from praxis2.server.app import _agent_meta

    profiles_dict = load_all_profiles()
    out = []
    for slug in DISCIPLINE_SLUGS:
        base = _agent_meta(slug)
        prof = profiles_dict.get(slug, {})
        out.append({**base, **prof})
    await _json(send, 200, {"profiles": out})


async def handle_storage_trajectories(scope, receive, send, deps) -> None:
    """GET /api/storage/trajectories — 当前用户的 MD 模拟轨迹列表。

    查 md_jobs 表(通过 md_repo),映射为前端 MdTrajectory 接口。
    md_repo 可能为 None(PG 未配置),此时返回空列表而非 500。
    """
    user = scope.get("user")
    if not user:
        await _json(send, 401, {"error": "unauthorized"})
        return

    md_repo = deps.get("md_repo")
    if md_repo is None:
        await _json(send, 200, {"trajectories": []})
        return

    user_id = user["user_id"]
    ssh_cfg = deps.get("ssh_cfg")
    ssh_user = ssh_cfg.user if ssh_cfg else "zkyd"

    rows = await md_repo.list_recent(user_id, limit=200)
    trajs = [_job_to_trajectory(r, ssh_user) for r in rows]
    await _json(send, 200, {"trajectories": trajs})


def _job_to_trajectory(job: dict, ssh_user: str) -> dict:
    """md_jobs row → MdTrajectory-compatible dict。"""
    job_id = job["id"]
    params = job.get("params") or {}
    notes = params.get("notes") or ""
    name = notes if notes else f"{job['sim_type']} {str(job_id)[:8]}"

    created_at = job.get("created_at")
    finished_at = job.get("finished_at")

    return {
        "job_id": job_id,
        "name": name,
        "size_bytes": 0,
        "remote_host": job.get("gpu_host") or f"10.102.106.53",
        "remote_path": f"/home/{ssh_user}/praxis-md/{job_id}",
        "structure": params.get("structure_file_id") or "",
        "ensemble": params.get("ensemble") or "",
        "time_ns": params.get("time_ns"),
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at or ""),
        "finished_at": finished_at.isoformat() if hasattr(finished_at, "isoformat") else (str(finished_at) if finished_at else None),
        "status": job.get("status", "unknown"),
        "download_url": f"/api/md/jobs/{job_id}",
        "sim_type": job.get("sim_type", ""),
        "cost_li": job.get("cost_li", 0),
        "gpu_hours": job.get("gpu_hours", 0.0),
    }


ROUTES: dict[tuple[str, str], str] = {
    ("/api/files", "GET"): "handle_files_list",
    ("/api/files", "POST"): "handle_files_upload",
    ("/api/files/usage", "GET"): "handle_files_usage",
    ("/api/storage/biggest", "GET"): "handle_storage_biggest",
    ("/api/storage/trajectories", "GET"): "handle_storage_trajectories",
    ("/api/agents/profile", "GET"): "handle_agents_profile",
    # 动态路径 /api/files/{id} 不能用 dict 静态匹配,T11 在 app.py 加 prefix dispatch:
    # /api/files/{uuid}              DELETE → handle_files_delete
    # /api/files/{uuid}/content      GET    → handle_files_download
}
