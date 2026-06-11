"""AuditRepo query + insert (复用 audit_log M9 表)."""
from __future__ import annotations

import pytest

from praxis2.admin.repo import AuditRepo

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def test_insert_and_query_returns_row(pg_pool, fake_user_id):
    repo = AuditRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            audit_id = await repo.insert(
                conn, user_id=fake_user_id, actor="admin",
                action="test_action", resource="user",
                resource_id=fake_user_id,
                ip="127.0.0.1", ua="test-ua",
                meta={"foo": "bar"},
            )
    assert audit_id > 0
    result = await repo.query({"user_id": fake_user_id, "action": "test_action"},
                              page=1, limit=10)
    matched = [r for r in result["rows"] if r["id"] == audit_id]
    assert matched and matched[0]["meta"] == {"foo": "bar"}


async def test_query_filter_by_action(pg_pool, fake_user_id):
    repo = AuditRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            await repo.insert(
                conn, fake_user_id, "admin", "balance_adjust",
                "user", fake_user_id, None, None, {"amount": 100},
            )
    result = await repo.query({"action": "balance_adjust"}, page=1, limit=10)
    assert all(r["action"] == "balance_adjust" for r in result["rows"])


async def test_query_pagination(pg_pool, fake_user_id):
    repo = AuditRepo(pg_pool)
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            for _ in range(3):
                await repo.insert(
                    conn, fake_user_id, "admin", "paging_test",
                    "user", fake_user_id, None, None, None,
                )
    p1 = await repo.query({"action": "paging_test"}, page=1, limit=2)
    p2 = await repo.query({"action": "paging_test"}, page=2, limit=2)
    assert len(p1["rows"]) == 2
    assert len(p2["rows"]) >= 1
