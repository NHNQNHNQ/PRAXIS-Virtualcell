"""RedisStore + auth session ops + login_fail/email_throttle(单元层 fakeredis)。"""

from __future__ import annotations

import pytest

from praxis2.store.base import Namespace


@pytest.mark.asyncio
async def test_redis_store_kv_set_get_delete():
    pytest.importorskip("fakeredis")
    import fakeredis.aioredis

    from praxis2.store.redis import RedisStore

    client = fakeredis.aioredis.FakeRedis()
    st = RedisStore(client)
    ns = Namespace(user_id="u1", scope="cache")
    await st.kv_set(ns, "k1", b"hello")
    assert await st.kv_get(ns, "k1") == b"hello"
    await st.kv_delete(ns, "k1")
    assert await st.kv_get(ns, "k1") is None
    await client.aclose()


@pytest.mark.asyncio
async def test_auth_session_set_get_del():
    pytest.importorskip("fakeredis")
    import fakeredis.aioredis

    from praxis2.store.redis import auth_session_del, auth_session_get, auth_session_set

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await auth_session_set(
        client, "tok-abc", {"user_id": "u1", "email": "a@b"}, ttl_s=300, pepper="test"
    )
    got = await auth_session_get(client, "tok-abc", pepper="test")
    assert got and got["user_id"] == "u1" and got["email"] == "a@b"
    await auth_session_del(client, "tok-abc", pepper="test")
    assert await auth_session_get(client, "tok-abc", pepper="test") is None
    await client.aclose()


@pytest.mark.asyncio
async def test_user_sessions_add_drain_returns_all_tokens():
    pytest.importorskip("fakeredis")
    import fakeredis.aioredis

    from praxis2.store.redis import user_sessions_add, user_sessions_drain

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    for t in ("tok1", "tok2", "tok3"):
        await user_sessions_add(client, "u1", t, ttl_s=300)
    drained = await user_sessions_drain(client, "u1")
    assert set(drained) == {"tok1", "tok2", "tok3"}
    assert await user_sessions_drain(client, "u1") == []
    await client.aclose()


@pytest.mark.asyncio
async def test_login_fail_incr_resets():
    pytest.importorskip("fakeredis")
    import fakeredis.aioredis

    from praxis2.store.redis import login_fail_incr, login_fail_reset

    c = fakeredis.aioredis.FakeRedis(decode_responses=True)
    assert await login_fail_incr(c, "a@b.com") == 1
    assert await login_fail_incr(c, "a@b.com") == 2
    await login_fail_reset(c, "a@b.com")
    assert await login_fail_incr(c, "a@b.com") == 1
    await c.aclose()


@pytest.mark.asyncio
async def test_email_throttle_first_ok_second_blocked():
    pytest.importorskip("fakeredis")
    import fakeredis.aioredis

    from praxis2.store.redis import email_throttle_check

    c = fakeredis.aioredis.FakeRedis(decode_responses=True)
    assert await email_throttle_check(c, "a@b.com", ttl_s=60) is True
    assert await email_throttle_check(c, "a@b.com", ttl_s=60) is False
    await c.aclose()
