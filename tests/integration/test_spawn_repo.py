"""SpawnRepo CRUD 集成测试 — 需要真实 PG (testcontainers)。"""

import pytest

from praxis2.spawn.repo import SpawnRepo

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]


async def test_create_then_get(pg_pool, fake_user_id):
    repo = SpawnRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        task_id = await repo.create(conn, fake_user_id, "hello", "deepseek-v4-pro")
    row = await repo.get(task_id)
    assert row["id"] == task_id
    assert row["user_id"] == fake_user_id
    assert row["status"] == "pending"
    assert row["prompt"] == "hello"
    assert row["model"] == "deepseek-v4-pro"
    assert row["answer"] == ""


async def test_count_active_pending_running(pg_pool, fake_user_id):
    repo = SpawnRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        await repo.create(conn, fake_user_id, "p1", "m")  # pending
        t2 = await repo.create(conn, fake_user_id, "p2", "m")
        await repo.update_running(t2)
        t3 = await repo.create(conn, fake_user_id, "p3", "m")
        await repo.update_failed(t3, "boom")  # not active
    assert await repo.count_active(fake_user_id) == 2


async def test_update_partial_appends(pg_pool, fake_user_id):
    repo = SpawnRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        tid = await repo.create(conn, fake_user_id, "p", "m")
    await repo.update_partial(tid, "hello ")
    await repo.update_partial(tid, "hello world")
    row = await repo.get(tid)
    assert row["answer"] == "hello world"


async def test_list_recent_desc_and_limit(pg_pool, fake_user_id):
    repo = SpawnRepo(pg_pool)
    ids = []
    for i in range(5):
        async with pg_pool.acquire() as conn:
            ids.append(await repo.create(conn, fake_user_id, f"p{i}", "m"))
    rows = await repo.list_recent(fake_user_id, limit=3)
    assert len(rows) == 3
    assert [r["id"] for r in rows] == list(reversed(ids))[:3]


async def test_trim_old_keeps_latest_n(pg_pool, fake_user_id):
    repo = SpawnRepo(pg_pool)
    ids = []
    for i in range(7):
        async with pg_pool.acquire() as conn:
            ids.append(await repo.create(conn, fake_user_id, f"p{i}", "m"))
    await repo.trim_old(fake_user_id, keep=3)
    rows = await repo.list_recent(fake_user_id, limit=100)
    assert len(rows) == 3
    assert {r["id"] for r in rows} == set(ids[-3:])
