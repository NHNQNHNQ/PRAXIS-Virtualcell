import asyncio

import pytest

from praxis2.runtime.locks import (
    InMemoryLockBackend,
    SessionLock,
    acquire_session_lock,
)


def test_session_lock_key_is_user_scoped():

    lk = SessionLock(InMemoryLockBackend())
    assert lk.key("u1", "s1") == "u1:s1"
    assert lk.key("u1", "s2") != lk.key("u1", "s1")
    assert lk.key("u2", "s1") != lk.key("u1", "s1")


async def test_same_session_requests_serialized():

    backend = InMemoryLockBackend()
    order: list[str] = []

    async def worker(tag: str) -> None:
        async with acquire_session_lock(backend, "u1", "s1"):
            order.append(f"{tag}-enter")
            await asyncio.sleep(0.01)
            order.append(f"{tag}-exit")

    await asyncio.gather(worker("A"), worker("B"))

    assert order in (
        ["A-enter", "A-exit", "B-enter", "B-exit"],
        ["B-enter", "B-exit", "A-enter", "A-exit"],
    )


async def test_different_sessions_run_concurrently():

    backend = InMemoryLockBackend()
    started = asyncio.Event()

    async def hold_s1() -> None:
        async with acquire_session_lock(backend, "u1", "s1"):
            started.set()
            await asyncio.sleep(0.05)

    async def quick_s2() -> bool:
        await started.wait()
        async with acquire_session_lock(backend, "u1", "s2"):
            return True

    t1 = asyncio.create_task(hold_s1())
    got = await asyncio.wait_for(quick_s2(), timeout=0.5)
    await t1
    assert got is True


async def test_lock_released_on_exception():

    backend = InMemoryLockBackend()
    with pytest.raises(RuntimeError):
        async with acquire_session_lock(backend, "u1", "s1"):
            raise RuntimeError("boom")

    async with acquire_session_lock(backend, "u1", "s1"):
        pass


@pytest.mark.integration
async def test_redis_lock_backend_smoke():

    from praxis2.runtime.locks import RedisLockBackend

    backend = RedisLockBackend("redis://localhost:6379/0")
    async with acquire_session_lock(backend, "u1", "s1"):
        pass
    await backend.aclose()
