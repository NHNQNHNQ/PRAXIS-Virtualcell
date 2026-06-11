"""M10 files routes:5 endpoint × happy + error code + Range。"""
from __future__ import annotations

import shutil
import tempfile
import uuid
from datetime import UTC, datetime

import pytest

from tests.test_auth_routes import _make_deps
from tests.test_auth_routes_v2_me import (
    _capture,
    _mk_receive,
    _mk_scope,
    _mk_userrow,
)


class _FakeFilesRepo:
    def __init__(self):
        self.rows = {}

    async def create_file(self, **kw):
        fid = str(uuid.uuid4())
        row = {
            "id": fid, "filename": kw["filename"],
            "size_bytes": kw["size_bytes"], "mime": kw["mime"],
            "purpose": kw["purpose"], "storage_key": kw["storage_key"],
            "created_at": datetime.now(UTC),
        }
        self.rows[fid] = row
        return row

    async def list_files(self, *, user_id, purpose):
        return [r for r in self.rows.values()
                if (purpose is None or r["purpose"] == purpose)]

    async def get_file(self, *, user_id, file_id):
        return self.rows.get(file_id)

    async def soft_delete(self, *, user_id, file_id):
        if file_id in self.rows:
            del self.rows[file_id]
            return file_id
        return None

    async def usage(self, *, user_id):
        return {
            "used_bytes": sum(r["size_bytes"] for r in self.rows.values()),
            "count": len(self.rows),
        }


@pytest.fixture
async def files_deps():
    deps = await _make_deps()
    root = tempfile.mkdtemp(prefix="praxis2_files_test_")
    from praxis2.files.store_fs import FsStore
    fs = FsStore(root)
    deps["files_repo"] = _FakeFilesRepo()
    deps["fs_store"] = fs
    # 补 _Settings 缺少的 files quota 字段
    settings = deps["settings"]
    if not hasattr(settings, "files_quota_bytes"):
        settings.files_quota_bytes = 100 * 1024**3       # 100 GB
    if not hasattr(settings, "files_max_per_file_bytes"):
        settings.files_max_per_file_bytes = 20 * 1024**3  # 20 GB
    yield deps
    shutil.rmtree(root, ignore_errors=True)


async def test_list_files_empty(files_deps):
    from praxis2.server.routes.files import handle_files_list
    files_deps["repo"]._users["uid-l1"] = _mk_userrow(id="uid-l1", email="l1@x")
    scope = {"type": "http", "method": "GET", "path": "/api/files",
             "headers": [], "query_string": b"",
             "user": {"user_id": "uid-l1"}}
    status, body, _ = await _capture(handle_files_list, scope, _mk_receive(), files_deps)
    assert status == 200
    assert body == {"files": []}


async def test_storage_biggest_unauthorized(files_deps):
    from praxis2.server.routes.files import handle_storage_biggest
    scope = {"type": "http", "method": "GET", "path": "/api/storage/biggest",
             "headers": [], "query_string": b""}  # 无 user
    status, body, _ = await _capture(
        handle_storage_biggest, scope, _mk_receive(), files_deps,
    )
    assert status == 401
    assert body["error"] == "unauthorized"


async def test_storage_biggest_sorted_desc_and_limit(files_deps):
    from praxis2.server.routes.files import handle_storage_biggest
    files_deps["repo"]._users["uid-b1"] = _mk_userrow(id="uid-b1", email="b1@x")
    # 造 3 个不同大小的文件(乱序插入)
    sizes = {"small": 10, "big": 9000, "mid": 500}
    for name, sz in sizes.items():
        await files_deps["files_repo"].create_file(
            user_id="uid-b1", filename=f"{name}.pdb", size_bytes=sz,
            mime=None, purpose="pdb", storage_key=f"fs:{name}",
        )
    scope = {"type": "http", "method": "GET", "path": "/api/storage/biggest",
             "headers": [], "query_string": b"limit=2",
             "user": {"user_id": "uid-b1"}}
    status, body, _ = await _capture(
        handle_storage_biggest, scope, _mk_receive(), files_deps,
    )
    assert status == 200
    files = body["files"]
    # limit=2 截断
    assert len(files) == 2
    # 降序:big(9000) > mid(500)
    assert [f["size_bytes"] for f in files] == [9000, 500]
    # 字段:spec 字段 + 前端别名 path/mtime
    top = files[0]
    assert top["filename"] == "big.pdb"
    assert top["path"] == "big.pdb"
    assert "created_at" in top and "mtime" in top
    # created_at 已 isoformat(字符串,非 datetime)
    assert isinstance(top["created_at"], str)


async def test_storage_biggest_limit_clamped(files_deps):
    """非法 limit → 默认 50;超界 limit clamp 到 200。"""
    from praxis2.server.routes.files import _qs_limit
    assert _qs_limit({"query_string": b""}) == 50
    assert _qs_limit({"query_string": b"limit=abc"}) == 50
    assert _qs_limit({"query_string": b"limit=0"}) == 1
    assert _qs_limit({"query_string": b"limit=99999"}) == 200
    assert _qs_limit({"query_string": b"limit=30"}) == 30


async def test_usage_empty(files_deps):
    from praxis2.server.routes.files import handle_files_usage
    files_deps["repo"]._users["uid-u1"] = _mk_userrow(id="uid-u1", email="u1@x")
    scope = {"type": "http", "method": "GET", "path": "/api/files/usage",
             "headers": [], "user": {"user_id": "uid-u1"}}
    status, body, _ = await _capture(handle_files_usage, scope, _mk_receive(), files_deps)
    assert status == 200
    # 注意字段名 count(不是 files_count!)
    assert body["count"] == 0
    assert body["used_bytes"] == 0
    assert "quota_bytes" in body
    assert "max_per_file_bytes" in body


async def test_invalid_purpose_400(files_deps):
    from praxis2.server.routes.files import handle_files_list
    files_deps["repo"]._users["uid-p1"] = _mk_userrow(id="uid-p1", email="p1@x")
    scope = {"type": "http", "method": "GET", "path": "/api/files",
             "headers": [], "query_string": b"purpose=__INVALID__",
             "user": {"user_id": "uid-p1"}}
    status, body, _ = await _capture(handle_files_list, scope, _mk_receive(), files_deps)
    assert status == 400
    assert body["error"] == "invalid_purpose"


async def test_delete_404_when_not_found(files_deps):
    from praxis2.server.routes.files import handle_files_delete
    files_deps["repo"]._users["uid-d1"] = _mk_userrow(id="uid-d1", email="d1@x")
    fake_fid = str(uuid.uuid4())
    scope = {"type": "http", "method": "DELETE",
             "path": f"/api/files/{fake_fid}",
             "headers": [], "user": {"user_id": "uid-d1"},
             "path_params": {"file_id": fake_fid}}
    status, body, _ = await _capture(
        handle_files_delete, scope, _mk_receive(), files_deps,
    )
    assert status == 404


async def test_delete_happy(files_deps):
    from praxis2.server.routes.files import handle_files_delete
    files_deps["repo"]._users["uid-d2"] = _mk_userrow(id="uid-d2", email="d2@x")
    row = await files_deps["files_repo"].create_file(
        user_id="uid-d2", filename="x.pdb", size_bytes=10,
        mime=None, purpose="pdb", storage_key="fs:x",
    )
    fid = row["id"]
    scope = {"type": "http", "method": "DELETE",
             "path": f"/api/files/{fid}", "headers": [],
             "user": {"user_id": "uid-d2"},
             "path_params": {"file_id": fid}}
    status, body, _ = await _capture(
        handle_files_delete, scope, _mk_receive(), files_deps,
    )
    assert status == 200
    assert body == {"ok": True}


async def test_download_404_when_missing(files_deps):
    from praxis2.server.routes.files import handle_files_download
    files_deps["repo"]._users["uid-dl1"] = _mk_userrow(id="uid-dl1", email="dl1@x")
    fake_fid = str(uuid.uuid4())
    scope = {"type": "http", "method": "GET",
             "path": f"/api/files/{fake_fid}/content",
             "headers": [], "user": {"user_id": "uid-dl1"},
             "path_params": {"file_id": fake_fid}}
    status, body, _ = await _capture(
        handle_files_download, scope, _mk_receive(), files_deps,
    )
    assert status == 404


def _build_multipart_body(boundary: bytes, filename: bytes, content: bytes) -> bytes:
    return (
        b"--" + boundary + b"\r\n"
        + b'Content-Disposition: form-data; name="file"; filename="' + filename + b'"\r\n'
        + b"Content-Type: application/octet-stream\r\n\r\n"
        + content + b"\r\n"
        + b"--" + boundary + b"--\r\n"
    )


async def test_upload_happy(files_deps):
    from praxis2.server.routes.files import handle_files_upload
    files_deps["repo"]._users["uid-up1"] = _mk_userrow(id="uid-up1", email="up1@x")

    boundary = b"BOUNDARY_UPLOAD"
    body = _build_multipart_body(boundary, b"test.pdb", b"hello PDB")

    chunks = iter([
        {"type": "http.request", "body": body, "more_body": False},
    ])

    async def receive():
        return next(chunks)

    scope = {"type": "http", "method": "POST",
             "path": "/api/files", "headers": [
                 (b"content-type", b"multipart/form-data; boundary=" + boundary),
                 (b"content-length", str(len(body)).encode()),
             ],
             "query_string": b"purpose=pdb",
             "user": {"user_id": "uid-up1"}}
    status, resp, _ = await _capture(
        handle_files_upload, scope, receive, files_deps,
    )
    assert status == 200
    assert resp["filename"] == "test.pdb"
    assert resp["size_bytes"] == 9
    assert resp["purpose"] == "pdb"


async def test_agents_profile_returns_13(files_deps):
    from praxis2.server.routes.files import handle_agents_profile
    scope = _mk_scope("GET", "/api/agents/profile")
    status, body, _ = await _capture(
        handle_agents_profile, scope, _mk_receive(), files_deps,
    )
    assert status == 200
    assert "profiles" in body
    assert len(body["profiles"]) == 13


async def test_agents_profile_has_full_shape(files_deps):
    from praxis2.server.routes.files import handle_agents_profile
    scope = _mk_scope("GET", "/api/agents/profile")
    _, body, _ = await _capture(
        handle_agents_profile, scope, _mk_receive(), files_deps,
    )
    for p in body["profiles"]:
        # spec §4.1 12+ 字段(slug+name+desc+emoji+examples 来自 _AGENT_META,
        # short_prompt/methods/case_count/rule_count/skill_workflows/sample_cases/
        # helps_with/delivers 来自 brains/profile.py)
        for k in ("slug", "name", "desc", "emoji", "examples",
                  "short_prompt", "methods", "case_count", "rule_count",
                  "skill_workflows", "sample_cases", "helps_with", "delivers"):
            assert k in p, f"{p.get('slug', '?')} missing {k}"
