"""scripts/create_admin.py + scripts/migrate_v1_users.py 单元测试。"""

from __future__ import annotations

import sys

import pytest


@pytest.mark.asyncio
async def test_create_admin_inserts_role_admin():
    from praxis2.auth.repository import FakeAuthRepository
    from scripts.create_admin import create_admin

    repo = FakeAuthRepository()
    user_id = await create_admin(
        repo=repo,
        email="admin@p",
        password="adm1n-pw",
        display_name="Admin",
        pepper="test-pepper",
    )
    row = await repo.get_user_by_id(user_id)
    assert row and row.role == "admin"
    assert row.email == "admin@p"
    audits = await repo.list_audit_by_user(user_id, limit=10)
    assert any(a.action == "admin_seed" for a in audits)


@pytest.mark.asyncio
async def test_create_admin_refuses_when_email_exists():
    from praxis2.auth.errors import EmailConflict
    from praxis2.auth.repository import FakeAuthRepository
    from scripts.create_admin import create_admin

    repo = FakeAuthRepository()
    await create_admin(repo=repo, email="x@y", password="pw", display_name="X", pepper="p")
    with pytest.raises(EmailConflict):
        await create_admin(repo=repo, email="x@y", password="pw2", display_name="X2", pepper="p")


def test_create_admin_cli_parses_args(monkeypatch, capsys):
    """CLI 入口可解参 + 运行不报。"""
    import scripts.create_admin as mod
    from praxis2.auth.repository import FakeAuthRepository

    fake_repo = FakeAuthRepository()
    monkeypatch.setattr(mod, "_make_repo_from_env", lambda: fake_repo)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "create_admin",
            "--email",
            "cli@p",
            "--password",
            "cli-pw",
            "--display-name",
            "CLI",
            "--pepper",
            "p",
        ],
    )
    mod.main()
    out = capsys.readouterr().out
    assert "已创建 admin user:" in out


@pytest.mark.asyncio
async def test_migrate_v1_users_stub_handles_synthetic_dump():
    """合成 v1 dump dict → 调 migrate_users_from_v1_dump → Fake repo INSERT。"""
    from praxis2.auth.repository import FakeAuthRepository
    from scripts.migrate_v1_users import migrate_users_from_v1_dump

    fake_dump = [
        {
            "id": "uuid-1",
            "email": "u1@v1",
            "phone": None,
            "password_hash": "$argon2id$xxx",
            "display_name": "U1",
            "role": "user",
            "created_at": "2026-05-01T00:00:00Z",
        },
        {
            "id": "uuid-2",
            "email": "u2@v1",
            "phone": None,
            "password_hash": "$argon2id$yyy",
            "display_name": "U2",
            "role": "admin",
            "created_at": "2026-05-02T00:00:00Z",
        },
    ]
    repo = FakeAuthRepository()
    n = await migrate_users_from_v1_dump(fake_dump, repo=repo)
    assert n == 2
    u1 = await repo.get_user_by_email("u1@v1")
    assert u1 and u1.role == "user"
    u2 = await repo.get_user_by_email("u2@v1")
    assert u2 and u2.role == "admin"


@pytest.mark.asyncio
async def test_migrate_v1_users_skips_duplicate_email():
    from praxis2.auth.repository import FakeAuthRepository
    from scripts.migrate_v1_users import migrate_users_from_v1_dump

    repo = FakeAuthRepository()
    await repo.create_user(
        email="dup@v1", password_hash=b"existing", display_name="EXISTING", role="user"
    )
    n = await migrate_users_from_v1_dump(
        [
            {
                "id": "uuid-3",
                "email": "dup@v1",
                "phone": None,
                "password_hash": "$argon2id$dup",
                "display_name": "DUP",
                "role": "user",
                "created_at": "2026-05-03T00:00:00Z",
            },
        ],
        repo=repo,
    )
    assert n == 0
