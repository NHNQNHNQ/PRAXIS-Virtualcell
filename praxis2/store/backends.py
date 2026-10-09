import redis.asyncio as aioredis

from praxis2.store.base import Namespace


class RedisKVStore:
    def __init__(self, url: str):
        self._r = aioredis.from_url(url)

    async def kv_set(self, ns: Namespace, key: str, value: bytes, ttl_s: float | None = None) -> None:

        px = int(ttl_s * 1000) if ttl_s else None
        await self._r.set(ns.key(key), value, px=px)

    async def kv_get(self, ns: Namespace, key: str) -> bytes | None:
        return await self._r.get(ns.key(key))

    async def kv_delete(self, ns: Namespace, key: str) -> None:
        await self._r.delete(ns.key(key))

    async def aclose(self) -> None:
        await self._r.aclose()


class PgMetaStore:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._conn = None

    async def ping(self) -> None:
        import asyncpg

        self._conn = await asyncpg.connect(self._dsn)
        assert await self._conn.fetchval("SELECT 1") == 1

    async def aclose(self) -> None:
        if self._conn is not None:
            await self._conn.close()
