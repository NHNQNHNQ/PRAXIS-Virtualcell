"""Ledger.record() 单元 + integration 测试。

整笔事务要外层(handler / register)管;Ledger 方法自身只保证 SELECT FOR UPDATE
+ INSERT ledger + UPDATE users 在传入 conn 上原子执行。
"""

from __future__ import annotations

import os
import uuid

import pytest

pytestmark = pytest.mark.integration  # 需 PRAXIS_INTEGRATION=1 + docker PG


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
    """造一个测试 user,返 id;测试结束删干净。"""
    uid = uuid.uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id, email, password_hash, balance_li) "
            "VALUES ($1, $2, $3, 0)",
            uid, f"t_{uid}@x", b"x",
        )
    yield str(uid)
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM ledger WHERE user_id=$1", uid)
        await conn.execute("DELETE FROM users WHERE id=$1", uid)


async def test_record_signup_gift_inserts_row_and_updates_balance(pool, user_id):
    from praxis2.accounting.ledger import Ledger

    L = Ledger(pool)
    async with pool.acquire() as conn:
        async with conn.transaction():
            new_bal = await L.record(
                conn, user_id, 10000, "signup_gift", None, None, {}
            )
    assert new_bal == 10000
    async with pool.acquire() as conn:
        bal = await conn.fetchval(
            "SELECT balance_li FROM users WHERE id=$1", uuid.UUID(user_id)
        )
        rows = await conn.fetch(
            "SELECT amount_li, kind, balance_after FROM ledger WHERE user_id=$1",
            uuid.UUID(user_id),
        )
    assert bal == 10000
    assert len(rows) == 1
    assert rows[0]["amount_li"] == 10000
    assert rows[0]["kind"] == "signup_gift"
    assert rows[0]["balance_after"] == 10000


async def test_record_consumption_negative_amount(pool, user_id):
    from praxis2.accounting.ledger import Ledger

    L = Ledger(pool)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await L.record(conn, user_id, 10000, "signup_gift", None, None, {})
        async with conn.transaction():
            new_bal = await L.record(
                conn,
                user_id,
                -200,
                "chat_out",
                "chat_session",
                "sess-x",
                {"req": 1},
            )
    assert new_bal == 9800


async def test_record_zero_amount_allowed(pool, user_id):
    from praxis2.accounting.ledger import Ledger
    L = Ledger(pool)
    async with pool.acquire() as conn:
        async with conn.transaction():
            new_bal = await L.record(conn, user_id, 0, "admin_adjust", None, None, {"note": "noop"})
    assert new_bal == 0


async def test_record_insufficient_balance_raises(pool, user_id):
    from praxis2.accounting.ledger import Ledger, LedgerError
    L = Ledger(pool)
    with pytest.raises(LedgerError, match="insufficient_balance"):
        async with pool.acquire() as conn:
            async with conn.transaction():
                await L.record(conn, user_id, -100, "chat_out", None, None, {})


async def test_record_unknown_user_raises(pool):
    from praxis2.accounting.ledger import Ledger, LedgerError
    L = Ledger(pool)
    fake_uid = str(uuid.uuid4())
    with pytest.raises(LedgerError, match="user_not_found"):
        async with pool.acquire() as conn:
            async with conn.transaction():
                await L.record(conn, fake_uid, 100, "topup", None, None, {})


async def test_recent_returns_desc_by_created_at(pool, user_id):
    from praxis2.accounting.ledger import Ledger
    L = Ledger(pool)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await L.record(conn, user_id, 10000, "signup_gift", None, None, {})
        async with conn.transaction():
            await L.record(conn, user_id, -200, "chat_out", None, None, {})
        async with conn.transaction():
            await L.record(conn, user_id, -100, "chat_out", None, None, {})
    rows = await L.recent(user_id, limit=20)
    assert len(rows) == 3
    assert [r["amount_li"] for r in rows] == [-100, -200, 10000]  # DESC


async def test_recent_limit_default_20(pool, user_id):
    from praxis2.accounting.ledger import Ledger
    L = Ledger(pool)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await L.record(conn, user_id, 100000, "signup_gift", None, None, {})
        for _ in range(25):
            async with conn.transaction():
                await L.record(conn, user_id, -10, "chat_out", None, None, {})
    rows = await L.recent(user_id)  # default 20
    assert len(rows) == 20


async def test_recent_empty_for_new_user(pool, user_id):
    from praxis2.accounting.ledger import Ledger
    L = Ledger(pool)
    rows = await L.recent(user_id)
    assert rows == []


async def test_record_meta_json_roundtrip(pool, user_id):
    from praxis2.accounting.ledger import Ledger
    L = Ledger(pool)
    payload = {"req_id": "abc", "tokens": {"in": 12, "out": 34}}
    async with pool.acquire() as conn:
        async with conn.transaction():
            await L.record(conn, user_id, 10000, "signup_gift", None, None, {})
        async with conn.transaction():
            await L.record(conn, user_id, -100, "chat_out", "chat_session", "sess-x", payload)
    rows = await L.recent(user_id)
    assert rows[0]["meta"] == payload


async def test_concurrent_records_no_lost_update(pool, user_id):
    """5 个并发 +100 入账,最终余额必须 = 500(SELECT FOR UPDATE 防 lost update)。"""
    import asyncio

    from praxis2.accounting.ledger import Ledger

    L = Ledger(pool)

    async def credit():
        async with pool.acquire() as conn:
            async with conn.transaction():
                await L.record(conn, user_id, 100, "topup", None, None, {})

    await asyncio.gather(*[credit() for _ in range(5)])
    async with pool.acquire() as conn:
        bal = await conn.fetchval("SELECT balance_li FROM users WHERE id=$1", uuid.UUID(user_id))
    assert bal == 500
