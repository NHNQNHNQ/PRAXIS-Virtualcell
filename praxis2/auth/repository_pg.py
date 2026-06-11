"""PgAuthRepository:asyncpg 真实现(integration / staging 用)。

复用 store/pg.py make_pg_pool 共享 asyncpg pool。
"""

from __future__ import annotations

import json
import uuid

import asyncpg

from praxis2.auth.errors import EmailConflict
from praxis2.auth.repository import AuditRow, EmailCodeRow, UserRow


class PgAuthRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_user(self, *, email, password_hash, display_name, role):
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """INSERT INTO users (email, password_hash, display_name, role)
                       VALUES ($1, $2, $3, $4)
                       RETURNING id, email, password_hash, display_name, role, plan,
                                 status, balance_li, created_at, last_login_at,
                                 last_login_ip, realname_verified_at, deleted_at""",
                    email,
                    password_hash,
                    display_name,
                    role,
                )
        except asyncpg.UniqueViolationError as e:
            raise EmailConflict(f"邮箱 {email} 已注册") from e
        return _row_to_user(row)

    async def get_user_by_email(self, email):
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT id, email, password_hash, display_name, role, plan,
                          status, balance_li, created_at, last_login_at,
                          last_login_ip, realname_verified_at, deleted_at FROM users
                   WHERE email=$1 AND deleted_at IS NULL""",
                email,
            )
        return _row_to_user(row) if row else None

    async def get_user_by_id(self, user_id):
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT id, email, password_hash, display_name, role, plan,
                          status, balance_li, created_at, last_login_at,
                          last_login_ip, realname_verified_at, deleted_at FROM users
                   WHERE id=$1 AND deleted_at IS NULL""",
                user_id,
            )
        return _row_to_user(row) if row else None

    async def soft_delete_user(self, user_id):
        async with self._pool.acquire() as conn:
            await conn.execute("UPDATE users SET deleted_at=now() WHERE id=$1", user_id)

    async def update_user_role(self, user_id, *, role: str) -> None:
        """v2.0.2 — 升降级 role(user / admin)。M12 admin v2 完整管理面板前的运维口子。"""
        if role not in {"user", "admin"}:
            raise ValueError(f"role 必须是 user 或 admin,实际:{role!r}")
        async with self._pool.acquire() as conn:
            await conn.execute("UPDATE users SET role=$2 WHERE id=$1", user_id, role)

    async def update_last_login(self, user_id, *, ip, at):
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_login_at=$2, last_login_ip=$3 WHERE id=$1",
                user_id,
                at,
                ip,
            )

    async def insert_email_code(self, *, email, code, purpose, expires_at):
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO email_codes (email, code, purpose, expires_at)
                   VALUES ($1, $2, $3, $4) RETURNING id""",
                email,
                code,
                purpose,
                expires_at,
            )
        return int(row["id"])

    async def get_latest_email_code(self, email, purpose):
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT id, email, code, purpose, attempts, used, expires_at,
                          created_at FROM email_codes
                   WHERE email=$1 AND purpose=$2 AND used=false
                         AND expires_at > now()
                   ORDER BY created_at DESC LIMIT 1""",
                email,
                purpose,
            )
        return _row_to_email_code(row) if row else None

    async def mark_email_code_used(self, code_id):
        async with self._pool.acquire() as conn:
            await conn.execute("UPDATE email_codes SET used=true WHERE id=$1", code_id)

    async def incr_email_code_attempts(self, code_id):
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE email_codes SET attempts=attempts+1 WHERE id=$1 RETURNING attempts",
                code_id,
            )
        return int(row["attempts"]) if row else 0

    async def insert_audit(
        self,
        *,
        user_id,
        actor,
        action,
        resource=None,
        resource_id=None,
        ip=None,
        ua=None,
        meta=None,
    ):
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO audit_log
                   (user_id, actor, action, resource, resource_id, ip, ua, meta)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)""",
                user_id,
                actor,
                action,
                resource,
                resource_id,
                ip,
                ua,
                json.dumps(meta) if meta else None,
            )

    async def list_audit_by_user(self, user_id, limit=100):
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, user_id, actor, action, resource, resource_id, ip, ua,
                          meta, created_at FROM audit_log
                   WHERE user_id=$1 ORDER BY created_at DESC LIMIT $2""",
                user_id,
                limit,
            )
        return [_row_to_audit(r) for r in rows]

    # ── M9:profile + balance ─────────────────────────────────────────
    PROFILE_FIELDS = (
        "research_field", "affiliation", "expertise_level",
        "projects", "custom_intro",
    )

    async def get_user_profile(self, user_id: str) -> dict | None:
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT research_field, affiliation, expertise_level, "
                "       projects, custom_intro, updated_at "
                "FROM user_profiles WHERE user_id=$1",
                uid,
            )
        if row is None:
            return None
        return {
            "research_field": row["research_field"],
            "affiliation": row["affiliation"],
            "expertise_level": row["expertise_level"],
            "projects": row["projects"],
            "custom_intro": row["custom_intro"],
            "updated_at": row["updated_at"],
        }

    async def upsert_user_profile(self, user_id: str, **fields) -> None:
        """fields 只含调用方真要写的字段;值可为 None(SET NULL = 清空)。

        缺失字段不进 SET clause。空 fields 视为 no-op。
        """
        if not fields:
            return
        unknown = set(fields) - set(self.PROFILE_FIELDS)
        if unknown:
            raise ValueError(f"unknown profile field: {unknown}")
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        cols = list(fields.keys())
        col_list = ", ".join(cols)
        val_placeholders = ", ".join(f"${i+2}" for i in range(len(cols)))
        set_clause = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols)
        sql = (
            f"INSERT INTO user_profiles (user_id, {col_list}, updated_at) "
            f"VALUES ($1, {val_placeholders}, now()) "
            f"ON CONFLICT (user_id) DO UPDATE SET {set_clause}, updated_at=now()"
        )
        async with self._pool.acquire() as conn:
            await conn.execute(sql, uid, *[fields[c] for c in cols])

    async def get_user_with_balance(self, user_id: str) -> dict | None:
        """读 user 全字段 + balance_li(已在 users 表里)+ realname_verified bool。

        balance_li 在 ledger 写入时跟着 UPDATE users 同步,这里直接读。
        """
        u = await self.get_user_by_id(user_id)
        if u is None:
            return None
        return {
            "id": u.id,
            "email": u.email,
            "phone": None,  # M9 schema 无该列(001 有 phone 但 InMemoryAuth 无,统一 None)
            "display_name": u.display_name,
            "role": u.role,
            "plan": u.plan,
            "status": u.status,
            "balance_li": u.balance_li,
            "realname_verified": bool(u.realname_verified_at),
            "created_at": u.created_at,
        }

    async def get_balance_li(self, user_id: str) -> int:
        """便利方法:只取 balance_li,handle_me_balance 用。"""
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        async with self._pool.acquire() as conn:
            cur = await conn.fetchval(
                "SELECT balance_li FROM users WHERE id=$1 AND deleted_at IS NULL", uid
            )
        return int(cur) if cur is not None else 0


def _row_to_user(r) -> UserRow | None:
    if r is None:
        return None
    return UserRow(
        id=str(r["id"]),
        email=r["email"],
        password_hash=bytes(r["password_hash"]),
        display_name=r["display_name"],
        role=r["role"],
        plan=r["plan"],
        status=r["status"],
        balance_li=int(r["balance_li"]),
        created_at=r["created_at"],
        last_login_at=r["last_login_at"],
        last_login_ip=str(r["last_login_ip"]) if r["last_login_ip"] else None,
        realname_verified_at=r["realname_verified_at"],
        deleted_at=r["deleted_at"],
    )


def _row_to_email_code(r) -> EmailCodeRow:
    return EmailCodeRow(
        id=int(r["id"]),
        email=r["email"],
        code=r["code"],
        purpose=r["purpose"],
        attempts=int(r["attempts"]),
        used=bool(r["used"]),
        expires_at=r["expires_at"],
        created_at=r["created_at"],
    )


def _row_to_audit(r) -> AuditRow:
    return AuditRow(
        id=int(r["id"]),
        user_id=str(r["user_id"]) if r["user_id"] else None,
        actor=r["actor"],
        action=r["action"],
        resource=r["resource"],
        resource_id=r["resource_id"],
        ip=str(r["ip"]) if r["ip"] else None,
        ua=r["ua"],
        meta=json.loads(r["meta"]) if r["meta"] else None,
        created_at=r["created_at"],
    )
