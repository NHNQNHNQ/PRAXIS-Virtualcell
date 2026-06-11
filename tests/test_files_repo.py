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
    assert usage["used_bytes"] == 200
    assert usage["count"] == 1


async def test_usage_zero_for_new_user(pool, user_id):
    from praxis2.files.repo import FilesRepo
    r = FilesRepo(pool)
    usage = await r.usage(user_id=user_id)
    assert usage == {"used_bytes": 0, "count": 0}


async def test_create_file_with_invalid_purpose_raises(pool, user_id):
    import asyncpg

    from praxis2.files.repo import FilesRepo
    r = FilesRepo(pool)
    with pytest.raises((asyncpg.CheckViolationError, asyncpg.PostgresError)):
        await r.create_file(user_id=user_id, filename="x", size_bytes=10,
                            mime=None, purpose="invalid_purpose",
                            storage_key="fs:x/y")
