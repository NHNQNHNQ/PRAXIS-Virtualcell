"""PgAuthRepository profile + balance 方法 integration 测试。"""
from __future__ import annotations

import os
import uuid

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
async def repo():
    pytest.importorskip("asyncpg")
    import asyncpg

    from praxis2.auth.repository_pg import PgAuthRepository
    url = os.environ.get("PRAXIS_DB_URL", "")
    if not url:
        pytest.skip("PRAXIS_DB_URL not set")
    pool = await asyncpg.create_pool(url.replace("postgresql+asyncpg://", "postgresql://"))
    yield PgAuthRepository(pool)
    await pool.close()


@pytest.fixture
async def user(repo):
    u = await repo.create_user(
        email=f"t_{uuid.uuid4()}@x", password_hash=b"x",
        display_name="X", role="user",
    )
    yield u
    async with repo._pool.acquire() as conn:
        await conn.execute("DELETE FROM user_profiles WHERE user_id=$1", uuid.UUID(u.id))
        await conn.execute("DELETE FROM ledger WHERE user_id=$1", uuid.UUID(u.id))
        await conn.execute("DELETE FROM users WHERE id=$1", uuid.UUID(u.id))


async def test_get_user_profile_returns_none_when_absent(repo, user):
    p = await repo.get_user_profile(user.id)
    assert p is None


async def test_upsert_user_profile_creates_row_when_absent(repo, user):
    await repo.upsert_user_profile(user.id, research_field="Bio", affiliation="X Univ")
    p = await repo.get_user_profile(user.id)
    assert p["research_field"] == "Bio"
    assert p["affiliation"] == "X Univ"
    assert p["expertise_level"] is None
    assert p["projects"] is None
    assert p["custom_intro"] is None
    assert p["updated_at"] is not None


async def test_upsert_partial_keeps_existing(repo, user):
    await repo.upsert_user_profile(user.id, research_field="Bio")
    await repo.upsert_user_profile(user.id, affiliation="Y Inst")
    p = await repo.get_user_profile(user.id)
    assert p["research_field"] == "Bio"
    assert p["affiliation"] == "Y Inst"


async def test_upsert_none_value_clears_field(repo, user):
    """null = 清空(handler 转 None 后传到 repo,repo SET NULL)。"""
    await repo.upsert_user_profile(user.id, research_field="Bio")
    await repo.upsert_user_profile(user.id, research_field=None)
    p = await repo.get_user_profile(user.id)
    assert p["research_field"] is None


async def test_get_user_with_balance_includes_balance_li(repo, user):
    u = await repo.get_user_with_balance(user.id)
    assert u["balance_li"] == 0
    assert u["email"] == user.email
    assert u["plan"] == "free"
    assert u["realname_verified"] is False
    assert u["created_at"] is not None
