"""§11.3 同 {user_id}:{session_id} 串行化锁。

请求落任意无状态 worker → 先取本锁保证同会话串行(根除多标签页/
重连并发写 transcript 错乱,§10 风险登记「同会话并发写冲突」)。
不同 session 不互斥(横扩前提:无 sticky 依赖)。

内存版 InMemoryLockBackend(单进程 asyncio.Lock per key)保证正确性可测;
真 RedisLockBackend(SET NX PX + TTL,看门狗续约 M7)标 integration(M6 校准②,
真分布式实测留装 docker 后,类比 v1 §7 多 worker 路径写好未启用)。"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Protocol


class LockBackend(Protocol):
    async def acquire(self, key: str) -> None: ...
    async def release(self, key: str) -> None: ...


class InMemoryLockBackend:
    """单进程:每 key 一把 asyncio.Lock(同 key 串行,异 key 并发)。"""

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock(self, key: str) -> asyncio.Lock:
        # 同 key 复用同一 Lock 实例(否则串行化失效);异 key 各自独立
        return self._locks.setdefault(key, asyncio.Lock())

    async def acquire(self, key: str) -> None:
        await self._lock(key).acquire()

    async def release(self, key: str) -> None:
        self._locks[key].release()


class SessionLock:
    """锁 key = {user_id}:{session_id}(§11.3)。"""

    def __init__(self, backend: LockBackend) -> None:
        self._backend = backend

    def key(self, user_id: str, session_id: str) -> str:
        if not user_id or not session_id:
            raise ValueError("SessionLock 需非空 user_id 与 session_id(§11.6)")
        return f"{user_id}:{session_id}"


@asynccontextmanager
async def acquire_session_lock(
    backend: LockBackend, user_id: str, session_id: str
) -> AsyncIterator[None]:
    """同会话串行化(§11.3)。异常路径仍释放锁(防死锁,代码级保证;
    Redis 后端另有 TTL+看门狗兜进程崩溃)。"""
    k = SessionLock(backend).key(user_id, session_id)
    await backend.acquire(k)
    try:
        yield
    finally:
        await backend.release(k)


class RedisLockBackend:
    """真 Redis 分布式锁:SET key token NX PX=ttl + TTL(看门狗续约 M7)+ Lua 原子释放。
    M6 接口位 + 标 integration(总纲校准②,真分布式实测留装 docker 后)。
    单进程内存版已锁死同 key 串行正确性;本类语义对齐,实测在 docker 环境。"""

    _RELEASE_LUA = (
        "if redis.call('get', KEYS[1]) == ARGV[1] "
        "then return redis.call('del', KEYS[1]) else return 0 end"
    )

    def __init__(self, url: str, *, ttl_ms: int = 30000) -> None:
        import redis.asyncio as aioredis

        self._r = aioredis.from_url(url)
        self._ttl_ms = ttl_ms
        self._tokens: dict[str, str] = {}

    async def acquire(self, key: str) -> None:
        import uuid

        token = uuid.uuid4().hex
        # 自旋等待(指数退避上限 50ms);看门狗续约由调用周期短于 ttl 保证,
        # 第一版不起独立续约任务(轻量 LLM 通道单轮 < ttl;长任务 M7 续约)
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
