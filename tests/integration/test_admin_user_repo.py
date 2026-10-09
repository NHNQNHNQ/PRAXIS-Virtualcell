"""AdminUserRepo 真 PG fixture 验证。"""
from __future__ import annotations

import pytest

from praxis2.accounting.ledger import Ledger, LedgerError
from praxis2.admin.repo import AdminUserRepo, UserNotFound

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def test_list_users_returns_paginated(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    result = await repo.list_users(q="", page=1, limit=50)
    assert "users" in result
    assert result["total"] >= 1  # fake_user_id 至少 1
    assert result["page"] == 1
    assert result["limit"] == 50
    # 字段完整性 (跟 FE admin.ts AdminUserRow 对齐)
    if result["users"]:
        u = result["users"][0]
        assert "id" in u
        assert "email" in u
        assert "phone" in u  # M9 users 表有 phone
        assert "balance_li" in u
        assert "balance_yuan" in u


async def test_list_users_q_filters_by_email_ilike(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    # fake_user_id fixture 应有 email 含 "test"
    result = await repo.list_users(q="test", page=1, limit=50)
    # 避免 vacuous all([]): 至少匹到 1 个 fake_user_id
    assert len(result["users"]) >= 1
    assert all("test" in u["email"].lower() or "test" in (u["display_name"] or "").lower()
               for u in result["users"])


async def test_list_users_pagination_offset(pg_pool):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    page1 = await repo.list_users(q="", page=1, limit=2)
    page2 = await repo.list_users(q="", page=2, limit=2)
    if page1["total"] >= 4:
        # 不同页 id 不同
        assert set(u["id"] for u in page1["users"]) != set(
            u["id"] for u in page2["users"]
        )


async def test_adjust_balance_topup_increases_balance(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        before = await conn.fetchval(
            "SELECT balance_li FROM users WHERE id=$1::uuid", fake_user_id,
        )
        async with conn.transaction():
            result = await repo.adjust_balance(
                conn, fake_user_id, fake_user_id, 5000, "test topup",
            )
    expected_new = int(before) + 5000
    assert result["new_balance_li"] == expected_new
    # ledger_id 是真 ledger 表 BIGSERIAL pk, 不等于 balance
    assert result["ledger_id"] > 0
    assert result["ledger_id"] != result["new_balance_li"]
    # yuan 格式 (1 元 = 100 li)
    assert result["new_balance_yuan"] == f"{expected_new / 100:.2f}"


async def test_adjust_balance_zero_amount_raises(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            with pytest.raises(ValueError, match="zero_amount"):
                await repo.adjust_balance(
                    conn, fake_user_id, fake_user_id, 0, "noop",
                )


async def test_adjust_balance_negative_overflow_raises(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        # 先给 1000,然后扣 999999 → 必负
        async with conn.transaction():
            await repo.adjust_balance(
                conn, fake_user_id, fake_user_id, 1000, "seed",
            )
        async with conn.transaction():
            with pytest.raises(LedgerError, match="insufficient"):
                await repo.adjust_balance(
                    conn, fake_user_id, fake_user_id, -999999, "overdraw",
                )


async def test_adjust_balance_to_exactly_zero(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        cur = await conn.fetchval(
            "SELECT balance_li FROM users WHERE id=$1::uuid", fake_user_id,
        )
        # 扣到正好 0(Ledger.record `if new_balance < 0` 严格小于, =0 允许)
        async with conn.transaction():
            result = await repo.adjust_balance(
                conn, fake_user_id, fake_user_id, -int(cur), "zero out",
            )
    assert result["new_balance_li"] == 0
    assert result["new_balance_yuan"] == "0.00"


async def test_adjust_balance_meta_persisted(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            result = await repo.adjust_balance(
                conn, fake_user_id, fake_user_id, 100, "meta-roundtrip",
            )
        row = await conn.fetchrow(
            "SELECT meta::jsonb AS m FROM ledger WHERE id=$1",
            result["ledger_id"],
        )
    import json as _json
    meta = _json.loads(row["m"]) if isinstance(row["m"], str) else row["m"]
    assert meta == {"note": "meta-roundtrip"}


async def test_freeze_changes_status(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            result = await repo.freeze(
                conn, fake_user_id, fake_user_id, "test reason",
            )
    assert result["status"] == "frozen"
    user = await repo.get_user(fake_user_id)
    assert user["status"] == "frozen"


async def test_freeze_idempotent_marks_already(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            await repo.freeze(conn, fake_user_id, fake_user_id, "first")
        async with conn.transaction():
            result = await repo.freeze(conn, fake_user_id, fake_user_id, "second")
    assert result["already"] is True


async def test_unfreeze_restores_status(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            await repo.freeze(conn, fake_user_id, fake_user_id, "test")
        async with conn.transaction():
            result = await repo.unfreeze(conn, fake_user_id, fake_user_id)
    assert result["status"] == "active"


async def test_freeze_user_not_found_raises(pg_pool):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            with pytest.raises(UserNotFound):
                await repo.freeze(
                    conn, "00000000-0000-0000-0000-000000000000",
                    "00000000-0000-0000-0000-000000000000", "x",
                )


async def test_get_stats_returns_all_buckets(pg_pool):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    stats = await repo.get_stats()
    assert "users" in stats and all(
        k in stats["users"] for k in ("total", "active", "frozen", "deleted")
    )
    assert "balance" in stats
    assert "runs" in stats
    assert "consumption" in stats
