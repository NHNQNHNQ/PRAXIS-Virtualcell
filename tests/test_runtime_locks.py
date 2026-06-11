import asyncio

import pytest

from praxis2.runtime.locks import (
    InMemoryLockBackend,
    SessionLock,
    acquire_session_lock,
)


def test_session_lock_key_is_user_scoped():
    # §11.3:锁 key = {user_id}:{session_id}(同会话串行,跨会话/跨用户不互斥)
    lk = SessionLock(InMemoryLockBackend())
    assert lk.key("u1", "s1") == "u1:s1"
    assert lk.key("u1", "s2") != lk.key("u1", "s1")
    assert lk.key("u2", "s1") != lk.key("u1", "s1")


async def test_same_session_requests_serialized():
    # 同 {user,session} 两并发请求被锁串行(无交错)——根除 transcript 错乱
    backend = InMemoryLockBackend()
    order: list[str] = []

    async def worker(tag: str) -> None:
        async with acquire_session_lock(backend, "u1", "s1"):
            order.append(f"{tag}-enter")
            await asyncio.sleep(0.01)
            order.append(f"{tag}-exit")

    await asyncio.gather(worker("A"), worker("B"))
    # 串行:必须 enter/exit 成对不交错(A 全程在 B 之前 或 反之)
    assert order in (
        ["A-enter", "A-exit", "B-enter", "B-exit"],
        ["B-enter", "B-exit", "A-enter", "A-exit"],
    )


async def test_different_sessions_run_concurrently():
    # 不同 session 不互斥(横扩前提:无 sticky 依赖,§11.3)
    backend = InMemoryLockBackend()
    started = asyncio.Event()

    async def hold_s1() -> None:
        async with acquire_session_lock(backend, "u1", "s1"):
            started.set()
            await asyncio.sleep(0.05)

    async def quick_s2() -> bool:
        await started.wait()
        async with acquire_session_lock(backend, "u1", "s2"):
            return True  # s2 不被 s1 的锁挡住

    t1 = asyncio.create_task(hold_s1())
    got = await asyncio.wait_for(quick_s2(), timeout=0.5)
    await t1
    assert got is True


async def test_lock_released_on_exception():
    # 锁内抛异常仍释放(防死锁:看门狗/TTL 之外的代码级保证)
    backend = InMemoryLockBackend()
    with pytest.raises(RuntimeError):
        async with acquire_session_lock(backend, "u1", "s1"):
            raise RuntimeError("boom")
    # 能再次获取即证明已释放
    async with acquire_session_lock(backend, "u1", "s1"):
        pass


@pytest.mark.integration
async def test_redis_lock_backend_smoke():
    # 真 Redis 分布式锁(SET NX PX + 看门狗)——无 docker 自动 skip(总纲校准②)
    from praxis2.runtime.locks import RedisLockBackend

    backend = RedisLockBackend("redis://localhost:6379/0")
    async with acquire_session_lock(backend, "u1", "s1"):
        pass
    await backend.aclose()
