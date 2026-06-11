"""auth repository:Protocol + FakeAuthRepository(单元用)。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from praxis2.auth.errors import EmailConflict


@dataclass(frozen=True)
class UserRow:
    id: str
    email: str
    password_hash: bytes
    display_name: str | None
    role: str
    plan: str = "free"
    status: str = "active"
    balance_li: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_login_at: datetime | None = None
    last_login_ip: str | None = None
    realname_verified_at: datetime | None = None
    deleted_at: datetime | None = None


@dataclass(frozen=True)
class EmailCodeRow:
    id: int
    email: str
    code: str
    purpose: str
    attempts: int
    used: bool
    expires_at: datetime
    created_at: datetime


@dataclass(frozen=True)
class AuditRow:
    id: int
    user_id: str | None
    actor: str
    action: str
    resource: str | None
    resource_id: str | None
    ip: str | None
    ua: str | None
    meta: dict | None
    created_at: datetime


@runtime_checkable
class AuthRepository(Protocol):
    async def create_user(
        self, *, email: str, password_hash: bytes, display_name: str | None, role: str
    ) -> UserRow: ...
    async def get_user_by_email(self, email: str) -> UserRow | None: ...
    async def get_user_by_id(self, user_id: str) -> UserRow | None: ...
    async def soft_delete_user(self, user_id: str) -> None: ...
    async def update_last_login(self, user_id: str, *, ip: str | None, at: datetime) -> None: ...
    async def insert_email_code(
        self, *, email: str, code: str, purpose: str, expires_at: datetime
    ) -> int: ...
    async def get_latest_email_code(self, email: str, purpose: str) -> EmailCodeRow | None: ...
    async def mark_email_code_used(self, code_id: int) -> None: ...
    async def incr_email_code_attempts(self, code_id: int) -> int: ...
    async def insert_audit(
        self,
        *,
        user_id: str | None,
        actor: str,
        action: str,
        resource: str | None = None,
        resource_id: str | None = None,
        ip: str | None = None,
        ua: str | None = None,
        meta: dict | None = None,
    ) -> None: ...
    async def list_audit_by_user(self, user_id: str, limit: int = 100) -> list[AuditRow]: ...
    async def get_user_profile(self, user_id: str) -> dict | None: ...
    async def upsert_user_profile(self, user_id: str, **fields: str | None) -> None: ...
    async def get_user_with_balance(self, user_id: str) -> dict | None: ...
    async def get_balance_li(self, user_id: str) -> int: ...


class FakeAuthRepository:
    """单元层内存实现(单进程,非线程安全;仅 pytest 用)。"""

    def __init__(self) -> None:
        self._users: dict[str, UserRow] = {}
        self._email_codes: list[EmailCodeRow] = []
        self._audit: list[AuditRow] = []
        self._profiles: dict[str, dict] = {}
        self._code_id = 0
        self._audit_id = 0

    async def create_user(self, *, email, password_hash, display_name, role):
        for u in self._users.values():
            if u.email == email and u.deleted_at is None:
                raise EmailConflict(f"邮箱 {email} 已注册")
        uid = str(uuid.uuid4())
        row = UserRow(
            id=uid,
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            role=role,
        )
        self._users[uid] = row
        return row

    async def get_user_by_email(self, email):
        for u in self._users.values():
            if u.email == email and u.deleted_at is None:
                return u
        return None

    async def get_user_by_id(self, user_id):
        u = self._users.get(user_id)
        return u if u and u.deleted_at is None else None

    async def soft_delete_user(self, user_id):
        u = self._users.get(user_id)
        if u:
            self._users[user_id] = replace(u, deleted_at=datetime.now(UTC))

    async def update_last_login(self, user_id, *, ip, at):
        u = self._users.get(user_id)
        if u:
            self._users[user_id] = replace(u, last_login_at=at, last_login_ip=ip)

    async def insert_email_code(self, *, email, code, purpose, expires_at):
        self._code_id += 1
        row = EmailCodeRow(
            id=self._code_id,
            email=email,
            code=code,
            purpose=purpose,
            attempts=0,
            used=False,
            expires_at=expires_at,
            created_at=datetime.now(UTC),
        )
        self._email_codes.append(row)
        return row.id

    async def get_latest_email_code(self, email, purpose):
        c = [
            r
            for r in self._email_codes
            if r.email == email
            and r.purpose == purpose
            and not r.used
            and r.expires_at > datetime.now(UTC)
        ]
        return max(c, key=lambda r: r.created_at) if c else None

    async def mark_email_code_used(self, code_id):
        for i, r in enumerate(self._email_codes):
            if r.id == code_id:
                self._email_codes[i] = replace(r, used=True)
                return

    async def incr_email_code_attempts(self, code_id):
        for i, r in enumerate(self._email_codes):
            if r.id == code_id:
                new_n = r.attempts + 1
                self._email_codes[i] = replace(r, attempts=new_n)
                return new_n
        return 0

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
        self._audit_id += 1
        self._audit.append(
            AuditRow(
                id=self._audit_id,
                user_id=user_id,
                actor=actor,
                action=action,
                resource=resource,
                resource_id=resource_id,
                ip=ip,
                ua=ua,
                meta=meta,
                created_at=datetime.now(UTC),
            )
        )

    async def list_audit_by_user(self, user_id, limit=100):
        return [r for r in self._audit if r.user_id == user_id][-limit:]

    PROFILE_FIELDS = (
        "research_field", "affiliation", "expertise_level",
        "projects", "custom_intro",
    )

    async def get_user_profile(self, user_id):
        return self._profiles.get(user_id)

    async def upsert_user_profile(self, user_id, **fields):
        if not fields:
            return
        unknown = set(fields) - set(self.PROFILE_FIELDS)
        if unknown:
            raise ValueError(f"unknown profile field: {unknown}")
        cur = self._profiles.get(user_id) or {
            "research_field": None, "affiliation": None,
            "expertise_level": None, "projects": None, "custom_intro": None,
            "updated_at": None,
        }
        for k, v in fields.items():
            cur[k] = v
        cur["updated_at"] = datetime.now(UTC)
        self._profiles[user_id] = cur

    async def get_user_with_balance(self, user_id):
        u = self._users.get(user_id)
        if u is None:
            return None
        return {
            "id": u.id, "email": u.email, "phone": None,
            "display_name": u.display_name, "role": u.role,
            "plan": u.plan, "status": u.status, "balance_li": u.balance_li,
            "realname_verified": bool(u.realname_verified_at),
            "created_at": u.created_at,
        }

    async def get_balance_li(self, user_id):
        u = self._users.get(user_id)
        return u.balance_li if u else 0
