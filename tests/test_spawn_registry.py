import asyncio

import pytest

from praxis2.spawn.registry import SpawnRegistry


@pytest.mark.asyncio
async def test_register_and_cancel():
    reg = SpawnRegistry()

    started = asyncio.Event()
    cancelled = False

    async def long_task():
        nonlocal cancelled
        started.set()
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled = True
            raise

    task = asyncio.create_task(long_task())
    reg.register("tid-1", task)
    await started.wait()

    assert reg.cancel("tid-1") is True
    try:
        await task
    except asyncio.CancelledError:
        pass
    assert cancelled is True


@pytest.mark.asyncio
async def test_cancel_unknown_returns_false():
    reg = SpawnRegistry()
    assert reg.cancel("nope") is False


@pytest.mark.asyncio
async def test_unregister_after_done():
    reg = SpawnRegistry()

    async def quick():
        return 42

    task = asyncio.create_task(quick())
    reg.register("tid-2", task)
    await task
    reg.unregister("tid-2")
    assert reg.cancel("tid-2") is False
