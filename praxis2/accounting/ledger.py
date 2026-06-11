"""Ledger:append-only 流水 + 余额一致(SELECT FOR UPDATE 防 lost update)。

设计:`record(conn, ...)` 不自己开事务,要求调用方传入已 begin 的 conn;
便于跟 register / chat 等更大事务组合(原子 user 创建 + 赠送)。

`recent(user_id, limit)` 自己拿 conn(只读,不卡)。
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import asyncpg


class LedgerError(Exception):
    """ledger 业务错误:user_not_found / insufficient_balance。"""


class Ledger:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def record(
        self,
        conn: asyncpg.Connection,
        user_id: str,
        amount_li: int,
        kind: str,
        ref_type: str | None,
        ref_id: str | None,
        meta: dict | None,
    ) -> int:
        """append + 更新余额。返 balance_after。

        调用方必须已 `async with conn.transaction():` 包住此调用。
        """
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        cur = await conn.fetchval(
            "SELECT balance_li FROM users WHERE id=$1 FOR UPDATE", uid
        )
        if cur is None:
            raise LedgerError(f"user_not_found: {user_id}")
        new_balance = int(cur) + int(amount_li)
        if new_balance < 0:
            raise LedgerError(
                f"insufficient_balance: cur={cur} amount={amount_li}"
            )
        await conn.execute(
            "INSERT INTO ledger "
            "(user_id, amount_li, kind, ref_type, ref_id, balance_after, meta) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)",
            uid,
            int(amount_li),
            kind,
            ref_type,
            ref_id,
            new_balance,
            json.dumps(meta or {}),
        )
        await conn.execute(
            "UPDATE users SET balance_li=$1 WHERE id=$2", new_balance, uid
        )
        return new_balance

    async def consume_capped(
        self,
        conn: asyncpg.Connection,
        user_id: str,
        requested_li: int,
        ref_type: str | None,
        ref_id: str | None,
        meta: dict | None,
    ) -> int:
        """扣费,余额不足只扣到 0(先答后扣,不拒)。返实际扣的 li(>=0)。

        与 record() 不同:record 拒负余额(insufficient_balance),consume 把扣费
        cap 到当前余额——chat 是先答后扣,答案已出,不能因余额不足回滚。
        调用方必须已 `async with conn.transaction():` 包住。
        """
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        cur = await conn.fetchval(
            "SELECT balance_li FROM users WHERE id=$1 FOR UPDATE", uid
        )
        if cur is None:
            raise LedgerError(f"user_not_found: {user_id}")
        actual = min(int(requested_li), int(cur))  # cap 到余额,不负
        if actual <= 0:
            return 0  # 余额已 0 或无需扣 → 不记空流水
        new_balance = int(cur) - actual
        await conn.execute(
            "INSERT INTO ledger "
            "(user_id, amount_li, kind, ref_type, ref_id, balance_after, meta) "
            "VALUES ($1, $2, 'consume', $3, $4, $5, $6::jsonb)",
            uid, -actual, ref_type, ref_id, new_balance, json.dumps(meta or {}),
        )
        await conn.execute(
            "UPDATE users SET balance_li=$1 WHERE id=$2", new_balance, uid
        )
        return actual

    async def recent(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """读最近 N 条流水(DESC)。"""
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, amount_li, kind, ref_type, ref_id, balance_after, "
                "       meta, created_at "
                "FROM ledger WHERE user_id=$1 "
                "ORDER BY created_at DESC, id DESC LIMIT $2",
                uid,
                int(limit),
            )
        return [_row_to_dict(r) for r in rows]


def _row_to_dict(r) -> dict[str, Any]:
    return {
        "id": int(r["id"]),
        "amount_li": int(r["amount_li"]),
        "kind": r["kind"],
        "ref_type": r["ref_type"],
        "ref_id": r["ref_id"],
        "balance_after": int(r["balance_after"]),
        "meta": json.loads(r["meta"]) if r["meta"] else None,
        "created_at": r["created_at"],
    }
