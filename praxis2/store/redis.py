"""Redis Store + auth session 专用 ops(v1.1 carry ① 关闭,§11.4)。

KV 直接 SET/GET/DEL;Blob/Meta 不在 Redis(NotImplementedError → 转 PgStore)。
auth session 用 HSET/HGETALL + EXPIRE;user_sessions SADD/SMEMBERS/DEL(logout-all)。
session key = HMAC-SHA256(pepper, token);hset+expire 经 pipeline 原子提交(Phase A.3+A.4)。
login_fail INCR + EX 5min(暴破锁定);email_throttle SET NX EX 60s(send-code 频控)。
"""

from __future__ import annotations

import json

from praxis2.auth.cookie_hash import session_key_from_token
from praxis2.store.base import Namespace, Store


def make_redis_client(url: str, decode_responses: bool = True):
    """aioredis client 工厂(统一所有 redis 访问入口)。"""
    import redis.asyncio as aioredis

    return aioredis.from_url(url, decode_responses=decode_responses)


class RedisStore(Store):
    """KV 真实现;Blob/Meta 走 PgStore。"""

    def __init__(self, client) -> None:
        self._c = client

    async def kv_set(
        self, ns: Namespace, key: str, value: bytes, ttl_s: float | None = None
    ) -> None:
        k = ns.key(key)
        if ttl_s is not None:
            await self._c.set(k, value, ex=int(ttl_s))
        else:
            await self._c.set(k, value)

    async def kv_get(self, ns: Namespace, key: str) -> bytes | None:
        v = await self._c.get(ns.key(key))
        if v is None:
            return None
        return v.encode() if isinstance(v, str) else v

    async def kv_delete(self, ns: Namespace, key: str) -> None:
        await self._c.delete(ns.key(key))

    async def blob_put(self, ns, key, data):
        raise NotImplementedError("Blob 走 PgStore")

    async def blob_get(self, ns, key):
        raise NotImplementedError("Blob 走 PgStore")

    async def blob_append(self, ns, key, chunk):
        raise NotImplementedError("Blob 走 PgStore")

    async def meta_upsert(self, table, row):
        raise NotImplementedError("Meta 走 PgStore")

    async def meta_get(self, table, user_id, pk):
        raise NotImplementedError("Meta 走 PgStore")

    async def meta_list(self, table, user_id):
        raise NotImplementedError("Meta 走 PgStore")


# ── auth session ops(opaque token + 可服务端撤销,design §5.3)──────
# Phase A.3+A.4(M9 C3+C4):cookie 持原 token,Redis 存 HMAC-SHA256(pepper, token)。
# hset + expire 用 pipeline(transaction=True) 原子提交,防 TTL 漏失。


def _session_redis_key(token: str, *, pepper: str) -> str:
    """统一 session Redis key 拼装,改 prefix 只动这里。"""
    return f"session:{session_key_from_token(token, pepper=pepper)}"


async def auth_session_set(
    client, token: str, data: dict, ttl_s: int, *, pepper: str
) -> None:
    """HMAC key + 原子 hset+expire(防 Redis 泄露 + 防 TTL 漏失)。"""
    key = _session_redis_key(token, pepper=pepper)
    async with client.pipeline(transaction=True) as pipe:
        pipe.hset(key, mapping={k: json.dumps(v) for k, v in data.items()})
        pipe.expire(key, ttl_s)
        await pipe.execute()


async def auth_session_get(client, token: str, *, pepper: str) -> dict | None:
    key = _session_redis_key(token, pepper=pepper)
    raw = await client.hgetall(key)
    if not raw:
        return None
    return {k: json.loads(v) for k, v in raw.items()}


async def auth_session_del(client, token: str, *, pepper: str) -> None:
    await client.delete(_session_redis_key(token, pepper=pepper))


# ── user_sessions(logout-all)─────────────────────────────────────────


async def user_sessions_add(client, user_id: str, token: str, ttl_s: int) -> None:
    key = f"user_sessions:{user_id}"
    await client.sadd(key, token)
    await client.expire(key, ttl_s)


async def user_sessions_drain(client, user_id: str) -> list[str]:
    """SMEMBERS + DEL 取出所有 token(logout-all 用)。"""
    key = f"user_sessions:{user_id}"
    async with client.pipeline(transaction=True) as pipe:
        pipe.smembers(key)
        pipe.delete(key)
        results = await pipe.execute()
    members = results[0]
    return list(members) if members else []


# ── login_fail 锁定 + email send 频控 ─────────────────────


async def login_fail_incr(client, email: str, ttl_s: int = 300) -> int:
    key = f"login_fail:{email}"
    n = await client.incr(key)
    if n == 1:
        await client.expire(key, ttl_s)
    return int(n)


async def login_fail_reset(client, email: str) -> None:
    await client.delete(f"login_fail:{email}")


async def login_fail_incr_ip(client, ip: str, ttl_s: int = 300) -> int:
    """per-IP 计数:防扫号(不同 email 但同 IP 也累加)。"""
    key = f"login_fail_ip:{ip}"
    n = await client.incr(key)
    if n == 1:
        await client.expire(key, ttl_s)
    return int(n)


async def login_fail_reset_ip(client, ip: str) -> None:
    await client.delete(f"login_fail_ip:{ip}")


async def email_throttle_check(client, email: str, ttl_s: int = 60) -> bool:
    """True = 放行(无最近发送),False = 频控拒绝(60s 内已发)。"""
    set_ok = await client.set(f"email_throttle:{email}", "1", nx=True, ex=ttl_s)
    return bool(set_ok)
