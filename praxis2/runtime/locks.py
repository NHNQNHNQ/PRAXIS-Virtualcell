import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Protocol


class LockBackend(Protocol):
    async def acquire(self, key: str) -> None: ...
    async def release(self, key: str) -> None: ...


class InMemoryLockBackend:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock(self, key: str) -> asyncio.Lock:

        return self._locks.setdefault(key, asyncio.Lock())

    async def acquire(self, key: str) -> None:
        await self._lock(key).acquire()

    async def release(self, key: str) -> None:
        self._locks[key].release()


class SessionLock:
    def __init__(self, backend: LockBackend) -> None:
        self._backend = backend

    def key(self, user_id: str, session_id: str) -> str:
        if not user_id or not session_id:
            raise ValueError("SessionLock requires nonempty user_id and session_id")
        return f"{user_id}:{session_id}"


@asynccontextmanager
async def acquire_session_lock(backend: LockBackend, user_id: str, session_id: str) -> AsyncIterator[None]:

    k = SessionLock(backend).key(user_id, session_id)
    await backend.acquire(k)
    try:
        yield
    finally:
        await backend.release(k)


class RedisLockBackend:
    _RELEASE_LUA = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"

    def __init__(self, url: str, *, ttl_ms: int = 30000) -> None:
        import redis.asyncio as aioredis

        self._r = aioredis.from_url(url)
        self._ttl_ms = ttl_ms
        self._tokens: dict[str, str] = {}

    async def acquire(self, key: str) -> None:
        import uuid

        token = uuid.uuid4().hex

        delay = 0.005
        while not await self._r.set(key, token, nx=True, px=self._ttl_ms):
            await asyncio.sleep(delay)
            delay = min(delay * 2, 0.05)
        self._tokens[key] = token

    async def release(self, key: str) -> None:
        token = self._tokens.pop(key, None)
        if token is not None:
            await self._r.eval(self._RELEASE_LUA, 1, key, token)

    async def aclose(self) -> None:
        await self._r.aclose()
