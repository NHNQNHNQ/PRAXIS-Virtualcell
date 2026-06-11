"""真实后端骨架。M4/M6 充实(连接池/事务/迁移);M0 仅连接+基本读写,
复用 Task 7 契约语义。集成测试默认 skip(总纲 §5⑩)。"""

import redis.asyncio as aioredis

from praxis2.store.base import Namespace


class RedisKVStore:
    def __init__(self, url: str):
        self._r = aioredis.from_url(url)

    async def kv_set(
        self, ns: Namespace, key: str, value: bytes, ttl_s: float | None = None
    ) -> None:
        # 用 px(毫秒)而非 ex(秒):sub-second TTL 经 ex=int() 会截断为 0,
        # Redis 拒绝 "EX 0"(invalid expire time)。ttl_s=0.0 为 falsy → None
        # (无过期);0/负 TTL 的精确语义留待 M4 定义。
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
