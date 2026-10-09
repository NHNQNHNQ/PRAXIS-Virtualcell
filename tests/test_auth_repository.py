"""auth.repository 单元测试(FakeAuthRepository)。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from praxis2.auth.repository import (
    AuthRepository,
    EmailCodeRow,
    FakeAuthRepository,
    UserRow,
)


@pytest.mark.asyncio
async def test_create_user_and_get_by_email():
    repo = FakeAuthRepository()
    u = await repo.create_user(
        email="a@b.com", password_hash=b"$argon2$x", display_name="A", role="user"
    )
    assert isinstance(u, UserRow) and u.email == "a@b.com"
    assert len(u.id) >= 8
    got = await repo.get_user_by_email("a@b.com")
    assert got and got.id == u.id


@pytest.mark.asyncio
async def test_get_by_email_skips_soft_deleted_and_allows_reregister():
    repo = FakeAuthRepository()
    u = await repo.create_user(email="a@b.com", password_hash=b"h", display_name=None, role="user")
    await repo.soft_delete_user(u.id)
    assert await repo.get_user_by_email("a@b.com") is None
    u2 = await repo.create_user(
        email="a@b.com", password_hash=b"h2", display_name=None, role="user"
    )
    assert u2.id != u.id


@pytest.mark.asyncio
async def test_email_conflict_when_active():
    repo = FakeAuthRepository()
    await repo.create_user(email="a@b.com", password_hash=b"h", display_name=None, role="user")
    from praxis2.auth.errors import EmailConflict

    with pytest.raises(EmailConflict):
        await repo.create_user(email="a@b.com", password_hash=b"h2", display_name=None, role="user")


@pytest.mark.asyncio
async def test_get_by_id_and_update_last_login():
    repo = FakeAuthRepository()
    u = await repo.create_user(email="x@y.com", password_hash=b"h", display_name="x", role="admin")
    assert (await repo.get_user_by_id("non-existent")) is None
    await repo.update_last_login(u.id, ip="1.2.3.4", at=datetime(2026, 5, 20, tzinfo=UTC))
    got = await repo.get_user_by_id(u.id)
    assert got and got.role == "admin" and got.last_login_ip == "1.2.3.4"


@pytest.mark.asyncio
async def test_email_code_insert_latest_mark_used():
    repo = FakeAuthRepository()
    now = datetime.now(UTC)
    cid = await repo.insert_email_code(
        email="a@b.com",
        code="123456",
        purpose="register",
        expires_at=now + timedelta(minutes=5),
    )
    assert isinstance(cid, int)
    row = await repo.get_latest_email_code("a@b.com", "register")
    assert row and row.code == "123456" and not row.used
    await repo.mark_email_code_used(row.id)
    row2 = await repo.get_latest_email_code("a@b.com", "register")
    assert row2 is None


@pytest.mark.asyncio
async def test_email_code_attempts_incr():
    repo = FakeAuthRepository()
    now = datetime.now(UTC)
    cid = await repo.insert_email_code(
        email="a@b.com",
        code="123",
        purpose="login",
        expires_at=now + timedelta(minutes=5),
    )
    n = await repo.incr_email_code_attempts(cid)
    assert n == 1
    n = await repo.incr_email_code_attempts(cid)
    assert n == 2


@pytest.mark.asyncio
async def test_audit_insert_and_list():
    repo = FakeAuthRepository()
    await repo.insert_audit(
        user_id="u1",
        actor="self",
        action="login_success",
        resource="user",
        resource_id="u1",
        ip="1.1.1.1",
        ua="curl/8",
        meta={"foo": "bar"},
    )
    rows = await repo.list_audit_by_user("u1", limit=10)
    assert len(rows) == 1
    assert rows[0].action == "login_success" and rows[0].meta == {"foo": "bar"}


def test_fake_satisfies_protocol():
    assert isinstance(FakeAuthRepository(), AuthRepository)


def test_email_code_row_dataclass():
    """字段位:确保 EmailCodeRow 7 字段齐(防字段被误删)。"""
    import dataclasses

    fields = {f.name for f in dataclasses.fields(EmailCodeRow)}
    assert {
        "id",
        "email",
        "code",
        "purpose",
        "attempts",
        "used",
        "expires_at",
        "created_at",
    } <= fields


def test_userrow_has_realname_verified_at_field():
    """M9:UserRow 需含 realname_verified_at(TIMESTAMPTZ | None)以便 handle_me 算 bool。"""
    from praxis2.auth.repository import UserRow
    fields = {f.name for f in UserRow.__dataclass_fields__.values()}
    assert "realname_verified_at" in fields


async def test_inmemory_create_user_realname_verified_at_default_none():
    from praxis2.auth.repository import FakeAuthRepository
    repo = FakeAuthRepository()
    user = await repo.create_user(
        email="x@x", password_hash=b"x", display_name="X", role="user",
    )
    assert user.realname_verified_at is None
