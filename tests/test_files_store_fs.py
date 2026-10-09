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
