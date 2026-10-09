"""Phase A.3+A.4:session token HMAC + HSET+EXPIRE 原子化(反 Redis 泄露 + 反 TTL 漏失)。"""

import pytest

from praxis2.auth.cookie_hash import session_key_from_token
from praxis2.store.redis import auth_session_del, auth_session_get, auth_session_set

# ─── cookie_hash 工具不变式 ───────────────────────────────────────


def test_session_key_deterministic_same_pepper():
    k1 = session_key_from_token("raw_token_abc", pepper="p1")
    k2 = session_key_from_token("raw_token_abc", pepper="p1")
    assert k1 == k2


def test_session_key_differs_per_token():
    k1 = session_key_from_token("token_a", pepper="p1")
    k2 = session_key_from_token("token_b", pepper="p1")
    assert k1 != k2


def test_session_key_differs_per_pepper():
    """Pepper rotation invariant:换 pepper 旧 session 自动失效。"""
    k1 = session_key_from_token("token_a", pepper="p1")
    k2 = session_key_from_token("token_a", pepper="p2")
    assert k1 != k2


def test_session_key_not_reveal_token():
    """HMAC 应不含明文。"""
    k = session_key_from_token("super_secret_token", pepper="p")
    assert "super_secret_token" not in k
    assert len(k) == 64  # hex of sha256


def test_session_key_rejects_empty_token():
    with pytest.raises(ValueError, match="token 必填"):
        session_key_from_token("", pepper="p")


def test_session_key_rejects_empty_pepper():
    with pytest.raises(ValueError, match="pepper 必填"):
        session_key_from_token("t", pepper="")


# ─── Redis 集成不变式 ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_redis_key_is_hashed_not_raw_token():
    """Redis 实际 key 必须是 HMAC 哈希,而非原 token。"""
    import fakeredis.aioredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    raw_token = "raw_session_token_xyz_lots_of_chars"
    pepper = "test_pepper"

    await auth_session_set(
        client, raw_token, {"user_id": "u1"}, ttl_s=3600, pepper=pepper
    )

    # 原 token 作 key:不存在
    assert not await client.exists(f"session:{raw_token}")
    # HMAC 路径:存在
    hashed = session_key_from_token(raw_token, pepper=pepper)
    assert await client.exists(f"session:{hashed}")
    await client.aclose()


@pytest.mark.asyncio
async def test_get_round_trip_through_hash():
    """get 透过 raw_token + pepper 仍能取回数据。"""
    import fakeredis.aioredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await auth_session_set(
        client, "tok", {"user_id": "u1", "email": "x@y"}, ttl_s=300, pepper="p"
    )
    data = await auth_session_get(client, "tok", pepper="p")
    assert data is not None
    assert data["user_id"] == "u1"
    assert data["email"] == "x@y"
    await client.aclose()


@pytest.mark.asyncio
async def test_pepper_rotation_invalidates_old_sessions():
    """换 pepper 即旧 session 失效(rotation 真生效)。"""
    import fakeredis.aioredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await auth_session_set(
        client, "tok", {"user_id": "u1"}, ttl_s=300, pepper="old_pepper"
    )
    assert await auth_session_get(client, "tok", pepper="new_pepper") is None
    await client.aclose()


@pytest.mark.asyncio
async def test_del_uses_hashed_key():
    """del 也走哈希路径,保证 token 不漏。"""
    import fakeredis.aioredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await auth_session_set(client, "tok", {"u": "u1"}, ttl_s=300, pepper="p")
    hashed = session_key_from_token("tok", pepper="p")
    assert await client.exists(f"session:{hashed}")
    await auth_session_del(client, "tok", pepper="p")
    assert not await client.exists(f"session:{hashed}")
    await client.aclose()


@pytest.mark.asyncio
async def test_hset_expire_is_atomic_via_pipeline():
    """A.4:hset + expire 通过 pipeline transaction 原子提交,防止 TTL 漏失。

    用 monkey-patch 计数 pipeline.execute / 单独 expire 调用次数验证。"""
    import fakeredis.aioredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)

    # 包装 pipeline 计数
    orig_pipeline = client.pipeline
    pipeline_calls = []

    def wrapped_pipeline(*args, **kwargs):
        pipeline_calls.append((args, kwargs))
        return orig_pipeline(*args, **kwargs)

    client.pipeline = wrapped_pipeline

    # 包装 expire 计数:如果有 standalone expire(非 pipeline 内)说明非原子
    standalone_expire = 0
    orig_expire = client.expire

    async def wrapped_expire(*args, **kwargs):
        nonlocal standalone_expire
        standalone_expire += 1
        return await orig_expire(*args, **kwargs)

    client.expire = wrapped_expire

    await auth_session_set(client, "tok", {"u": "u1"}, ttl_s=60, pepper="p")

    assert len(pipeline_calls) == 1, f"应走 pipeline 一次,实际 {len(pipeline_calls)}"
    assert standalone_expire == 0, (
        f"不应有 standalone expire 调用,实际 {standalone_expire};说明 hset+expire 没原子化"
    )

    # 验证 TTL 真的设上了
    hashed = session_key_from_token("tok", pepper="p")
    ttl = await client.ttl(f"session:{hashed}")
    assert ttl > 0 and ttl <= 60
    await client.aclose()
