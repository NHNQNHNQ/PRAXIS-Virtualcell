import asyncio
import sys

import pytest

from praxis2.mcp.config import MCPServerSpec
from praxis2.mcp.pool import MCPConnectionPool


def _echo_spec(name="echo"):

    return MCPServerSpec(
        name=name,
        command=sys.executable,
        args=["-m", "praxis2.mcp.echo_server"],
        env={},
    )


@pytest.mark.asyncio
async def test_pool_start_spawns_and_lists_tools():
    pool = MCPConnectionPool([_echo_spec()])
    await pool.start_all()
    try:
        tools = pool.all_tools()
        names = sorted(t.name for t in tools)
        assert "mcp__echo__echo" in names
        assert "mcp__echo__add" in names
    finally:
        await pool.close_all()


@pytest.mark.asyncio
async def test_pool_tool_call_roundtrip():
    pool = MCPConnectionPool([_echo_spec()])
    await pool.start_all()
    try:
        echo_tool = next(t for t in pool.all_tools() if t.name == "mcp__echo__echo")
        r = await echo_tool.run({"text": "v0.17 ok"})
        assert r.ok
        assert "echo: v0.17 ok" in r.value
        add_tool = next(t for t in pool.all_tools() if t.name == "mcp__echo__add")
        r2 = await add_tool.run({"a": 3, "b": 4})
        assert r2.ok
        assert "7" in r2.value
    finally:
        await pool.close_all()


@pytest.mark.asyncio
async def test_pool_start_all_idempotent():
    pool = MCPConnectionPool([_echo_spec()])
    await pool.start_all()
    n1 = len(pool.all_tools())
    await pool.start_all()
    try:
        assert len(pool.all_tools()) == n1
    finally:
        await pool.close_all()


@pytest.mark.asyncio
async def test_pool_bad_server_skipped_not_crash():

    bad = MCPServerSpec(name="bad", command="/nonexistent/binary_xyz", args=[], env={})
    pool = MCPConnectionPool([bad, _echo_spec(name="good")], retry=1)
    await pool.start_all()
    try:
        names = [t.name for t in pool.all_tools()]
        assert any(n.startswith("mcp__good__") for n in names)
        audit = pool.audit_log()
        assert any(a["server"] == "bad" for a in audit)
    finally:
        await pool.close_all()


@pytest.mark.asyncio
async def test_pool_empty_specs_no_tools():
    pool = MCPConnectionPool([])
    await pool.start_all()
    assert pool.all_tools() == []
    await pool.close_all()


@pytest.mark.asyncio
async def test_pool_slow_server_startup_timeout_skipped():

    slow = MCPServerSpec(
        name="slow",
        command=sys.executable,
        args=["-c", "import time; time.sleep(60)"],
        env={},
        startup_timeout_s=1.0,
    )
    good = MCPServerSpec(
        name="good",
        command=sys.executable,
        args=["-m", "praxis2.mcp.echo_server"],
        env={},
        startup_timeout_s=10.0,
    )
    pool = MCPConnectionPool(
        [slow, good],
        retry=0,
        startup_timeout_s=0.01,
    )
    await pool.start_all()
    try:
        names = [t.name for t in pool.all_tools()]

        assert any(n.startswith("mcp__good__") for n in names)

        assert any(a["server"] == "slow" for a in pool.audit_log())
    finally:
        await pool.close_all()


@pytest.mark.asyncio
async def test_pool_cross_task_call_tool_works():

    pool = MCPConnectionPool([_echo_spec()])
    await asyncio.create_task(pool.start_all())  # task A spawn
    try:

        async def _call():
            tool = next(t for t in pool.all_tools() if t.name == "mcp__echo__echo")
            return await tool.run({"text": "xtask"})

        r = await asyncio.create_task(_call())
        assert r.ok
        assert "echo: xtask" in r.value
    finally:
        await pool.close_all()


@pytest.mark.asyncio
async def test_pool_cross_task_close_does_not_raise():

    pool = MCPConnectionPool([_echo_spec()])
    await asyncio.create_task(pool.start_all())  # task A

    async def _close():
        await pool.close_all()

    await asyncio.create_task(_close())
    assert pool.all_tools() == []


@pytest.mark.asyncio
async def test_lazy_once_start_idempotent():

    spec = _echo_spec()
    pool = MCPConnectionPool([spec])
    started = {"v": False}

    async def ensure():
        if started["v"]:
            return
        started["v"] = True
        await pool.start_all()

    await ensure()
    await ensure()
    try:
        assert len([t for t in pool.all_tools() if t.name.startswith("mcp__echo__")]) == 2
    finally:
        await pool.close_all()


@pytest.mark.asyncio
async def test_ensure_mcp_concurrent_lazy_once():

    pool = MCPConnectionPool([_echo_spec()])
    lock = asyncio.Lock()
    state = {"started": False, "start_calls": 0}

    async def ensure():
        if state["started"]:
            return
        async with lock:
            if state["started"]:
                return
            state["start_calls"] += 1
            await pool.start_all()
            state["started"] = True

    await asyncio.gather(ensure(), ensure())
    try:
        assert state["start_calls"] == 1

        names = [t.name for t in pool.all_tools()]
        assert "mcp__echo__echo" in names and "mcp__echo__add" in names
    finally:
        await pool.close_all()
