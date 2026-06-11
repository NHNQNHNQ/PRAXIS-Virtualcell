"""admin v2 后端:user 管理 + audit 查询 + reconcile + stats。"""
from __future__ import annotations

import uuid
from typing import Any

import asyncpg

from praxis2.accounting.ledger import Ledger


def clamp_pagination(page: Any, limit: Any) -> tuple[int, int]:
    """统一处理 query string page/limit:
    page < 1 → 1; limit < 1 → 50; limit > 200 → 200。
    返 (page, limit) clamped。非整数转 int(失败用默认)。
    """
    try:
        p = int(page) if page is not None else 1
    except (ValueError, TypeError):
        p = 1
    try:
        lim = int(limit) if limit is not None else 50
    except (ValueError, TypeError):
        lim = 50
    return max(p, 1), max(min(lim, 200), 1)


class AdminUserRepo:
    def __init__(self, pool: asyncpg.Pool, ledger: Ledger) -> None:
        self._pool = pool
        self._ledger = ledger

    async def list_users(
        self, q: str, page: int, limit: int,
    ) -> dict[str, Any]:
        """模糊匹配 email + display_name (ILIKE %q%)。q='' 返全表。"""
        offset = (page - 1) * limit
        async with self._pool.acquire() as conn:
            if q:
                pattern = f"%{q}%"
                rows = await conn.fetch(
                    "SELECT id, email, phone, display_name, role, plan, status, "
                    "balance_li, created_at, last_login_at "
                    "FROM users "
                    "WHERE (email ILIKE $1 OR display_name ILIKE $1) "
                    "AND deleted_at IS NULL "
                    "ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                    pattern, limit, offset,
                )
                total = await conn.fetchval(
                    "SELECT count(*) FROM users WHERE "
                    "(email ILIKE $1 OR display_name ILIKE $1) "
                    "AND deleted_at IS NULL",
                    pattern,
                )
            else:
                rows = await conn.fetch(
                    "SELECT id, email, phone, display_name, role, plan, status, "
                    "balance_li, created_at, last_login_at "
                    "FROM users WHERE deleted_at IS NULL "
                    "ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                    limit, offset,
                )
                total = await conn.fetchval(
                    "SELECT count(*) FROM users WHERE deleted_at IS NULL"
                )
        return {
            "users": [self._user_row(r) for r in rows],
            "total": int(total),
            "page": page,
            "limit": limit,
        }

    async def adjust_balance(
        self, conn: asyncpg.Connection,
        target_user_id: str, admin_id: str,
        amount_li: int, note: str,
    ) -> dict[str, Any]:
        """admin 充值/扣款。caller 提供 conn(同 tx 跟 audit 一起)。

        amount_li 正 = 充值,负 = 扣款。
        返 {ledger_id, new_balance_li, new_balance_yuan};
        target 不存在或余额变负抛 LedgerError(handler 层分类转 400/404)。
        """
        if amount_li == 0:
            raise ValueError("zero_amount")
        new_balance = await self._ledger.record(
            conn, target_user_id, amount_li,
            kind="admin_adjust", ref_type="admin", ref_id=admin_id,
            meta={"note": note},
        )
        # Ledger.record 返 balance_after (不是 ledger.id);单独捞最新 ledger row id
        ledger_id = await conn.fetchval(
            "SELECT id FROM ledger WHERE user_id=$1 "
            "ORDER BY id DESC LIMIT 1",
            uuid.UUID(target_user_id),
        )
        return {
            "ledger_id": int(ledger_id),
            "new_balance_li": int(new_balance),
            "new_balance_yuan": f"{new_balance / 100:.2f}",
        }

    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        """读 user row (admin 端用,含 role/status/balance)。"""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, email, display_name, role, plan, status, "
                "balance_li, created_at, last_login_at "
                "FROM users WHERE id=$1 AND deleted_at IS NULL",
                uuid.UUID(user_id),
            )
        return self._user_row(row) if row else None

    async def freeze(
        self, conn: asyncpg.Connection,
        target_user_id: str, admin_id: str, reason: str,
    ) -> dict[str, Any]:
        """改 users.status='frozen'。target 是 admin 时拒 (handler 转 403)。"""
        cur = await conn.fetchrow(
            "SELECT role, status FROM users WHERE id=$1 AND deleted_at IS NULL "
            "FOR UPDATE",
            uuid.UUID(target_user_id),
        )
        if cur is None:
            raise UserNotFound(target_user_id)
        if cur["role"] == "admin":
            raise CannotFreezeAdmin(target_user_id)
        already = cur["status"] == "frozen"
        if not already:
            await conn.execute(
                "UPDATE users SET status='frozen' WHERE id=$1",
                uuid.UUID(target_user_id),
            )
        return {"ok": True, "status": "frozen", "already": already, "reason": reason}

    async def unfreeze(
        self, conn: asyncpg.Connection,
        target_user_id: str, admin_id: str,
    ) -> dict[str, Any]:
        cur = await conn.fetchrow(
            "SELECT status FROM users WHERE id=$1 AND deleted_at IS NULL FOR UPDATE",
            uuid.UUID(target_user_id),
        )
        if cur is None:
            raise UserNotFound(target_user_id)
        already = cur["status"] != "frozen"
        if not already:
            await conn.execute(
                "UPDATE users SET status='active' WHERE id=$1",
                uuid.UUID(target_user_id),
            )
        return {"ok": True, "status": "active", "already": already}

    async def reconcile(self, max_users: int) -> dict[str, Any]:
        """诊断:扫 max_users 个 user,对比 users.balance_li vs SUM(ledger).

        不锁、不修(诊断 only)。返 {checked, mismatches: int, details: list[≤20]}。
        """
        async with self._pool.acquire() as conn:
            users = await conn.fetch(
                "SELECT id, balance_li FROM users WHERE deleted_at IS NULL "
                "ORDER BY created_at DESC LIMIT $1",
                max_users,
            )
            mismatches: list[dict[str, Any]] = []
            for u in users:
                ledger_sum = await conn.fetchval(
                    "SELECT COALESCE(SUM(amount_li), 0) FROM ledger WHERE user_id=$1",
                    u["id"],
                )
                if int(u["balance_li"]) != int(ledger_sum):
                    mismatches.append({
                        "user_id": str(u["id"]),
                        "balance_li": int(u["balance_li"]),
                        "ledger_sum": int(ledger_sum),
                        "diff": int(u["balance_li"]) - int(ledger_sum),
                    })
        return {
            "checked": len(users),
            "mismatches": len(mismatches),
            "details": mismatches[:20],
        }

    async def get_stats(self) -> dict[str, Any]:
        """admin dashboard:user 数 / outstanding 余额 / runs / consumption。"""
        async with self._pool.acquire() as conn:
            user_stats = await conn.fetchrow(
                "SELECT count(*) FILTER (WHERE deleted_at IS NULL) AS total, "
                "count(*) FILTER (WHERE status='active' AND deleted_at IS NULL) AS active, "
                "count(*) FILTER (WHERE status='frozen' AND deleted_at IS NULL) AS frozen, "
                "count(*) FILTER (WHERE deleted_at IS NOT NULL) AS deleted "
                "FROM users",
            )
            outstanding = await conn.fetchval(
                "SELECT COALESCE(SUM(balance_li), 0) FROM users WHERE deleted_at IS NULL"
            )
            # runs (md_jobs + spawn_tasks 都算)
            md_stats = await conn.fetchrow(
                "SELECT count(*) AS total, "
                "count(*) FILTER (WHERE status='done') AS done, "
                "count(*) FILTER (WHERE status='failed') AS failed "
                "FROM md_jobs",
            )
            consumption = await conn.fetchval(
                "SELECT COALESCE(SUM(-amount_li), 0) FROM ledger "
                "WHERE amount_li < 0",
            )
        return {
            "users": {
                "total": int(user_stats["total"]),
                "active": int(user_stats["active"]),
                "frozen": int(user_stats["frozen"]),
                "deleted": int(user_stats["deleted"]),
            },
            "balance": {
                "outstanding_li": int(outstanding),
                "outstanding_yuan": f"{outstanding / 100:.2f}",
            },
            "runs": {
                "total": int(md_stats["total"]),
                "done": int(md_stats["done"]),
                "failed": int(md_stats["failed"]),
            },
            "consumption": {
                "total_li": int(consumption),
                "total_yuan": f"{consumption / 100:.2f}",
            },
        }

    @staticmethod
    def _user_row(r: asyncpg.Record) -> dict[str, Any]:
        d = dict(r)
        d["id"] = str(d["id"])
        d["balance_yuan"] = f"{d['balance_li'] / 100:.2f}"
        for k in ("created_at", "last_login_at"):
            if d.get(k):
                d[k] = d[k].isoformat()
        return d


class UserNotFound(Exception):
    def __init__(self, uid: str) -> None:
        super().__init__(f"user not found: {uid}")
        self.uid = uid


class CannotFreezeAdmin(Exception):
    def __init__(self, uid: str) -> None:
        super().__init__(f"cannot freeze admin user: {uid}")
        self.uid = uid


class AuditRepo:
    """audit_log 查询 + 包 M9 insert_audit。"""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def query(
        self, filters: dict[str, Any], page: int, limit: int,
    ) -> dict[str, Any]:
        offset = (page - 1) * limit
        where: list[str] = []
        args: list[Any] = []
        if filters.get("user_id"):
            args.append(uuid.UUID(filters["user_id"]))
            where.append(f"user_id = ${len(args)}")
        if filters.get("action"):
            args.append(filters["action"])
            where.append(f"action = ${len(args)}")
        where_sql = " WHERE " + " AND ".join(where) if where else ""
        args.extend([limit, offset])
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT id, user_id, actor, action, resource, resource_id, "
                f"ip, ua, meta, created_at "
                f"FROM audit_log{where_sql} "
                f"ORDER BY created_at DESC LIMIT ${len(args)-1} OFFSET ${len(args)}",
                *args,
            )
            total = await conn.fetchval(
                f"SELECT count(*) FROM audit_log{where_sql}",
                *args[:-2],
            )
        return {
            "rows": [self._audit_row(r) for r in rows],
            "total": int(total),
            "page": page,
            "limit": limit,
        }

    async def insert(
        self, conn: asyncpg.Connection,
        user_id: str | None, actor: str, action: str,
        resource: str | None, resource_id: str | None,
        ip: str | None, ua: str | None, meta: dict | None,
    ) -> int:
        """直接复用 M9 audit_log SQL 风格。"""
        import json as _json
        uid_val = uuid.UUID(user_id) if user_id else None
        row = await conn.fetchrow(
            "INSERT INTO audit_log "
            "(user_id, actor, action, resource, resource_id, ip, ua, meta) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb) "
            "RETURNING id",
            uid_val, actor, action, resource, resource_id,
            ip, ua, _json.dumps(meta) if meta else None,
        )
        return int(row["id"])

    @staticmethod
    def _audit_row(r: asyncpg.Record) -> dict[str, Any]:
        import json as _json
        d = dict(r)
        if d.get("user_id"):
            d["user_id"] = str(d["user_id"])
        if d.get("ip") is not None:
            # asyncpg 把 INET 反序列化成 ipaddress.IPv4Address/IPv6Address,
            # json.dumps 不识别 → str() 转回 "1.2.3.4" 字符串。
            d["ip"] = str(d["ip"])
        if d.get("meta"):
            d["meta"] = _json.loads(d["meta"]) if isinstance(d["meta"], str) else d["meta"]
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        return d
