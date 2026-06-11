import asyncio
import sys
import pytest
from praxis2.mcp.config import MCPServerSpec
from praxis2.mcp.pool import MCPConnectionPool


def _echo_spec(name="echo"):
    # 关键:command 用 sys.executable(有 mcp lib),不是裸 "python"
    return MCPServerSpec(
        name=name, command=sys.executable,
        args=["-m", "praxis2.mcp.echo_server"], env={},
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
    await pool.start_all()  # 再调不重复 spawn
    try:
        assert len(pool.all_tools()) == n1
    finally:
        await pool.close_all()


@pytest.mark.asyncio
async def test_pool_bad_server_skipped_not_crash():
    """坏 server(命令不存在)retry 失败 → 跳过 + audit,不阻塞好 server。"""
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
    """server spawn 成功但不讲 MCP 协议(sleep)→ 握手超时跳过 + audit,
    不阻塞 good server(验 #1:initialize/list_tools 超时保护)。"""
    # 这个 server 启动后只 sleep,不响应 MCP initialize → 握手会挂
    slow = MCPServerSpec(
        name="slow", command=sys.executable,
        args=["-c", "import time; time.sleep(60)"], env={},
    )
    pool = MCPConnectionPool(
        [slow, _echo_spec(name="good")],
        retry=0, startup_timeout_s=1.0,  # 短超时,测试快
    )
    await pool.start_all()
    try:
        names = [t.name for t in pool.all_tools()]
        # good server 的工具在(slow 没拖垮它)
        assert any(n.startswith("mcp__good__") for n in names)
        # slow 进 audit
        assert any(a["server"] == "slow" for a in pool.audit_log())
    finally:
        await pool.close_all()


@pytest.mark.asyncio
async def test_pool_cross_task_call_tool_works():
    """架构基石验证:start_all 一次后,不同 task 调 call_tool 复用常驻 session
    安全(call_tool 不退 cancel scope)—— lazy-once + 多请求复用的前提。"""
    pool = MCPConnectionPool([_echo_spec()])
    await asyncio.create_task(pool.start_all())  # task A spawn
    try:
        async def _call():
            tool = next(t for t in pool.all_tools() if t.name == "mcp__echo__echo")
            return await tool.run({"text": "xtask"})
        r = await asyncio.create_task(_call())  # task B(不同 task)调用
        assert r.ok
        assert "echo: xtask" in r.value
    finally:
        await pool.close_all()


@pytest.mark.asyncio
async def test_pool_cross_task_close_does_not_raise():
    """close_all 跨 task 触发 anyio cancel-scope RuntimeError,但被吞,不冒泡
    (降级 OS 兜底)。锁定这个已知边界:shutdown 跨 task 不崩 chat。"""
    pool = MCPConnectionPool([_echo_spec()])
    await asyncio.create_task(pool.start_all())  # task A
    async def _close():
        await pool.close_all()
    # close 在不同 task —— 不应抛(内部吞 cancel-scope RuntimeError)
    await asyncio.create_task(_close())  # 不抛即通过
    assert pool.all_tools() == []  # 复位


@pytest.mark.asyncio
async def test_lazy_once_start_idempotent():
    """模拟 _App._ensure_mcp 的 lazy-once 守卫:多次调只 start_all 一次。"""
    spec = _echo_spec()
    pool = MCPConnectionPool([spec])
    started = {"v": False}

    async def ensure():
        if started["v"]:
            return
        started["v"] = True
        await pool.start_all()

    await ensure()
    await ensure()  # 第二次不再 start
    try:
        # start_all 自身也幂等;工具只注册一次
        assert len([t for t in pool.all_tools() if t.name.startswith("mcp__echo__")]) == 2
    finally:
        await pool.close_all()


@pytest.mark.asyncio
async def test_ensure_mcp_concurrent_lazy_once():
    """I-2 回归:模拟 _App._ensure_mcp 的并发 lazy-once —— 两个并发首请求,
    start_all 只跑一次,且两个调用返回后工具都已就绪(B 等到 A spawn 完成,
    不会拿到空列表)。"""
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

    # 两个并发"首请求"
    await asyncio.gather(ensure(), ensure())
    try:
        # start 逻辑只进一次(第二个在锁后 double-check 命中 return)
        assert state["start_calls"] == 1
        # 两个调用返回后工具都就绪(echo 的 2 个 tool 在)
        names = [t.name for t in pool.all_tools()]
        assert "mcp__echo__echo" in names and "mcp__echo__add" in names
    finally:
        await pool.close_all()
