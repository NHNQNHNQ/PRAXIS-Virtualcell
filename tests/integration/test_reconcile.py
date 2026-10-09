"""reconcile 制造 mismatch 验证检出。"""
from __future__ import annotations

import uuid

import pytest

from praxis2.accounting.ledger import Ledger
from praxis2.admin.repo import AdminUserRepo

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def _seed_balance_to_ledger(conn, user_id: str) -> None:
    """fixture 直接 INSERT balance_li=100000 没写 ledger → 默认就 drift。
    每个 test 先补一条 seed ledger 行让 fake_user_id 对齐。"""
    uid = uuid.UUID(user_id)
    bal = await conn.fetchval(
        "SELECT balance_li FROM users WHERE id=$1", uid,
    )
    # 该 user 已存在的 ledger sum
    existing = await conn.fetchval(
        "SELECT COALESCE(SUM(amount_li), 0) FROM ledger WHERE user_id=$1", uid,
    )
    delta = int(bal) - int(existing)
    if delta != 0:
        await conn.execute(
            "INSERT INTO ledger "
            "(user_id, amount_li, kind, ref_type, ref_id, balance_after, meta) "
            "VALUES ($1, $2, 'fixture_seed', NULL, NULL, $3, '{}'::jsonb)",
            uid, delta, int(bal),
        )


async def test_reconcile_clean_returns_zero_mismatches(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        await _seed_balance_to_ledger(conn, fake_user_id)
        # 然后通过 Ledger.record 加余额(保持一致)
        async with conn.transaction():
            await Ledger(pg_pool).record(
                conn, fake_user_id, 1000, kind="seed",
                ref_type=None, ref_id=None, meta={},
            )
    result = await repo.reconcile(max_users=100)
    # 该 user 应该不在 mismatch 列表
    assert not any(d["user_id"] == fake_user_id for d in result["details"])


async def test_reconcile_detects_balance_drift(pg_pool, fake_user_id):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    async with pg_pool.acquire() as conn:
        await _seed_balance_to_ledger(conn, fake_user_id)
        # 故意 UPDATE balance 跳过 ledger → 制造 +7777 drift
        await conn.execute(
            "UPDATE users SET balance_li = balance_li + 7777 WHERE id=$1",
            uuid.UUID(fake_user_id),
        )
    result = await repo.reconcile(max_users=100)
    assert result["mismatches"] >= 1
    diffs = [d["diff"] for d in result["details"] if d["user_id"] == fake_user_id]
    assert diffs and abs(diffs[0]) == 7777


async def test_reconcile_max_users_cap(pg_pool):
    repo = AdminUserRepo(pg_pool, Ledger(pg_pool))
    result = await repo.reconcile(max_users=5)
    assert result["checked"] <= 5
