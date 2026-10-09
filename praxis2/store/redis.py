"""Redis-backed key-value storage; use PgStore for blobs and metadata."""

from __future__ import annotations

from praxis2.store.base import Namespace, Store


def make_redis_client(url: str, decode_responses: bool = True):
    """Create an asynchronous Redis client with the selected response decoding mode."""
    import redis.asyncio as aioredis

    return aioredis.from_url(url, decode_responses=decode_responses)


class RedisStore(Store):
    def __init__(self, client) -> None:
        self._c = client

    async def kv_set(self, ns: Namespace, key: str, value: bytes, ttl_s: float | None = None) -> None:
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
        raise NotImplementedError("Use PgStore for blobs")

    async def blob_get(self, ns, key):
        raise NotImplementedError("Use PgStore for blobs")

    async def blob_append(self, ns, key, chunk):
        raise NotImplementedError("Use PgStore for blobs")

    async def meta_upsert(self, table, row):
        raise NotImplementedError("Use PgStore for metadata")

    async def meta_get(self, table, user_id, pk):
        raise NotImplementedError("Use PgStore for metadata")

    async def meta_list(self, table, user_id):
        raise NotImplementedError("Use PgStore for metadata")
