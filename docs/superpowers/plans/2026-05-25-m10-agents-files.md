# M10 — agents/profile + 文件管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 v2 后端 `/api/agents/profile` 和 `/api/files/*` 接通,让 FE 智能体手册 + 文件管理面板真用;**v1 链路全程不动**;`core/agents/brains/tools/scheduler/runtime` 0 改。

**Architecture:** 003 alembic migration 新建 `files` 表;新模块 `praxis2/files/`(repo + fs streaming + multipart 流式 + mime/security);新 `praxis2/brains/profile.py`(启动 lazy walk 13 brain 文件树);6 endpoint 统一放在新 `praxis2/server/routes/files.py`(跟 `auth/routes.py:ROUTES` 同 merge 模式)。20GB 流式上传 + Range 下载 + python-multipart + python-magic。

**Tech Stack:** Python 3.13 / asyncpg / alembic raw SQL / python-multipart / python-magic + libmagic1 / PyYAML / pytest / TypeScript FE(0 改)

**Spec:** `docs/superpowers/specs/2026-05-25-m10-agents-files-design.md`

---

## File Structure

### 新增
| 路径 | 责任 |
|------|------|
| `migrations/versions/003_files.py` | DB 003:`files` 表 + 2 个 partial index(deleted_at IS NULL) |
| `praxis2/files/__init__.py` | 包 |
| `praxis2/files/security.py` | `sanitize_filename(name) -> str` |
| `praxis2/files/mime.py` | `detect(path) -> str`(python-magic + octet-stream 兜底) |
| `praxis2/files/store_fs.py` | `FsStore`:`write_stream` / `read_stream`(含 Range)/ `delete` / `exists` / `get_size` |
| `praxis2/files/repo.py` | `FilesRepo` 5 方法 + `FileRow` dataclass |
| `praxis2/files/multipart_stream.py` | `parse_upload(receive, on_chunk)`(python-multipart 包装,RFC 7578 流式)|
| `praxis2/brains/profile.py` | `load_all_profiles()` + `_walk_brain` + `_load_metadata_yaml`,module-level cache |
| `praxis2/server/routes/__init__.py` | 已存在,空 |
| `praxis2/server/routes/files.py` | 6 个 handler + `ROUTES` dict(`agents_profile` / `files_list` / `files_upload` / `files_delete` / `files_usage` / `files_download`) |
| `tests/test_files_security.py` | 4 个 sanitize 测试 |
| `tests/test_files_mime.py` | 3 个 mime detect 测试 |
| `tests/test_files_store_fs.py` | 8 个 fs streaming + Range 测试 |
| `tests/test_files_repo.py` | 10 个 FilesRepo integration 测试 |
| `tests/test_files_multipart_stream.py` | 4 个 parse_upload 单测 |
| `tests/test_files_routes.py` | 12 个 endpoint × 状态机 + Range |
| `tests/test_brains_profile.py` | 6 个 13-brain walk + metadata 缺缺补缺 |

### 改
| 路径 | 改动 |
|------|------|
| `praxis2/config.py` | + `files_root: str` / `files_quota_bytes: int` / `files_max_per_file_bytes: int` + env 读取 |
| `praxis2/auth/routes.py` | **删** `handle_files_usage_stub`(M9.1 stub,`files_count` 字段错位)+ `ROUTES` 那一行;**不删** 其他 admin stubs |
| `praxis2/server/app.py` | `_App.__init__` 构造 `FilesRepo` + `FsStore` + boot 调 `load_all_profiles()`;merge `files_routes.ROUTES` 进 `_routes`;构造 `files_deps = {"repo": ..., "fs_store": ..., "files_repo": ..., "settings": ...}` |
| `pyproject.toml` | + `python-multipart>=0.0.9` + `python-magic>=0.4.27` + `PyYAML>=6.0` |
| `deploy/gunicorn.conf.py` | `timeout = 120` → `1800`(20GB upload 慢路径) |
| `deploy/push_backend.sh` | pip install 末尾加 3 个新 deps |
| `frontend/src/lib/extras.ts` | 0 改(shape 已对齐 M10) |

---

## 测试策略

- **单元**(默认跑):`security` / `mime` / `multipart_stream` / `store_fs` / `brains_profile` 走真 fs(`tempfile.mkdtemp`);不需要 docker
- **Integration**(`@pytest.mark.integration`):`repo` + `routes` 需要 docker PG,跑 `PRAXIS_INTEGRATION=1 PRAXIS_DB_URL=... pytest ...`
- pytest baseline M9.1 = 1570 pass。M10 目标 ≥ 1606(+~36 新增)

---

## Task 1: Config + deps + gunicorn timeout

**Files:**
- Modify: `praxis2/config.py`
- Modify: `pyproject.toml`
- Modify: `deploy/gunicorn.conf.py`
- Modify: `deploy/push_backend.sh`
- Test: `tests/test_config_files.py`(新)

- [ ] **Step 1: 写失败测试**

```python
# tests/test_config_files.py
"""M10 config:PRAXIS_FILES_ROOT + QUOTA_BYTES + MAX_PER_FILE_BYTES。"""
from __future__ import annotations

from praxis2.config import Settings, load_from_env


def test_default_files_root():
    s = Settings(password_pepper="x", smtp_host="")
    assert s.files_root == "/home/zkyd/data1/praxis2-files"


def test_default_files_quota_100gb():
    s = Settings(password_pepper="x", smtp_host="")
    assert s.files_quota_bytes == 100 * 1024**3  # 107374182400


def test_default_files_max_per_file_20gb():
    s = Settings(password_pepper="x", smtp_host="")
    assert s.files_max_per_file_bytes == 20 * 1024**3  # 21474836480


def test_env_override_files_root(monkeypatch):
    monkeypatch.setenv("PRAXIS_PASSWORD_PEPPER", "x")
    monkeypatch.setenv("PRAXIS_FILES_ROOT", "/tmp/custom")
    s = load_from_env()
    assert s.files_root == "/tmp/custom"


def test_env_override_quota(monkeypatch):
    monkeypatch.setenv("PRAXIS_PASSWORD_PEPPER", "x")
    monkeypatch.setenv("PRAXIS_FILES_QUOTA_BYTES", "1073741824")  # 1 GB
    s = load_from_env()
    assert s.files_quota_bytes == 1073741824
```

- [ ] **Step 2: 跑测试确认红**

Run: `pytest tests/test_config_files.py -v`
Expected: 5 FAIL with `AttributeError: 'Settings' object has no attribute 'files_root'`

- [ ] **Step 3: 实现 — `praxis2/config.py`**

在 `signup_gift_li: int = 10000` 之后加:

```python
    signup_gift_li: int = 10000
    # M10:文件管理 3 个 env
    files_root: str = "/home/zkyd/data1/praxis2-files"
    files_quota_bytes: int = 100 * 1024**3            # 100 GB
    files_max_per_file_bytes: int = 20 * 1024**3      # 20 GB
```

在 `_KNOWN_KEYS` 集合加(找到该 set 的定义位置,加这 3 行):

```python
        "PRAXIS_FILES_ROOT",
        "PRAXIS_FILES_QUOTA_BYTES",
        "PRAXIS_FILES_MAX_PER_FILE_BYTES",
```

**同时**:在 `praxis2/auth/routes.py:handle_info` 里把 `"v0.10.0"` 改成 `"v0.11.0"`(spec 标 v0.11.0 = M10 ship 版,不留到 T13 sed):

```python
        {
            "service": "PRAXIS-2",
            "version": "v0.11.0",     # ← M10 改自 v0.10.0
            ...
        }
```

在 `load_from_env()` 里(`signup_gift_li=int(e.get("PRAXIS_SIGNUP_GIFT_LI", "10000"))` 后)加:

```python
        signup_gift_li=int(e.get("PRAXIS_SIGNUP_GIFT_LI", "10000")),
        files_root=e.get("PRAXIS_FILES_ROOT", "/home/zkyd/data1/praxis2-files"),
        files_quota_bytes=int(e.get(
            "PRAXIS_FILES_QUOTA_BYTES", str(100 * 1024**3))),
        files_max_per_file_bytes=int(e.get(
            "PRAXIS_FILES_MAX_PER_FILE_BYTES", str(20 * 1024**3))),
```

- [ ] **Step 4: 跑测试确认绿**

Run: `pytest tests/test_config_files.py -v`
Expected: 5 PASS

- [ ] **Step 5: pyproject deps + gunicorn timeout + push_backend.sh**

Edit `pyproject.toml`,在 `dependencies = [` 列表加 3 行(在已有 `httpx`/`asyncpg` 等同位置):

```toml
    "python-multipart>=0.0.9",
    "python-magic>=0.4.27",
    "PyYAML>=6.0",
```

Edit `deploy/gunicorn.conf.py`,改 `timeout = 120` → `timeout = 1800`。

Edit `deploy/push_backend.sh`,在最后一个 `python3 -m pip install --user` 命令的依赖列表加 `python-multipart` `python-magic` `pyyaml`。

- [ ] **Step 6: ruff + commit**

```bash
ruff check praxis2/config.py tests/test_config_files.py
git add praxis2/config.py tests/test_config_files.py pyproject.toml deploy/gunicorn.conf.py deploy/push_backend.sh
git commit -m "$(cat <<'EOF'
feat(M10/T1): config 3 个 files env + python-multipart/magic/yaml 依赖 + gunicorn timeout 1800s

env 默认:
- PRAXIS_FILES_ROOT=/home/zkyd/data1/praxis2-files
- PRAXIS_FILES_QUOTA_BYTES=107374182400 (100 GB)
- PRAXIS_FILES_MAX_PER_FILE_BYTES=21474836480 (20 GB)

gunicorn timeout 120s → 1800s 适配 20GB upload 慢路径。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: alembic 003 — files 表 + 2 索引

**Files:**
- Create: `migrations/versions/003_files.py`

- [ ] **Step 1: 写 003 migration**

```python
# migrations/versions/003_files.py
"""files: 用户上传文件元数据 + 2 个 partial index。

Revision ID: 003_files
Revises: 002_user_profile_billing
"""

from __future__ import annotations

from alembic import op

revision = "003_files"
down_revision = "002_user_profile_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE files (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            filename    TEXT NOT NULL,
            size_bytes  BIGINT NOT NULL CHECK (size_bytes >= 0),
            mime        TEXT,
            purpose     TEXT NOT NULL
                          CHECK (purpose IN ('pdb','config','report','md_input','other')),
            storage_key TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at  TIMESTAMPTZ
        );
    """)
    op.execute(
        "CREATE INDEX ix_files_user_purpose "
        "ON files(user_id, purpose) WHERE deleted_at IS NULL;"
    )
    op.execute(
        "CREATE INDEX ix_files_user_created "
        "ON files(user_id, created_at DESC) WHERE deleted_at IS NULL;"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_files_user_created;")
    op.execute("DROP INDEX IF EXISTS ix_files_user_purpose;")
    op.execute("DROP TABLE IF EXISTS files;")
```

- [ ] **Step 2: 语法验证**

```bash
python -c "import ast; ast.parse(open('migrations/versions/003_files.py').read())"
ruff check migrations/versions/003_files.py
```

Expected: 0 输出 + 0 errors

- [ ] **Step 3: Commit**

```bash
git add migrations/versions/003_files.py
git commit -m "$(cat <<'EOF'
feat(M10/T2): alembic 003 — files 表 + 2 partial index

CHECK purpose IN 5 枚举 + size_bytes >= 0。
两个 partial index 都 WHERE deleted_at IS NULL(active rows 查询路径快)。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `praxis2/files/security.py` — sanitize_filename

**Files:**
- Create: `praxis2/files/__init__.py`(空)
- Create: `praxis2/files/security.py`
- Test: `tests/test_files_security.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_files_security.py
"""M10 files security:filename sanitize。"""
from __future__ import annotations


def test_sanitize_keeps_chinese():
    from praxis2.files.security import sanitize_filename
    assert sanitize_filename("蛋白结构.pdb") == "蛋白结构.pdb"


def test_sanitize_strips_path_traversal():
    from praxis2.files.security import sanitize_filename
    # ../ / / 反斜线 / null / 控制字符 都该剥
    assert sanitize_filename("../../etc/passwd") == "etcpasswd"
    assert sanitize_filename("a/b/c.pdb") == "abc.pdb"
    assert sanitize_filename("a\\b.pdb") == "ab.pdb"
    assert sanitize_filename("a\x00b.pdb") == "ab.pdb"


def test_sanitize_caps_200_chars():
    from praxis2.files.security import sanitize_filename
    long_name = "a" * 300 + ".pdb"
    out = sanitize_filename(long_name)
    assert len(out) <= 200


def test_sanitize_keeps_dots_underscore_hyphen():
    from praxis2.files.security import sanitize_filename
    assert sanitize_filename("data.v1.0_final-2.pdb") == "data.v1.0_final-2.pdb"


def test_sanitize_empty_returns_underscore():
    from praxis2.files.security import sanitize_filename
    # 全是危险字符 → 不应返空,返 "_"
    assert sanitize_filename("///") == "_"
```

- [ ] **Step 2: 跑测试确认红**

Run: `pytest tests/test_files_security.py -v`
Expected: 5 FAIL — `ModuleNotFoundError: praxis2.files`

- [ ] **Step 3: 实现 — `praxis2/files/__init__.py` 空文件 + security.py**

```bash
mkdir -p praxis2/files
echo > praxis2/files/__init__.py
```

```python
# praxis2/files/security.py
"""文件名清洗:去 path traversal / 控制字符,保留中文 + 常用标点。"""

from __future__ import annotations

import re

# 允许字符:ASCII 字母数字 + 点 + 下划线 + 连字符 + 中日韩统一汉字
# (Unicode 一-鿿)。其他全删。
_SAFE_RE = re.compile(r"[A-Za-z0-9._\-一-鿿]+")
_MAX_LEN = 200


def sanitize_filename(name: str) -> str:
    """剥不安全字符,截断 200 字符。空结果返 '_' 防 fs 路径空。"""
    if not name:
        return "_"
    # 抽出所有"安全片段",拼接(等价于把不安全字符全替换成空)
    pieces = _SAFE_RE.findall(name)
    cleaned = "".join(pieces)
    if not cleaned:
        return "_"
    return cleaned[:_MAX_LEN]
```

- [ ] **Step 4: 跑测试确认绿**

Run: `pytest tests/test_files_security.py -v`
Expected: 5 PASS

- [ ] **Step 5: ruff + commit**

```bash
ruff check praxis2/files/ tests/test_files_security.py
git add praxis2/files/__init__.py praxis2/files/security.py tests/test_files_security.py
git commit -m "$(cat <<'EOF'
feat(M10/T3): files/security.py — sanitize_filename 保留中文 + 200 截断

正则白名单 [A-Za-z0-9._-] + 中日韩统一汉字 (\\u4e00-\\u9fff)。
真存储路径用 UUID,filename 仅 DB display + Content-Disposition,
这个函数兜底 path traversal 风险。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `praxis2/files/mime.py` — detect

**Files:**
- Create: `praxis2/files/mime.py`
- Test: `tests/test_files_mime.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_files_mime.py
"""M10 files mime:python-magic + octet-stream 兜底。"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


def _write_tmp(payload: bytes) -> str:
    f = tempfile.NamedTemporaryFile(delete=False)
    f.write(payload)
    f.close()
    return f.name


def test_detect_png_magic():
    from praxis2.files.mime import detect
    path = _write_tmp(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    try:
        # python-magic 不在 / libmagic 不在 → 兜底
        result = detect(path)
        assert result in ("image/png", "application/octet-stream")
    finally:
        Path(path).unlink()


def test_detect_pdf():
    from praxis2.files.mime import detect
    path = _write_tmp(b"%PDF-1.7\n" + b"\x00" * 100)
    try:
        result = detect(path)
        assert result in ("application/pdf", "application/octet-stream")
    finally:
        Path(path).unlink()


def test_detect_unknown_returns_octet_stream():
    from praxis2.files.mime import detect
    path = _write_tmp(b"\x00" * 100)   # 随机字节
    try:
        result = detect(path)
        # 即使 magic 装了,也可能返 octet-stream;不装一定返 octet-stream
        assert isinstance(result, str)
        assert "/" in result
    finally:
        Path(path).unlink()
```

- [ ] **Step 2: 跑测试确认红**

Run: `pytest tests/test_files_mime.py -v`
Expected: 3 FAIL — `ModuleNotFoundError: praxis2.files.mime`

- [ ] **Step 3: 实现 — `praxis2/files/mime.py`**

```python
# praxis2/files/mime.py
"""mime 检测:python-magic 探出 → fallback octet-stream。

production .53 装 libmagic1。dev/test 机可能没装(失败时静默兜底)。
"""

from __future__ import annotations

_OCTET_STREAM = "application/octet-stream"

try:
    import magic
    _MAGIC = magic.Magic(mime=True)
except (ImportError, Exception):  # libmagic 缺
    _MAGIC = None


def detect(path: str) -> str:
    """检 path 内容首部 mime。失败 → application/octet-stream。"""
    if _MAGIC is None:
        return _OCTET_STREAM
    try:
        out = _MAGIC.from_file(path)
        return out or _OCTET_STREAM
    except Exception:
        return _OCTET_STREAM
```

- [ ] **Step 4: 跑测试确认绿**

Run: `pytest tests/test_files_mime.py -v`
Expected: 3 PASS

- [ ] **Step 5: ruff + commit**

```bash
ruff check praxis2/files/mime.py tests/test_files_mime.py
git add praxis2/files/mime.py tests/test_files_mime.py
git commit -m "$(cat <<'EOF'
feat(M10/T4): files/mime.py — python-magic + octet-stream 兜底

libmagic1 不在 / 探测失败 → 'application/octet-stream'。
production .53 装 libmagic1 后真返 image/png 等。
dev 机不装也不崩(spec §5.2 安全:服务端 sniff,不信任 client mime)。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `praxis2/files/store_fs.py` — write/read stream + Range

**Files:**
- Create: `praxis2/files/store_fs.py`
- Test: `tests/test_files_store_fs.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_files_store_fs.py
"""M10 files store_fs:write_stream + read_stream + Range + cleanup。"""
from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import pytest


@pytest.fixture
def fs_root():
    d = tempfile.mkdtemp(prefix="praxis2_test_fs_")
    yield d
    import shutil
    shutil.rmtree(d, ignore_errors=True)


async def test_write_stream_creates_file(fs_root):
    from praxis2.files.store_fs import FsStore
    s = FsStore(fs_root)
    uid, fid = str(uuid.uuid4()), str(uuid.uuid4())

    async def gen():
        for chunk in (b"hello ", b"world"):
            yield chunk

    size = await s.write_stream(uid, fid, gen())
    assert size == 11
    assert s.exists(uid, fid)
    assert s.get_size(uid, fid) == 11


async def test_read_stream_full(fs_root):
    from praxis2.files.store_fs import FsStore
    s = FsStore(fs_root)
    uid, fid = str(uuid.uuid4()), str(uuid.uuid4())

    async def gen():
        yield b"hello world"

    await s.write_stream(uid, fid, gen())

    chunks = [c async for c in s.read_stream(uid, fid)]
    assert b"".join(chunks) == b"hello world"


async def test_read_stream_range_partial(fs_root):
    from praxis2.files.store_fs import FsStore
    s = FsStore(fs_root)
    uid, fid = str(uuid.uuid4()), str(uuid.uuid4())

    async def gen():
        yield b"hello world"   # 11 字节

    await s.write_stream(uid, fid, gen())

    # bytes 6-10 → "world"
    chunks = [c async for c in s.read_stream(uid, fid, start=6, end=10)]
    assert b"".join(chunks) == b"world"


async def test_read_stream_range_first_byte(fs_root):
    from praxis2.files.store_fs import FsStore
    s = FsStore(fs_root)
    uid, fid = str(uuid.uuid4()), str(uuid.uuid4())

    async def gen():
        yield b"hello world"

    await s.write_stream(uid, fid, gen())

    chunks = [c async for c in s.read_stream(uid, fid, start=0, end=0)]
    assert b"".join(chunks) == b"h"


async def test_write_stream_aborts_on_exception_cleans_part(fs_root):
    """gen 抛错 → .part 文件应被删,final 文件不存在。"""
    from praxis2.files.store_fs import FsStore
    s = FsStore(fs_root)
    uid, fid = str(uuid.uuid4()), str(uuid.uuid4())

    async def bad_gen():
        yield b"hello"
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await s.write_stream(uid, fid, bad_gen())

    assert not s.exists(uid, fid)
    part_path = Path(fs_root) / uid / f"{fid}.part"
    assert not part_path.exists()


async def test_delete_removes_file(fs_root):
    from praxis2.files.store_fs import FsStore
    s = FsStore(fs_root)
    uid, fid = str(uuid.uuid4()), str(uuid.uuid4())

    async def gen():
        yield b"hello"

    await s.write_stream(uid, fid, gen())
    assert s.exists(uid, fid)

    await s.delete(uid, fid)
    assert not s.exists(uid, fid)


async def test_exists_returns_false_for_missing(fs_root):
    from praxis2.files.store_fs import FsStore
    s = FsStore(fs_root)
    assert not s.exists(str(uuid.uuid4()), str(uuid.uuid4()))


async def test_get_size_returns_bytes(fs_root):
    from praxis2.files.store_fs import FsStore
    s = FsStore(fs_root)
    uid, fid = str(uuid.uuid4()), str(uuid.uuid4())

    async def gen():
        yield b"x" * 1024

    await s.write_stream(uid, fid, gen())
    assert s.get_size(uid, fid) == 1024
```

- [ ] **Step 2: 跑测试确认红**

Run: `pytest tests/test_files_store_fs.py -v`
Expected: 8 FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 — `praxis2/files/store_fs.py`**

```python
# praxis2/files/store_fs.py
"""本地 fs 流式存储。

布局:<root>/<user_id>/<file_id>      最终文件
      <root>/<user_id>/<file_id>.part  上传中(异常时清掉)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import AsyncIterator

_CHUNK_READ = 64 * 1024   # 64 KB read 块


class FsStore:
    def __init__(self, root: str) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _user_dir(self, user_id: str) -> Path:
        d = self._root / user_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _final_path(self, user_id: str, file_id: str) -> Path:
        return self._user_dir(user_id) / file_id

    def _part_path(self, user_id: str, file_id: str) -> Path:
        return self._user_dir(user_id) / f"{file_id}.part"

    async def write_stream(
        self,
        user_id: str,
        file_id: str,
        chunks: AsyncIterator[bytes],
    ) -> int:
        """流式写 .part → mv 到 final。异常时清 .part。返写入总字节数。"""
        part = self._part_path(user_id, file_id)
        final = self._final_path(user_id, file_id)
        total = 0
        try:
            with open(part, "wb") as f:
                async for chunk in chunks:
                    if chunk:
                        f.write(chunk)
                        total += len(chunk)
            os.rename(part, final)
            return total
        except BaseException:
            # 任何异常(含 KeyboardInterrupt)→ 删半文件
            try:
                if part.exists():
                    part.unlink()
            except OSError:
                pass
            raise

    async def read_stream(
        self,
        user_id: str,
        file_id: str,
        start: int = 0,
        end: int | None = None,
    ) -> AsyncIterator[bytes]:
        """读 [start, end] 闭区间(end=None → 到文件末尾)。"""
        path = self._final_path(user_id, file_id)
        size = path.stat().st_size
        if end is None or end >= size:
            end = size - 1
        if start > end:
            return
        remaining = end - start + 1
        with open(path, "rb") as f:
            f.seek(start)
            while remaining > 0:
                chunk = f.read(min(_CHUNK_READ, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    async def delete(self, user_id: str, file_id: str) -> None:
        path = self._final_path(user_id, file_id)
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    def exists(self, user_id: str, file_id: str) -> bool:
        return self._final_path(user_id, file_id).is_file()

    def get_size(self, user_id: str, file_id: str) -> int:
        return self._final_path(user_id, file_id).stat().st_size
```

- [ ] **Step 4: 跑测试确认绿**

```bash
pytest tests/test_files_store_fs.py -v
```

Expected: 8 PASS

- [ ] **Step 5: ruff + commit**

```bash
ruff check praxis2/files/store_fs.py tests/test_files_store_fs.py
git add praxis2/files/store_fs.py tests/test_files_store_fs.py
git commit -m "$(cat <<'EOF'
feat(M10/T5): files/store_fs.py — 流式 write + Range read + 异常 cleanup

布局:<root>/<user_id>/<file_id>(final)+ <file_id>.part(写中)。
write_stream:streaming write → atomic mv → final;异常 → unlink .part。
read_stream(start, end):闭区间,默认 0..size-1。
delete:幂等(文件不在不抛)。

跟 M11 spawn 任务无关:M11 carry 后台 GC 删 soft-deleted 文件。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `praxis2/files/repo.py` — FilesRepo CRUD

**Files:**
- Create: `praxis2/files/repo.py`
- Test: `tests/test_files_repo.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_files_repo.py
"""M10 FilesRepo integration 测试(需 PG)。"""
from __future__ import annotations

import os
import uuid

import pytest


pytestmark = pytest.mark.integration


@pytest.fixture
async def pool():
    pytest.importorskip("asyncpg")
    import asyncpg
    url = os.environ.get("PRAXIS_DB_URL", "")
    if not url:
        pytest.skip("PRAXIS_DB_URL not set")
    p = await asyncpg.create_pool(url.replace("postgresql+asyncpg://", "postgresql://"))
    yield p
    await p.close()


@pytest.fixture
async def user_id(pool):
    uid = uuid.uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id, email, password_hash, balance_li) VALUES ($1, $2, $3, 0)",
            uid, f"t_{uid}@x", b"x",
        )
    yield str(uid)
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM files WHERE user_id=$1", uid)
        await conn.execute("DELETE FROM users WHERE id=$1", uid)


async def test_create_file_returns_uuid_and_persists(pool, user_id):
    from praxis2.files.repo import FilesRepo
    r = FilesRepo(pool)
    row = await r.create_file(
        user_id=user_id, filename="x.pdb", size_bytes=100,
        mime="chemical/x-pdb", purpose="pdb",
        storage_key=f"fs:{user_id}/<file_id>",
    )
    assert row["id"]
    assert row["filename"] == "x.pdb"
    assert row["size_bytes"] == 100


async def test_list_files_filters_by_purpose(pool, user_id):
    from praxis2.files.repo import FilesRepo
    r = FilesRepo(pool)
    await r.create_file(user_id=user_id, filename="a.pdb", size_bytes=10,
                        mime=None, purpose="pdb", storage_key="fs:x/a")
    await r.create_file(user_id=user_id, filename="b.json", size_bytes=20,
                        mime=None, purpose="config", storage_key="fs:x/b")

    pdbs = await r.list_files(user_id=user_id, purpose="pdb")
    configs = await r.list_files(user_id=user_id, purpose="config")
    all_files = await r.list_files(user_id=user_id, purpose=None)

    assert len(pdbs) == 1
    assert pdbs[0]["filename"] == "a.pdb"
    assert len(configs) == 1
    assert len(all_files) == 2


async def test_list_files_excludes_soft_deleted(pool, user_id):
    from praxis2.files.repo import FilesRepo
    r = FilesRepo(pool)
    row = await r.create_file(user_id=user_id, filename="a.pdb", size_bytes=10,
                              mime=None, purpose="pdb", storage_key="fs:x/a")
    await r.soft_delete(user_id=user_id, file_id=row["id"])

    rows = await r.list_files(user_id=user_id, purpose=None)
    assert rows == []


async def test_soft_delete_returns_id_or_none(pool, user_id):
    from praxis2.files.repo import FilesRepo
    r = FilesRepo(pool)
    row = await r.create_file(user_id=user_id, filename="a.pdb", size_bytes=10,
                              mime=None, purpose="pdb", storage_key="fs:x/a")
    ok = await r.soft_delete(user_id=user_id, file_id=row["id"])
    assert ok is not None

    # 再删一次 → 404
    again = await r.soft_delete(user_id=user_id, file_id=row["id"])
    assert again is None


async def test_soft_delete_other_user_returns_none(pool, user_id):
    from praxis2.files.repo import FilesRepo
    r = FilesRepo(pool)
    row = await r.create_file(user_id=user_id, filename="a.pdb", size_bytes=10,
                              mime=None, purpose="pdb", storage_key="fs:x/a")
    fake_uid = str(uuid.uuid4())
    result = await r.soft_delete(user_id=fake_uid, file_id=row["id"])
    assert result is None


async def test_get_file_returns_row_or_none(pool, user_id):
    from praxis2.files.repo import FilesRepo
    r = FilesRepo(pool)
    row = await r.create_file(user_id=user_id, filename="a.pdb", size_bytes=10,
                              mime=None, purpose="pdb", storage_key="fs:x/a")
    got = await r.get_file(user_id=user_id, file_id=row["id"])
    assert got is not None
    assert got["filename"] == "a.pdb"

    # 不存在
    fake_fid = str(uuid.uuid4())
    none_row = await r.get_file(user_id=user_id, file_id=fake_fid)
    assert none_row is None


async def test_get_file_returns_none_after_soft_delete(pool, user_id):
    from praxis2.files.repo import FilesRepo
    r = FilesRepo(pool)
    row = await r.create_file(user_id=user_id, filename="a.pdb", size_bytes=10,
                              mime=None, purpose="pdb", storage_key="fs:x/a")
    await r.soft_delete(user_id=user_id, file_id=row["id"])
    got = await r.get_file(user_id=user_id, file_id=row["id"])
    assert got is None


async def test_usage_sums_only_active(pool, user_id):
    from praxis2.files.repo import FilesRepo
    r = FilesRepo(pool)
    a = await r.create_file(user_id=user_id, filename="a.pdb", size_bytes=100,
                            mime=None, purpose="pdb", storage_key="fs:x/a")
    await r.create_file(user_id=user_id, filename="b.json", size_bytes=200,
                        mime=None, purpose="config", storage_key="fs:x/b")
    await r.soft_delete(user_id=user_id, file_id=a["id"])

    usage = await r.usage(user_id=user_id)
    assert usage["used_bytes"] == 200   # a 已 soft-delete,只算 b
    assert usage["count"] == 1


async def test_usage_zero_for_new_user(pool, user_id):
    from praxis2.files.repo import FilesRepo
    r = FilesRepo(pool)
    usage = await r.usage(user_id=user_id)
    assert usage == {"used_bytes": 0, "count": 0}


async def test_create_file_with_invalid_purpose_raises(pool, user_id):
    from praxis2.files.repo import FilesRepo
    import asyncpg
    r = FilesRepo(pool)
    with pytest.raises((asyncpg.CheckViolationError, asyncpg.PostgresError)):
        await r.create_file(user_id=user_id, filename="x", size_bytes=10,
                            mime=None, purpose="invalid_purpose",
                            storage_key="fs:x/y")
```

- [ ] **Step 2: 跑测试确认红(integration 自动 SKIP if no PG)**

```bash
pytest tests/test_files_repo.py -v 2>&1 | tail -10
```

Expected: 10 SKIP(无 `PRAXIS_INTEGRATION` / `PRAXIS_DB_URL`)。本地有 docker 时:`PRAXIS_INTEGRATION=1 PRAXIS_DB_URL=... pytest tests/test_files_repo.py -v` 期望 10 FAIL with `ModuleNotFoundError`。

- [ ] **Step 3: 实现 — `praxis2/files/repo.py`**

```python
# praxis2/files/repo.py
"""FilesRepo:asyncpg CRUD against `files` 表。

list_files / create_file / get_file / soft_delete / usage。
软删用 deleted_at IS NULL 过滤;fs 实物由 FsStore 管,本模块不碰。
"""

from __future__ import annotations

import uuid
from typing import Any

import asyncpg


class FilesRepo:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_file(
        self,
        *,
        user_id: str,
        filename: str,
        size_bytes: int,
        mime: str | None,
        purpose: str,
        storage_key: str,
    ) -> dict[str, Any]:
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO files
                       (user_id, filename, size_bytes, mime, purpose, storage_key)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   RETURNING id, filename, size_bytes, mime, purpose,
                             storage_key, created_at""",
                uid, filename, int(size_bytes), mime, purpose, storage_key,
            )
        return _row_to_dict(row)

    async def list_files(
        self, *, user_id: str, purpose: str | None,
    ) -> list[dict[str, Any]]:
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        if purpose is None:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT id, filename, size_bytes, mime, purpose,
                              storage_key, created_at FROM files
                       WHERE user_id=$1 AND deleted_at IS NULL
                       ORDER BY created_at DESC""",
                    uid,
                )
        else:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT id, filename, size_bytes, mime, purpose,
                              storage_key, created_at FROM files
                       WHERE user_id=$1 AND purpose=$2 AND deleted_at IS NULL
                       ORDER BY created_at DESC""",
                    uid, purpose,
                )
        return [_row_to_dict(r) for r in rows]

    async def get_file(
        self, *, user_id: str, file_id: str,
    ) -> dict[str, Any] | None:
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        try:
            fid = uuid.UUID(file_id) if isinstance(file_id, str) else file_id
        except ValueError:
            return None
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT id, filename, size_bytes, mime, purpose,
                          storage_key, created_at FROM files
                   WHERE id=$1 AND user_id=$2 AND deleted_at IS NULL""",
                fid, uid,
            )
        return _row_to_dict(row) if row else None

    async def soft_delete(
        self, *, user_id: str, file_id: str,
    ) -> str | None:
        """返被删的 file_id;不归属当前用户 / 已删 → None。"""
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        try:
            fid = uuid.UUID(file_id) if isinstance(file_id, str) else file_id
        except ValueError:
            return None
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """UPDATE files SET deleted_at=now()
                   WHERE id=$1 AND user_id=$2 AND deleted_at IS NULL
                   RETURNING id""",
                fid, uid,
            )
        return str(row["id"]) if row else None

    async def usage(self, *, user_id: str) -> dict[str, int]:
        """返 {used_bytes, count}。"""
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT COALESCE(SUM(size_bytes), 0) AS used_bytes,
                          COUNT(*) AS cnt
                   FROM files WHERE user_id=$1 AND deleted_at IS NULL""",
                uid,
            )
        return {"used_bytes": int(row["used_bytes"]), "count": int(row["cnt"])}


def _row_to_dict(r) -> dict[str, Any]:
    return {
        "id": str(r["id"]),
        "filename": r["filename"],
        "size_bytes": int(r["size_bytes"]),
        "mime": r["mime"],
        "purpose": r["purpose"],
        "storage_key": r["storage_key"],
        "created_at": r["created_at"],
    }
```

- [ ] **Step 4: 跑测试确认绿(SKIP / PASS 取决于 docker)**

```bash
pytest tests/test_files_repo.py -v 2>&1 | tail -5
```

Expected: 10 SKIP(本机无 docker)或 10 PASS(有 docker)。**不 FAIL**。

- [ ] **Step 5: ruff + commit**

```bash
ruff check praxis2/files/repo.py tests/test_files_repo.py
git add praxis2/files/repo.py tests/test_files_repo.py
git commit -m "$(cat <<'EOF'
feat(M10/T6): files/repo.py — FilesRepo 5 方法 CRUD + 10 integration tests

create_file / list_files (with purpose filter) / get_file /
soft_delete / usage。

软删返被删 id 或 None;list/get 都 WHERE deleted_at IS NULL;
usage 用 COALESCE(SUM,0) 防空集 NULL。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: `praxis2/files/multipart_stream.py` — 流式 parser

**Files:**
- Create: `praxis2/files/multipart_stream.py`
- Test: `tests/test_files_multipart_stream.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_files_multipart_stream.py
"""M10 files multipart_stream:python-multipart 流式 parser 包装。"""
from __future__ import annotations

import pytest


def _build_multipart_body(
    boundary: bytes, filename: bytes, content: bytes,
    content_type: bytes = b"application/octet-stream",
) -> bytes:
    """构造一个最小 multipart/form-data body,只含一个 file field。"""
    return (
        b"--" + boundary + b"\r\n"
        + b'Content-Disposition: form-data; name="file"; filename="' + filename + b'"\r\n'
        + b"Content-Type: " + content_type + b"\r\n\r\n"
        + content + b"\r\n"
        + b"--" + boundary + b"--\r\n"
    )


def _mk_receive(body: bytes, chunk_size: int = 1024):
    """ASGI receive 模拟,分块发 body。"""
    chunks = [body[i:i+chunk_size] for i in range(0, len(body), chunk_size)]
    chunks.append(b"")   # 收尾空块表示 more_body=False
    iter_chunks = iter(chunks)

    async def receive():
        try:
            chunk = next(iter_chunks)
            more = chunk != b"" or next(iter_chunks, None) is not None
            return {"type": "http.request", "body": chunk, "more_body": more}
        except StopIteration:
            return {"type": "http.request", "body": b"", "more_body": False}
    return receive


async def test_parse_upload_returns_filename_and_chunks():
    from praxis2.files.multipart_stream import parse_upload

    boundary = b"BOUNDARY_TEST_X"
    body = _build_multipart_body(boundary, b"test.pdb", b"hello world")
    headers = [(b"content-type", b"multipart/form-data; boundary=" + boundary)]

    result = await parse_upload(_mk_receive(body), headers)
    assert result["filename"] == "test.pdb"
    chunks = b""
    async for c in result["body_iter"]:
        chunks += c
    assert chunks == b"hello world"


async def test_parse_upload_streams_large_body():
    """模拟 100 KB body,分多 chunk receive,parser 流式 yield 出来。"""
    from praxis2.files.multipart_stream import parse_upload

    boundary = b"BOUNDARY_BIG"
    content = b"x" * (100 * 1024)
    body = _build_multipart_body(boundary, b"big.bin", content)
    headers = [(b"content-type", b"multipart/form-data; boundary=" + boundary)]

    result = await parse_upload(_mk_receive(body, chunk_size=4096), headers)
    total = 0
    async for c in result["body_iter"]:
        total += len(c)
    assert total == 100 * 1024
    assert result["filename"] == "big.bin"


async def test_parse_upload_missing_boundary_raises():
    from praxis2.files.multipart_stream import parse_upload, MultipartError

    headers = [(b"content-type", b"multipart/form-data")]   # 无 boundary
    with pytest.raises(MultipartError):
        await parse_upload(_mk_receive(b""), headers)


async def test_parse_upload_no_file_field_raises():
    from praxis2.files.multipart_stream import parse_upload, MultipartError

    boundary = b"BOUNDARY"
    # body 里没有 file field,只是空 multipart
    body = b"--" + boundary + b"--\r\n"
    headers = [(b"content-type", b"multipart/form-data; boundary=" + boundary)]

    result = await parse_upload(_mk_receive(body), headers)
    # 消费 iter — 应当抛 / 或 filename 为 None
    with pytest.raises(MultipartError):
        async for _ in result["body_iter"]:
            pass
```

- [ ] **Step 2: 跑测试确认红**

```bash
pytest tests/test_files_multipart_stream.py -v
```

Expected: 4 FAIL — `ModuleNotFoundError`。

- [ ] **Step 3: 实现 — `praxis2/files/multipart_stream.py`**

```python
# praxis2/files/multipart_stream.py
"""multipart/form-data 流式 parser(python-multipart 包装)。

ASGI receive → multipart parser → async iter chunks。RFC 7578。
设计:接收方按 receive() 拿小块,push 进 parser,parser 调
on_part_data 回调把 file chunks 推到一个 asyncio.Queue,消费方
async for 拿到 chunks 写 fs。
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, AsyncIterator


class MultipartError(Exception):
    """multipart 解析错误:无 boundary / 无 file field / 解析中断。"""


_BOUNDARY_RE = re.compile(rb"boundary=([^;]+)")


def _extract_boundary(content_type: bytes) -> bytes:
    m = _BOUNDARY_RE.search(content_type)
    if not m:
        raise MultipartError("missing boundary in Content-Type")
    return m.group(1).strip(b'"').strip()


async def parse_upload(
    receive,
    headers: list[tuple[bytes, bytes]],
) -> dict[str, Any]:
    """返 {filename, content_type, body_iter}。

    body_iter 是 async generator,yield file 内容 chunks。
    """
    # 找 Content-Type header
    ct = b""
    for k, v in headers:
        if k.lower() == b"content-type":
            ct = v
            break
    if not ct.startswith(b"multipart/form-data"):
        raise MultipartError(f"not multipart: {ct!r}")
    boundary = _extract_boundary(ct)

    from multipart import multipart as mp_lib

    state: dict[str, Any] = {
        "filename": None,
        "content_type": None,
        "in_file": False,
        "done": False,
    }
    queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    # ── 回调 ─────────────────────────────────────────────
    current_field_name = []   # 用 list 包成 mutable

    def on_field_start():
        current_field_name.append(None)

    def on_field_name(data, start, end):
        # 多 chunk 累加 name
        if current_field_name[-1] is None:
            current_field_name[-1] = bytes(data[start:end])
        else:
            current_field_name[-1] += bytes(data[start:end])

    def on_field_data(data, start, end):
        pass   # 不是 file field 的 data 忽略

    def on_field_end():
        current_field_name.clear()

    def on_part_begin():
        state["in_file"] = False

    def on_header_field(data, start, end):
        pass

    def on_header_value(data, start, end):
        pass

    def on_header_end():
        pass

    def on_headers_finished():
        # 检 headers 里有没有 filename + Content-Type
        # python-multipart 暴露 disposition via parser.headers
        pass

    def on_part_data(data, start, end):
        if state["in_file"]:
            queue.put_nowait(bytes(data[start:end]))

    def on_part_end():
        if state["in_file"]:
            queue.put_nowait(None)   # EOF marker
            state["done"] = True

    def on_end():
        if not state["done"]:
            # 没 file part → 错
            queue.put_nowait(b"__ERROR__no_file_field__")

    # 用 MultipartParser 直接(不走 form parser 高级 API,我们要 streaming)
    parser = mp_lib.MultipartParser(
        boundary.decode("ascii"),
        callbacks={
            "on_part_begin":   on_part_begin,
            "on_part_data":    on_part_data,
            "on_part_end":     on_part_end,
            "on_header_field": on_header_field,
            "on_header_value": on_header_value,
            "on_header_end":   on_header_end,
            "on_headers_finished": on_headers_finished,
            "on_end":          on_end,
        },
    )

    # 我们需要从 part headers 里抽 filename 和 Content-Type。
    # 简单做法:在 on_headers_finished 时 parser.exit_state 已经把 raw header
    # 暴露给我们 — 但 python-multipart 不直接;改用替代方案:
    # 直接预扫 raw body 拿第一个 part 的 Content-Disposition。

    # ── 子进程 task:拉 receive,push 进 parser ─────────────
    async def pump():
        try:
            buf = b""
            header_done = False
            while True:
                msg = await receive()
                chunk = msg.get("body", b"")
                if chunk:
                    if not header_done:
                        buf += chunk
                        # 找两次 \r\n\r\n,第一次是第一 part headers 结束
                        idx = buf.find(b"\r\n\r\n")
                        if idx > 0:
                            # 解析 disposition
                            header_block = buf[:idx]
                            m = re.search(
                                rb'filename="([^"]+)"', header_block,
                            )
                            if m:
                                state["filename"] = m.group(1).decode(
                                    "utf-8", errors="replace")
                                state["in_file"] = True
                            ct_m = re.search(
                                rb"Content-Type:\s*(\S+)", header_block,
                            )
                            if ct_m:
                                state["content_type"] = ct_m.group(1).decode(
                                    "ascii", errors="replace")
                            header_done = True
                            # 把这一坨 push 进 parser
                            parser.write(buf)
                            buf = b""
                        # else: 还没找全,接着等
                    else:
                        parser.write(chunk)
                if not msg.get("more_body", False):
                    parser.finalize()
                    queue.put_nowait(None)
                    break
        except Exception as e:
            queue.put_nowait(b"__ERROR__" + str(e).encode())

    pump_task = asyncio.create_task(pump())

    async def body_iter() -> AsyncIterator[bytes]:
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            if isinstance(chunk, bytes) and chunk.startswith(b"__ERROR__"):
                raise MultipartError(chunk[len(b"__ERROR__"):].decode())
            yield chunk
        await pump_task   # wait clean shutdown

    # 第一次拉 receive 直到拿到 filename(让调用方拿到 metadata)
    # 但我们已经在 pump 里做了 — 等 pump 解析到 filename
    while not state["in_file"] and not state["done"]:
        await asyncio.sleep(0.001)
        if pump_task.done():
            # pump 结束了还没 file → 没 file field
            raise MultipartError("no file field in multipart body")

    if state["filename"] is None:
        raise MultipartError("no filename in Content-Disposition")

    return {
        "filename": state["filename"],
        "content_type": state["content_type"],
        "body_iter": body_iter(),
    }
```

> ⚠️ **实施注意**:python-multipart 的 callback API 在不同版本变化。此实现以 0.0.9 为准。若 production 装的是 0.0.20+,可能需要按新 API 调:`from multipart import MultipartParser` 直接 instantiate。**Plan 实施者:如果版本不匹配,先 `pip show python-multipart` 确认版本,然后参考 README 调用方式。** 备用方案:直接读 ASGI body 自行解析 boundary(纯 stdlib ~150 行,RFC 7578)— 但优先用 python-multipart 节省维护。

- [ ] **Step 4: 跑测试确认绿**

```bash
# 先确保 python-multipart 装了(T1 在 pyproject + push_backend 已加,但本机可能没装)
pip install python-multipart>=0.0.9
pytest tests/test_files_multipart_stream.py -v
```

Expected: 4 PASS。

> 如果 PASS < 4,可能是 python-multipart API 版本差异。看 error trace,按版本 README 调整 callback 名/签名,**不退化为读全 body 到内存**。

- [ ] **Step 5: ruff + commit**

```bash
ruff check praxis2/files/multipart_stream.py tests/test_files_multipart_stream.py
git add praxis2/files/multipart_stream.py tests/test_files_multipart_stream.py
git commit -m "$(cat <<'EOF'
feat(M10/T7): files/multipart_stream.py — python-multipart 流式包装

ASGI receive → MultipartParser callbacks → asyncio.Queue → async iter。
不读全 body 到内存,适配 20GB 上传。
预扫第一个 part headers 抽 filename + Content-Type。
4 个 happy/sad path 测试覆盖。

MultipartError:missing boundary / no file field / parse fail。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: `praxis2/brains/profile.py` — brain 资料卡 loader

**Files:**
- Create: `praxis2/brains/profile.py`
- Create(测试 fixture brain):`tests/fixtures/brains_m10/*`(若有需要)
- Test: `tests/test_brains_profile.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_brains_profile.py
"""M10 brains/profile.py — 13 brain walk + metadata.yaml + sample_cases。"""
from __future__ import annotations

from praxis2.brains.migrate import DISCIPLINE_SLUGS


def test_load_all_profiles_returns_13_slugs():
    from praxis2.brains.profile import load_all_profiles
    profiles = load_all_profiles()
    assert set(profiles.keys()) == set(DISCIPLINE_SLUGS)
    assert len(profiles) == 13


def test_profile_has_required_fields():
    from praxis2.brains.profile import load_all_profiles
    profiles = load_all_profiles()
    for slug, prof in profiles.items():
        # 6 个字段必须在(从 brain 文件树推理出的)
        for key in ("case_count", "rule_count", "skill_workflows",
                    "sample_cases", "short_prompt", "methods",
                    "helps_with", "delivers"):
            assert key in prof, f"{slug} missing {key}"


def test_profile_case_count_is_int():
    from praxis2.brains.profile import load_all_profiles
    profiles = load_all_profiles()
    for slug, prof in profiles.items():
        assert isinstance(prof["case_count"], int)
        assert prof["case_count"] >= 0


def test_profile_skill_workflows_is_sorted_list():
    from praxis2.brains.profile import load_all_profiles
    profiles = load_all_profiles()
    for slug, prof in profiles.items():
        wfs = prof["skill_workflows"]
        assert isinstance(wfs, list)
        assert wfs == sorted(wfs)


def test_profile_sample_cases_at_most_5():
    from praxis2.brains.profile import load_all_profiles
    profiles = load_all_profiles()
    for slug, prof in profiles.items():
        sc = prof["sample_cases"]
        assert isinstance(sc, list)
        assert len(sc) <= 5
        for c in sc:
            assert "case_id" in c
            assert "title" in c
            assert "file" in c


def test_profile_text_fields_returned_empty_when_no_metadata_yaml(tmp_path, monkeypatch):
    """没 metadata.yaml 的 brain:short_prompt='' / methods=[] / helps_with=[] / delivers=[]。"""
    from praxis2.brains.profile import _walk_brain
    # 造一个 fixture brain 目录
    brain_dir = tmp_path / "_brains" / "dummy"
    (brain_dir / "memory" / "cases").mkdir(parents=True)
    (brain_dir / "memory" / "rules").mkdir(parents=True)
    (brain_dir / "skills" / "workflows").mkdir(parents=True)

    prof = _walk_brain("dummy", root=tmp_path)
    assert prof["short_prompt"] == ""
    assert prof["methods"] == []
    assert prof["helps_with"] == []
    assert prof["delivers"] == []


def test_profile_metadata_yaml_loaded_when_present(tmp_path):
    """有 metadata.yaml:4 个字段从 yaml 拿。"""
    import yaml
    from praxis2.brains.profile import _walk_brain
    brain_dir = tmp_path / "_brains" / "dummy2"
    (brain_dir / "memory" / "cases").mkdir(parents=True)
    metadata = {
        "short_prompt": "Dummy 测试用",
        "methods": ["antiSMASH", "cobra"],
        "helps_with": ["通路设计"],
        "delivers": ["JSON 报告"],
    }
    (brain_dir / "metadata.yaml").write_text(
        yaml.safe_dump(metadata, allow_unicode=True), encoding="utf-8",
    )

    prof = _walk_brain("dummy2", root=tmp_path)
    assert prof["short_prompt"] == "Dummy 测试用"
    assert prof["methods"] == ["antiSMASH", "cobra"]
    assert prof["helps_with"] == ["通路设计"]
    assert prof["delivers"] == ["JSON 报告"]
```

- [ ] **Step 2: 跑测试确认红**

```bash
pytest tests/test_brains_profile.py -v
```

Expected: 7 FAIL — `ImportError` 或 `AttributeError`。

- [ ] **Step 3: 实现 — `praxis2/brains/profile.py`**

```python
# praxis2/brains/profile.py
"""brain 资料卡 loader — 启动一次 walk 13 学科,module-level cache。

`load_all_profiles()` 返 dict[slug, profile_dict],每个 profile 含:
- case_count / rule_count / skill_workflows / sample_cases
  (从 brains/<slug>/ 目录推理)
- short_prompt / methods / helps_with / delivers
  (从 brains/<slug>/metadata.yaml,缺 → 空)

改 brain 文件 → 重启 backend 才会重新 load。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from praxis2.brains.migrate import DISCIPLINE_SLUGS

# 默认 brain root:仓内 brains/<slug>/。生产可由 env PRAXIS_BRAINS_ROOT 覆盖。
_DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "brains"


_CACHE: dict[str, dict[str, Any]] | None = None


def load_all_profiles(*, root: Path | None = None) -> dict[str, dict[str, Any]]:
    """惰性初始化 module-level cache;后续调用 O(1)。"""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    actual_root = root or _DEFAULT_ROOT
    _CACHE = {slug: _walk_brain(slug, root=actual_root) for slug in DISCIPLINE_SLUGS}
    return _CACHE


def reset_cache_for_tests() -> None:
    """测试用:清缓存让下次 walk 重读。"""
    global _CACHE
    _CACHE = None


def _walk_brain(slug: str, *, root: Path) -> dict[str, Any]:
    brain_dir = root / slug
    case_count = _count_files(brain_dir / "memory" / "cases", "*.md")
    rule_count = _count_lines_in_files(brain_dir / "memory" / "rules", "*.md")
    skill_workflows = _list_workflow_dirs(brain_dir / "skills" / "workflows")
    sample_cases = _top_5_cases(brain_dir / "memory" / "cases", slug)
    yaml_data = _load_metadata_yaml(brain_dir / "metadata.yaml")
    return {
        "case_count": case_count,
        "rule_count": rule_count,
        "skill_workflows": skill_workflows,
        "sample_cases": sample_cases,
        "short_prompt": yaml_data.get("short_prompt", ""),
        "methods": yaml_data.get("methods", []),
        "helps_with": yaml_data.get("helps_with", []),
        "delivers": yaml_data.get("delivers", []),
    }


def _count_files(dir_path: Path, pattern: str) -> int:
    if not dir_path.is_dir():
        return 0
    return sum(1 for _ in dir_path.glob(pattern))


def _count_lines_in_files(dir_path: Path, pattern: str) -> int:
    """粗略数 rule 数 — 每文件每行算 1 rule(实际可能多行 = 1 rule,粗估)。"""
    if not dir_path.is_dir():
        return 0
    total = 0
    for p in dir_path.glob(pattern):
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        total += 1
        except OSError:
            pass
    return total


def _list_workflow_dirs(dir_path: Path) -> list[str]:
    if not dir_path.is_dir():
        return []
    return sorted(
        d.name for d in dir_path.iterdir()
        if d.is_dir() and (d / "SKILL.md").is_file()
    )


def _top_5_cases(dir_path: Path, slug: str) -> list[dict[str, str]]:
    if not dir_path.is_dir():
        return []
    cases = sorted(
        dir_path.glob("*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:5]
    out = []
    for p in cases:
        title = _extract_title(p) or p.stem
        # case_id:文件名(不带后缀,如 "01-bgc-prioritize" → "01-bgc-prioritize")
        out.append({
            "case_id": p.stem,
            "title": title,
            "file": f"brains/{slug}/memory/cases/{p.name}",
        })
    return out


def _extract_title(path: Path) -> str | None:
    """从 case .md 头部读 `# 标题` 或 frontmatter `title: ...`。"""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("# "):
                    return line[2:].strip()
                if line.startswith("title:"):
                    return line.split(":", 1)[1].strip().strip('"\'')
                if line and not line.startswith("#"):
                    break
    except OSError:
        return None
    return None


def _load_metadata_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}
```

- [ ] **Step 4: 跑测试确认绿**

```bash
pytest tests/test_brains_profile.py -v
```

Expected: 7 PASS。

- [ ] **Step 5: ruff + commit**

```bash
ruff check praxis2/brains/profile.py tests/test_brains_profile.py
git add praxis2/brains/profile.py tests/test_brains_profile.py
git commit -m "$(cat <<'EOF'
feat(M10/T8): brains/profile.py — 13 brain walk + metadata.yaml + sample_cases

启动 lazy walk:
- case_count:cases/*.md 数
- rule_count:rules/*.md 行数粗估(非空非 # 行)
- skill_workflows:workflows/<x>/SKILL.md 存在的目录名(sorted)
- sample_cases:mtime DESC top 5,title 从 .md 头部 H1 / frontmatter
- 4 个文本字段(short_prompt/methods/helps_with/delivers)从
  brains/<slug>/metadata.yaml,缺 → 空。

Module-level cache;reset_cache_for_tests() 给测试清缓存用。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: `praxis2/server/routes/files.py` — 5 file handler + ROUTES

**Files:**
- Create: `praxis2/server/routes/files.py`
- Test: `tests/test_files_routes.py`(部分 — 上传 / 列表 / 删除 / 使用量 / 下载;agents/profile 在 T10)

- [ ] **Step 1: 写 5 个 handler 失败测试**

```python
# tests/test_files_routes.py
"""M10 files routes:5 endpoint × happy + error code + Range。"""
from __future__ import annotations

import json
import tempfile
import uuid
from datetime import datetime, UTC
from pathlib import Path

import pytest

from tests.test_auth_routes_v2_me import (
    _capture, _mk_receive, _mk_scope, _mk_userrow,
)
from tests.test_auth_routes import _make_deps


@pytest.fixture
def files_deps():
    """测试 files deps:repo=Fake + fs_store=临时目录 + settings。"""
    import asyncio
    import shutil
    deps = asyncio.run(_make_deps())   # 复用 M9 deps
    root = tempfile.mkdtemp(prefix="praxis2_files_test_")
    from praxis2.files.store_fs import FsStore
    fs = FsStore(root)

    # Fake FilesRepo:in-memory
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

    deps["files_repo"] = _FakeFilesRepo()
    deps["fs_store"] = fs
    yield deps
    shutil.rmtree(root, ignore_errors=True)


async def test_list_files_empty(files_deps):
    from praxis2.server.routes.files import handle_files_list
    files_deps["repo"]._users["uid-l1"] = _mk_userrow(id="uid-l1", email="l1@x")
    scope = _mk_scope("GET", "/api/files", user={"user_id": "uid-l1"})
    status, body, _ = await _capture(handle_files_list, scope, _mk_receive(), files_deps)
    assert status == 200
    assert body == {"files": []}


async def test_usage_empty(files_deps):
    from praxis2.server.routes.files import handle_files_usage
    files_deps["repo"]._users["uid-u1"] = _mk_userrow(id="uid-u1", email="u1@x")
    scope = _mk_scope("GET", "/api/files/usage", user={"user_id": "uid-u1"})
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
    scope = _mk_scope("GET", "/api/files?purpose=__INVALID__",
                       user={"user_id": "uid-p1"})
    # query 解析:handler 自己从 scope query_string 抽 purpose
    scope_with_qs = {**scope, "query_string": b"purpose=__INVALID__"}
    status, body, _ = await _capture(
        handle_files_list, scope_with_qs, _mk_receive(), files_deps,
    )
    assert status == 400
    assert body["error"] == "invalid_purpose"


async def test_delete_404_when_not_found(files_deps):
    from praxis2.server.routes.files import handle_files_delete
    files_deps["repo"]._users["uid-d1"] = _mk_userrow(id="uid-d1", email="d1@x")
    fake_fid = str(uuid.uuid4())
    scope = _mk_scope("DELETE", f"/api/files/{fake_fid}",
                       user={"user_id": "uid-d1"})
    # handler 自己从 scope path 解 file_id
    scope_with_path = {**scope, "path_params": {"file_id": fake_fid}}
    status, body, _ = await _capture(
        handle_files_delete, scope_with_path, _mk_receive(), files_deps,
    )
    assert status == 404


async def test_delete_happy(files_deps):
    from praxis2.server.routes.files import handle_files_delete
    files_deps["repo"]._users["uid-d2"] = _mk_userrow(id="uid-d2", email="d2@x")
    # 先造一个 file row in fake repo
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


# 上传 happy/sad path:用真 multipart body
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


async def test_upload_size_too_large_413(files_deps):
    from praxis2.server.routes.files import handle_files_upload
    files_deps["repo"]._users["uid-up2"] = _mk_userrow(id="uid-up2", email="up2@x")
    # 把 settings.max_per_file_bytes 调到 5 字节看会不会 413
    files_deps["settings"].files_max_per_file_bytes = 5

    boundary = b"B"
    body = _build_multipart_body(boundary, b"big.bin", b"x" * 100)
    chunks = iter([
        {"type": "http.request", "body": body, "more_body": False},
    ])
    async def receive():
        return next(chunks)
    scope = {"type": "http", "method": "POST",
             "path": "/api/files", "headers": [
                 (b"content-type", b"multipart/form-data; boundary=" + boundary),
             ],
             "query_string": b"purpose=other",
             "user": {"user_id": "uid-up2"}}
    status, resp, _ = await _capture(
        handle_files_upload, scope, receive, files_deps,
    )
    assert status == 413
    assert resp["error"] == "file_too_large"
```

- [ ] **Step 2: 跑测试确认红**

```bash
pytest tests/test_files_routes.py -v 2>&1 | tail -10
```

Expected: 7 FAIL — `ModuleNotFoundError: praxis2.server.routes.files`。

- [ ] **Step 3: 实现 — `praxis2/server/routes/files.py`**

```python
# praxis2/server/routes/files.py
"""M10 files routes:5 endpoint + 1 agents/profile (T10 加)。

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

# spec §0 #5 五个枚举
_PURPOSES = {"pdb", "config", "report", "md_input", "other"}


# ── 小工具(若 routes/__init__.py 没暴露,这里本地造) ──────────────

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


def _path_file_id(scope) -> str:
    """从 path /api/files/{id} 或 /api/files/{id}/content 抽 id。"""
    pp = scope.get("path_params")
    if pp and "file_id" in pp:
        return pp["file_id"]
    # fallback:从 scope["path"] 解
    path = scope.get("path", "")
    parts = path.split("/")
    # /api/files/<id> 或 /api/files/<id>/content
    if len(parts) >= 4 and parts[1] == "api" and parts[2] == "files":
        return parts[3]
    return ""


# ── handlers ─────────────────────────────────────────────────────

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

    # 先查当前 usage(为后面 quota_exceeded 算)
    usage = await repo.usage(user_id=uid)
    quota = settings.files_quota_bytes
    used = usage["used_bytes"]

    # 解 multipart
    try:
        parsed = await parse_upload(receive, scope["headers"])
    except MultipartError as e:
        await _json(send, 400, {"error": "bad_multipart", "reason": str(e)})
        return

    filename = sanitize_filename(parsed["filename"] or "unnamed")
    storage_key = f"fs:{uid}/{fid}"

    # 流式写,边写边检 max + quota
    written = [0]
    aborted = [False]

    async def gated_chunks():
        async for chunk in parsed["body_iter"]:
            written[0] += len(chunk)
            if written[0] > max_size:
                aborted[0] = True
                raise _UploadLimit("file_too_large", {"limit_bytes": max_size})
            if used + written[0] > quota:
                aborted[0] = True
                raise _UploadLimit("quota_exceeded", {
                    "used_bytes": used, "quota_bytes": quota,
                })
            yield chunk

    # spec §5.1 carry:同用户并发 upload 应取 pg_advisory_xact_lock
    # (hashtext('upload:'||user_id)) 防 quota 绕过。M10 单 worker
    # gunicorn = 2 workers,真有并发概率低,M10.5 carry。
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

    # 用 magic 检 mime(读 fs 实际内容)
    final_path = fs_store._final_path(uid, fid)
    mime = detect_mime(str(final_path))

    # 写 DB
    try:
        row = await repo.create_file(
            user_id=uid, filename=filename, size_bytes=size,
            mime=mime, purpose=purpose, storage_key=storage_key,
        )
    except Exception as e:
        # DB 写失败 → 删 fs
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


class _UploadLimit(Exception):
    def __init__(self, code: str, detail: dict) -> None:
        self.code = code
        self.detail = detail


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
    fs_store = deps["fs_store"]
    if not fs_store.exists(user["user_id"], file_id):
        await _json(send, 404, {"error": "not_found"})
        return
    size = fs_store.get_size(user["user_id"], file_id)
    mime = (row["mime"] or "application/octet-stream").encode("ascii", "replace")
    filename = sanitize_filename(row["filename"])

    # 解 Range header
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
             f'attachment; filename="{filename}"'.encode("utf-8")),
        ]
        body_start, body_end = start, end
    else:
        status = 200
        headers = [
            (b"content-type", mime),
            (b"content-length", str(size).encode()),
            (b"accept-ranges", b"bytes"),
            (b"content-disposition",
             f'attachment; filename="{filename}"'.encode("utf-8")),
        ]
        body_start, body_end = 0, size - 1

    await send({"type": "http.response.start", "status": status,
                "headers": headers})
    async for chunk in fs_store.read_stream(
        user["user_id"], file_id, start=body_start, end=body_end,
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
            # 'bytes=-N' = 最后 N 字节
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


# ── ROUTES dict ──────────────────────────────────────────────────

ROUTES: dict[tuple[str, str], str] = {
    ("/api/files", "GET"): "handle_files_list",
    ("/api/files", "POST"): "handle_files_upload",
    ("/api/files/usage", "GET"): "handle_files_usage",
    # 动态路径 /api/files/{id} 不能用 dict 静态注册,需要 wildcard 匹配。
    # spec §4.4 / §4.6 的 path 含 {file_id}:DELETE /api/files/{id} 和 GET /api/files/{id}/content
    # app.py 那边匹配需要 prefix + 解析。这两条不进 ROUTES,改在 app.py 里 dispatch 时判断 prefix。
}
```

> ⚠️ **关键设计 issue**:`/api/files/{id}` 和 `/api/files/{id}/content` 是动态路径,M9 的 `_routes: dict[tuple,str]` 静态匹配吃不下。
> **方案**:在 `app.py._App.__call__` 已有的 dispatch 之前,加一个 prefix 匹配层:
> ```python
> # /api/files/<uuid> 或 /api/files/<uuid>/content
> if path.startswith("/api/files/") and path not in ("/api/files/usage",):
>     parts = path[len("/api/files/"):].split("/")
>     if len(parts) == 1 and method == "DELETE":
>         scope["path_params"] = {"file_id": parts[0]}
>         await handle_files_delete(scope, receive, send, files_deps)
>         return
>     elif len(parts) == 2 and parts[1] == "content" and method == "GET":
>         scope["path_params"] = {"file_id": parts[0]}
>         await handle_files_download(scope, receive, send, files_deps)
>         return
> ```
> 这个判断在 T11 app.py wire-up 时加。

- [ ] **Step 4: 跑测试确认绿**

```bash
pytest tests/test_files_routes.py -v
```

Expected: 7 PASS。

- [ ] **Step 5: ruff + commit**

```bash
ruff check praxis2/server/routes/files.py tests/test_files_routes.py
git add praxis2/server/routes/files.py tests/test_files_routes.py
git commit -m "$(cat <<'EOF'
feat(M10/T9): server/routes/files.py — 5 file handler + ROUTES + Range download

handler:
- handle_files_list:GET /api/files?purpose=,过滤 + 400 invalid_purpose
- handle_files_upload:POST /api/files?purpose=,流式 multipart + 413 size/quota
- handle_files_usage:GET /api/files/usage,字段 count(不是 files_count)
- handle_files_delete:DELETE /api/files/{id},404 not_found / 200 {ok:true}
- handle_files_download:GET /api/files/{id}/content,Range 206 / 416

ROUTES dict 只放静态路径(list/upload/usage),动态路径(delete/download)
由 app.py prefix dispatch(T11 加)。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: `praxis2/server/routes/files.py` — agents/profile handler

**Files:**
- Modify: `praxis2/server/routes/files.py`(append handler + ROUTES 加 1 行)
- Test: `tests/test_files_routes.py`(append 2 tests)

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_files_routes.py

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
        # spec §4.1 12 字段
        for k in ("slug", "name", "desc", "emoji", "examples",
                  "short_prompt", "methods", "case_count", "rule_count",
                  "skill_workflows", "sample_cases", "helps_with", "delivers"):
            assert k in p, f"{p.get('slug', '?')} missing {k}"
```

- [ ] **Step 2: 跑测试确认红**

```bash
pytest tests/test_files_routes.py -v -k agents_profile
```

Expected: 2 FAIL — `ImportError: cannot import name 'handle_agents_profile'`。

- [ ] **Step 3: 实现 — `praxis2/server/routes/files.py` append**

```python
# 末尾追加 handler:

async def handle_agents_profile(scope, receive, send, deps) -> None:
    """M10:返 13 学科 brain 资料卡。

    public endpoint(不要求登录,FE splash 阶段调)。
    """
    from praxis2.brains.profile import load_all_profiles
    from praxis2.brains.migrate import DISCIPLINE_SLUGS

    profiles_dict = load_all_profiles()

    # 5 字段从 _AGENT_META(server.app)
    from praxis2.server.app import _agent_meta

    out = []
    for slug in DISCIPLINE_SLUGS:
        base = _agent_meta(slug)
        prof = profiles_dict.get(slug, {})
        out.append({**base, **prof})
    await _json(send, 200, {"profiles": out})
```

ROUTES dict 加一行:

```python
ROUTES: dict[tuple[str, str], str] = {
    ("/api/files", "GET"): "handle_files_list",
    ("/api/files", "POST"): "handle_files_upload",
    ("/api/files/usage", "GET"): "handle_files_usage",
    ("/api/agents/profile", "GET"): "handle_agents_profile",   # ← 新加
}
```

- [ ] **Step 4: 跑测试确认绿**

```bash
pytest tests/test_files_routes.py -v -k agents_profile
pytest tests/test_files_routes.py -v   # 9 PASS 总
```

Expected: 2 + 7 = 9 PASS。

- [ ] **Step 5: ruff + commit**

```bash
ruff check praxis2/server/routes/files.py tests/test_files_routes.py
git add praxis2/server/routes/files.py tests/test_files_routes.py
git commit -m "$(cat <<'EOF'
feat(M10/T10): handle_agents_profile + ROUTES 加 1 行

返 13 学科 brain 资料卡 — 从 brains/profile.py module-level cache,
合并 _AGENT_META 的 5 字段 (slug/name/desc/emoji/examples)。

public endpoint:不要求登录。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: `praxis2/server/app.py` 注入 + ROUTES merge + 删 M9.1 stub

**Files:**
- Modify: `praxis2/server/app.py`
- Modify: `praxis2/auth/routes.py`

- [ ] **Step 1: 直接 implement — `praxis2/server/app.py`**

在 `_App.__init__` 里(M9 加的 `auth_deps = {...}` 之后),append:

```python
        # M10:FilesRepo + FsStore + brain profile boot
        from praxis2.files.repo import FilesRepo
        from praxis2.files.store_fs import FsStore
        from praxis2.brains.profile import load_all_profiles

        try:
            files_repo = FilesRepo(deps.repo._pool)
        except AttributeError:
            files_repo = None   # FakeAuthRepository 测试路径
        fs_store = FsStore(deps.settings.files_root)
        files_deps = {
            "repo":       deps.repo,
            "files_repo": files_repo,
            "fs_store":   fs_store,
            "settings":   deps.settings,
        }
        # boot 时 walk 13 brain 大脑(O(13 × ~10 文件 ≈ 130 reads,~5s)
        load_all_profiles()

        # merge M10 routes
        from praxis2.server.routes import files as files_routes
        for (path, method), handler_name in files_routes.ROUTES.items():
            handler_fn = getattr(files_routes, handler_name)
            self._routes[(path, method)] = self._make_files_handler(
                handler_fn, files_deps,
            )
        self._files_deps = files_deps   # 给动态路径 dispatch 用
```

加 helper(类内,放在 `_make_auth_handler` 附近):

```python
    def _make_files_handler(self, fn, files_deps):
        async def _wrapped(scope, receive, send):
            await fn(scope, receive, send, files_deps)
        return _wrapped
```

在 `_App.__call__` 里(`handler = self._routes.get(...)` **之前**)加动态路径 prefix dispatch:

```python
        # M10 dynamic paths:/api/files/{id} 和 /api/files/{id}/content
        if path.startswith("/api/files/") and path != "/api/files/usage":
            from praxis2.server.routes.files import (
                handle_files_delete, handle_files_download,
            )
            sub = path[len("/api/files/"):]
            parts = sub.split("/")
            if len(parts) == 1 and method == "DELETE":
                scope["path_params"] = {"file_id": parts[0]}
                await handle_files_delete(scope, receive, send,
                                            self._files_deps)
                return
            if len(parts) == 2 and parts[1] == "content" and method == "GET":
                scope["path_params"] = {"file_id": parts[0]}
                await handle_files_download(scope, receive, send,
                                              self._files_deps)
                return
        # 然后是已有的 handler = self._routes.get((path, method)) ...
```

- [ ] **Step 2: 删 M9.1 `handle_files_usage_stub`**

在 `praxis2/auth/routes.py` 删整段 `handle_files_usage_stub` 函数定义 + `ROUTES` 里那行 `("/api/files/usage", "GET"): "handle_files_usage_stub"`。

- [ ] **Step 3: 跑全测验证**

```bash
pytest -q tests/ -k "not integration" --ignore=tests/test_skills 2>&1 | tail -5
```

Expected: 全 PASS(M9 baseline 1570 + M10 新加 ≥ 36 = 1606+)。

- [ ] **Step 4: ruff**

```bash
ruff check praxis2/server/app.py praxis2/auth/routes.py
```

- [ ] **Step 5: Commit**

```bash
git add praxis2/server/app.py praxis2/auth/routes.py
git commit -m "$(cat <<'EOF'
feat(M10/T11): app.py 注入 FilesRepo/FsStore + ROUTES merge + 删 M9.1 stub

_App.__init__ 加:
- FilesRepo(deps.repo._pool)(FakeAuthRepository 测试路径 None)
- FsStore(settings.files_root)
- boot 时 load_all_profiles()(13 brain walk,~5s)
- merge files_routes.ROUTES 进 _routes(4 个静态路径)
- 动态路径 prefix dispatch:/api/files/{id} (DELETE) 和 /content (GET)

删 auth/routes.py:
- handle_files_usage_stub 整段(M9.1 字段 files_count 错位)
- ROUTES /api/files/usage 那行(M10 routes 已注册真版)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: 全测 + ruff + typecheck + 自审

**Files:** 无新建,验证

- [ ] **Step 1: pytest 全量**

```bash
cd /Volumes/T7/clade-learn/PRAXIS-2
pytest -q tests/ -k "not integration" --ignore=tests/test_skills 2>&1 | tail -10
```

Expected:
- ≥ 1606 passed(M9 1570 + ~36 M10 新增)
- 0 failed
- 18+ skipped(integration auto-skip)
- 26 xfailed

如有 FAIL,定位 + 修。

- [ ] **Step 2: ruff**

```bash
ruff check praxis2/ tests/ 2>&1 | tail -3
```

Expected: ≤ 10 errors(M9.1 baseline)。新引入的代码不应增 errors。

- [ ] **Step 3: FE typecheck + build**

```bash
cd frontend && npm run typecheck 2>&1 | tail -5
VITE_API_BASE='' npm run build 2>&1 | tail -5
ls dist/assets/index-*.js
```

Expected: 0 type errors, build success。FE 0 改 → 必通。

- [ ] **Step 4: spec 反查覆盖**

逐条对照 `docs/superpowers/specs/2026-05-25-m10-agents-files-design.md` §1 P0:
- [ ] 003 migration → T2
- [ ] FilesRepo CRUD → T6
- [ ] FsStore 流式 → T5
- [ ] mime / sanitize / multipart_stream → T3/T4/T7
- [ ] brain profile loader + metadata.yaml → T8
- [ ] 6 endpoint → T9 + T10(5 文件 + 1 profile)
- [ ] Config 3 env → T1
- [ ] M9.1 stub 删 → T11
- [ ] app.py wire-up → T11
- [ ] python-multipart/magic/yaml 依赖 → T1
- [ ] gunicorn timeout → T1

逐条对照 spec §6 测试覆盖(~36):
- T3 security 5、T4 mime 3、T5 store_fs 8、T6 repo 10、T7 multipart 4、T9+T10 routes 9、T8 profile 7 ≈ 46

- [ ] **Step 5: 无 commit(纯验证)**

---

## Task 13: Staging 部署 + smoke + tag v0.11.0

**Files:** 部署操作

⚠️ **DO NOT 触碰** `.40:8088` v1 / `.53:7788` v1 backend / 别的 .53 服务。仅动 `.53:8001` v2 + `.40:8080` 反代下的 `PRAXIS-2-fe/dist`。

- [ ] **Step 1: 装 libmagic1**

```bash
ssh zkyd@10.102.106.53 \
    'dpkg -l | grep -q libmagic1 || sudo apt-get install -y libmagic1'
ssh zkyd@10.102.106.53 \
    'python3 -c "import magic; print(magic.Magic(mime=True).from_buffer(b\"%PDF\"))"'
```

Expected: 不报错,返 `application/pdf` 或类似。

- [ ] **Step 2: rsync 后端**

```bash
cd /Volumes/T7/clade-learn/PRAXIS-2
rsync -avz --delete --partial --partial-dir=.rsync-partial \
    --exclude '__pycache__' --exclude '*.pyc' --exclude '.venv' \
    --exclude '._*' --exclude '.DS_Store' \
    praxis2/ zkyd@10.102.106.53:/home/zkyd/data1/mzy/PRAXIS-2/praxis2/
rsync -avz --delete --partial \
    --exclude '__pycache__' --exclude '*.pyc' \
    --exclude '._*' --exclude '.DS_Store' \
    migrations/ zkyd@10.102.106.53:/home/zkyd/data1/mzy/PRAXIS-2/migrations/
rsync -avz --partial --exclude '._*' \
    deploy/ zkyd@10.102.106.53:/home/zkyd/data1/mzy/PRAXIS-2/deploy/
```

- [ ] **Step 3: 装 Python deps on .53**

```bash
ssh zkyd@10.102.106.53 \
    '/home/zkyd/software/miniconda3/envs/praxis2/bin/pip install \
       "python-multipart>=0.0.9" "python-magic>=0.4.27" "pyyaml>=6.0"'
```

- [ ] **Step 4: alembic upgrade**

```bash
ssh zkyd@10.102.106.53 \
    'cd /home/zkyd/data1/mzy/PRAXIS-2 && source /home/zkyd/praxis2.env && \
     /home/zkyd/software/miniconda3/envs/praxis2/bin/alembic upgrade head'
ssh zkyd@10.102.106.53 \
    'docker exec praxis2-pg psql -U praxis2 -d praxis2 -c "\dt files" | head -5'
```

Expected: `Running upgrade 002 -> 003_files` + `files` 表存在。

- [ ] **Step 5: backend restart**

```bash
ssh zkyd@10.102.106.53 'tmux send-keys -t 10:praxis2-be C-c'
sleep 2
ssh zkyd@10.102.106.53 'tmux send-keys -t 10:praxis2-be \
    "cd /home/zkyd/data1/mzy/PRAXIS-2 && source /home/zkyd/praxis2.env && \
     /home/zkyd/software/miniconda3/envs/praxis2/bin/gunicorn \
     -c deploy/gunicorn.conf.py praxis2.server.app:make_app_default" Enter'
sleep 8
curl -m 5 -s http://10.102.106.53:8001/api/info | python3 -m json.tool
```

Expected: `version: "v0.10.0"`(M10 暂不 bump backend version 字符串 — T13 末尾改 v0.11.0)

实际改 backend `/api/info` 返 v0.11.0 在这步:

```bash
# 本地改 praxis2/auth/routes.py:handle_info 把 "v0.10.0" → "v0.11.0",
# rsync 单文件 + 重启,或者直接 sed:
ssh zkyd@10.102.106.53 \
    "sed -i 's/\"v0.10.0\"/\"v0.11.0\"/' /home/zkyd/data1/mzy/PRAXIS-2/praxis2/auth/routes.py"
# 再 restart(同上 send-keys)
```

更干净的做法:T1 commit 同时改 handle_info 版本 v0.10.0 → v0.11.0;rsync 时已带新。**plan 实施者建议:T1 同步改 backend version,不用在 T13 sed**。

- [ ] **Step 6: backend smoke**

```bash
EMAIL="m10test$(date +%s)@x.com"
curl -s -c /tmp/m10cj -X POST http://10.102.106.53:8001/api/auth/email/send-code \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$EMAIL\",\"purpose\":\"register\"}" | tee /tmp/sc.json
CODE=$(python3 -c "import json;print(json.load(open('/tmp/sc.json'))['dev_code'])")
curl -s -c /tmp/m10cj -X POST http://10.102.106.53:8001/api/auth/register \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$EMAIL\",\"code\":\"$CODE\",\"password\":\"pw\"}"

# agents/profile
echo "--- /api/agents/profile ---"
curl -m 5 -s -b /tmp/m10cj http://10.102.106.53:8001/api/agents/profile \
    | python3 -c "import json,sys;d=json.load(sys.stdin); print('profiles:',len(d['profiles']),'first:',d['profiles'][0]['slug'])"

# usage (字段 count 不是 files_count!)
echo "--- /api/files/usage ---"
curl -m 5 -s -b /tmp/m10cj http://10.102.106.53:8001/api/files/usage \
    | python3 -m json.tool
# 期望:{used_bytes:0, quota_bytes:107374182400, count:0, max_per_file_bytes:21474836480}

# upload (小文件 1 KB)
echo "--- upload 1 KB pdb ---"
echo "ATOM 1 N MET A 1" > /tmp/tiny.pdb
RESP=$(curl -m 30 -s -b /tmp/m10cj -X POST \
    "http://10.102.106.53:8001/api/files?purpose=pdb" \
    -F file=@/tmp/tiny.pdb)
echo "$RESP" | python3 -m json.tool
FID=$(echo "$RESP" | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])")

# list
echo "--- /api/files?purpose=pdb ---"
curl -m 5 -s -b /tmp/m10cj "http://10.102.106.53:8001/api/files?purpose=pdb" \
    | python3 -m json.tool

# download
echo "--- /api/files/<id>/content ---"
curl -m 10 -s -b /tmp/m10cj \
    "http://10.102.106.53:8001/api/files/$FID/content" -o /tmp/dl.pdb
diff /tmp/tiny.pdb /tmp/dl.pdb && echo OK

# delete
echo "--- DELETE /api/files/<id> ---"
curl -m 5 -s -b /tmp/m10cj -X DELETE \
    "http://10.102.106.53:8001/api/files/$FID" | python3 -m json.tool

# cleanup test user
curl -s -b /tmp/m10cj -X DELETE http://10.102.106.53:8001/api/me/account
rm /tmp/m10cj /tmp/tiny.pdb /tmp/dl.pdb /tmp/sc.json
```

**Critical assertions**:
- agents/profile 返 13 学科,first slug 合理
- usage 字段名 `count`(不是 `files_count`)
- upload 返 `{id, filename, size_bytes, mime, purpose, created_at}`
- download 真返跟上传一样的内容(diff OK)
- delete 返 `{ok:true}`

- [ ] **Step 7: 浏览器手测**

打开 `http://10.102.106.40:8080/`,登录已有账号,点开:
- [ ] 智能体手册(13 学科)→ 卡片显示 case_count / rule_count / skill_workflows
- [ ] 文件管理 → 上传一个 .pdb 文件 → 列表显示 → 下载验证 → 删除
- [ ] usage 数字正确(刚上传后 used_bytes > 0)

**同时验** `.40:8088` v1 仍然正常工作(回归 check)。

- [ ] **Step 8: tag v0.11.0**

```bash
cd /Volumes/T7/clade-learn/PRAXIS-2
git tag v0.11.0 -m "M10 ship: agents/profile + 文件管理"
git push origin main --tags
```

---

## Self-Review

### Spec 覆盖检查

| Spec section | 实现 task |
|---|---|
| §0 #1 存储 fs `.53:/home/zkyd/data1/praxis2-files/` | T1 env + T5 FsStore |
| §0 #2 单文件 20 GB | T1 env + T9 gated_chunks check |
| §0 #3 用户 100 GB | T1 env + T9 quota check |
| §0 #4 python-multipart | T1 deps + T7 wrapper |
| §0 #5 purpose 枚举 5 | T2 CHECK + T9 _PURPOSES |
| §0 #6 brain 缓存 process lifetime | T8 module-level _CACHE |
| §0 #7 Range download | T9 _parse_range + handle_files_download |
| §0 #8 filename sanitize | T3 |
| §0 #9 mime python-magic | T4 |
| §0 #10 sample_cases 5 + metadata.yaml | T8 _top_5_cases + _load_metadata_yaml |
| §0 #11 413 + error code | T9 _UploadLimit + handler |
| §2 schema files + 2 index | T2 |
| §3.1 8 个新文件 | T1-T10 |
| §3.2 7 个改文件 | T1 + T11 |
| §4.1 agents/profile shape 12 字段 | T10 |
| §4.2 files list filter | T9 handle_files_list |
| §4.3 upload streaming + 413 | T9 handle_files_upload |
| §4.4 delete soft + 404 | T9 handle_files_delete |
| §4.5 usage 字段 `count` | T9 handle_files_usage |
| §4.6 download Range / 206 / 416 | T9 handle_files_download |
| §5.1 advisory lock | **未在 task 实现** — see gap |
| §5.2 安全表 6 风险 | T3 sanitize + T4 mime + T9 user_id 检 |
| §6 测试 ~36 | T3-T10 共 ~46(超额) |

### 已识别 gap

1. **§5.1 PG advisory lock(同用户并发 upload 防 quota 绕过)** — Plan 没在 T9 实现 `SELECT pg_advisory_xact_lock(hashtext('upload:'||user_id))`。
   - 影响:同用户并发 5 个 upload 都查 `usage` 拿到相同 used,各自认为没超 quota → 总和超额。
   - 严重度:M10 staging 单用户场景不暴露;真有需要 M10.5 加。**Plan 接受这个 gap,T9 注释里标 TODO**。
   - **修补**:T9 实现里加注释:
     ```python
     # spec §5.1 carry:同用户并发 upload 应取 pg_advisory_xact_lock
     # (hashtext('upload:'||user_id)) 防 quota 绕过。M10 单 worker
     # gunicorn = 2 workers,真有并发概率低,M10.5 carry。
     ```
   - 加到 T9 Step 3 实现注释里(不另起 task)。

2. **backend version v0.10.0 → v0.11.0** — Plan 仅在 T13 提及。**建议**:T1 顺手改 `handle_info` 那个字符串。
   - 修补:T1 Step 3 实现加一条 edit on `praxis2/auth/routes.py:handle_info` 把 `"v0.10.0"` → `"v0.11.0"`。

### 已识别风险(明确写在 task 内)

- **T7 multipart_stream**:python-multipart API 在不同版本差异大,实现细节标 ⚠️ 给实施者看版本 README 调整。
- **T9 _UploadLimit 在 fs_store.write_stream 内抛**:store_fs.write_stream 已 try/except BaseException 清 .part,_UploadLimit 子类于 Exception → 会被捕获 + .part 清干净 + re-raise。✅ 逻辑通。
- **T11 app.py 动态路径**:`/api/files/{id}` UUID 字符串可能含 `/`?UUID 不含 `/`,split 安全。

### 不在 plan 内的 carry

- M11.5 后台 GC 删 soft-deleted fs 实物
- v3 接 store_s3.py 真 COS
- 多 file multipart upload
- 断点续传
- virus scan
- per-plan quota 差异化(M12)

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-25-m10-agents-files.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — 每 task 一个 fresh subagent,两阶段 review,iteration 快(M9 时 9/13 task 一次过,这次预计 11/13)

**2. Inline Execution** — 本会话顺序执行,batch checkpoints

**Which approach?**
