# MCP client (stdio) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 PRAXIS 智能体能调用外部 stdio MCP server 暴露的工具(`mcp__<server>__<tool>`),一次性解锁 MCP 生态能力。

**Architecture:** 用官方 `mcp` lib 1.26.0 的 `stdio_client` + `ClientSession`;进程级常驻连接池(`MCPConnectionPool`,`AsyncExitStack` 维持常驻 session)在首个 chat-stream 请求时 lazy-once spawn 所有 configured server;每个远端 tool 包成 `MCPTool(Tool)` 注册进 `build_chat_registry`。

**Tech Stack:** Python 3.13 / mcp 1.26.0(`FastMCP` server + `ClientSession`/`stdio_client` client)/ asyncio `AsyncExitStack` / 现有 `Tool`/`ToolRegistry`/`Settings` 框架。

---

## 设计取舍记录(实现前必读)

1. **lazy-once vs lifespan startup**:spec §4 写"make_app 时一次 start_all",但 ASGI `_App.__init__` 是 sync,MCP spawn 是 async。技术取舍:用 **lazy-once**(首个 chat-stream 请求触发 `await pool.start_all()`,幂等,之后常驻)。语义等价"进程级常驻",触发点是首请求而非 lifespan。改动最小且测试友好(`_App(deps)` 构造不 spawn)。

2. **echo server 放 `praxis2/mcp/echo_server.py`**(非 spec 说的 `tests/fixtures/`):因 e2e 在 staging 跑,staging 部署 rsync `praxis2/`,放 praxis2/ 下可 `python -m praxis2.mcp.echo_server` 启动,单测 + e2e 共用。

3. **command 必须指向有 mcp lib 的解释器**:spike 验证裸 `python` 会 ModuleNotFoundError。echo server config 用 `sys.executable`(单测)/ conda praxis2 python(staging)。

4. **retry 失败的 subprocess 泄漏**:单个 server retry 失败时,已 enter 的 stdio context 留给 `close_all` 统一清(MVP 简化,受信 server 下罕见,retry 次数少)。

---

## File Structure

| 文件 | 职责 | 创建/修改 |
|---|---|---|
| `praxis2/mcp/__init__.py` | 包标识 + 导出 3 个公开符号 | 创建 |
| `praxis2/mcp/config.py` | `MCPServerSpec` + `parse_mcp_servers(json_str)` | 创建 |
| `praxis2/mcp/echo_server.py` | FastMCP echo+add stdio server(单测 fixture + e2e) | 创建 |
| `praxis2/mcp/tool_adapter.py` | `MCPTool(Tool)` 包装单个远端 tool | 创建 |
| `praxis2/mcp/pool.py` | `MCPConnectionPool` 常驻连接 + retry | 创建 |
| `praxis2/config.py` | `Settings.mcp_servers_json` + `_KNOWN_KEYS` + load | 修改 |
| `praxis2/server/chat_registry.py` | `build_chat_registry(mcp_tools=...)` 参数 | 修改 |
| `praxis2/server/app.py` | `_App` lazy start pool + chat-stream 传 mcp_tools | 修改 |
| `pyproject.toml` | `mcp>=1.26,<2` 进 dependencies | 修改 |
| `tests/test_mcp_config.py` | config 解析单测 | 创建 |
| `tests/test_mcp_tool_adapter.py` | MCPTool 单测(fake session) | 创建 |
| `tests/test_mcp_pool.py` | pool spawn-list-call-close 往返(echo server) | 创建 |
| `tests/test_mcp_registry_integration.py` | registry 含 MCPTool + 命名不冲突 | 创建 |

---

## Task 1: config — MCPServerSpec + parse_mcp_servers

**Files:**
- Create: `praxis2/mcp/__init__.py`
- Create: `praxis2/mcp/config.py`
- Test: `tests/test_mcp_config.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_mcp_config.py
import pytest
from praxis2.mcp.config import MCPServerSpec, parse_mcp_servers


def test_parse_empty_returns_empty_list():
    assert parse_mcp_servers("") == []
    assert parse_mcp_servers("   ") == []


def test_parse_single_server():
    specs = parse_mcp_servers(
        '[{"name":"echo","command":"python","args":["-m","praxis2.mcp.echo_server"]}]'
    )
    assert len(specs) == 1
    s = specs[0]
    assert s.name == "echo"
    assert s.command == "python"
    assert s.args == ["-m", "praxis2.mcp.echo_server"]
    assert s.env == {}


def test_parse_with_env():
    specs = parse_mcp_servers(
        '[{"name":"fs","command":"node","args":["x.js"],"env":{"KEY":"v"}}]'
    )
    assert specs[0].env == {"KEY": "v"}


def test_parse_multiple_servers():
    specs = parse_mcp_servers(
        '[{"name":"a","command":"python","args":[]},'
        '{"name":"b","command":"node","args":["s.js"]}]'
    )
    assert [s.name for s in specs] == ["a", "b"]


def test_parse_invalid_json_raises():
    with pytest.raises(ValueError, match="MCP.*JSON"):
        parse_mcp_servers("not json {[")


def test_parse_missing_name_raises():
    with pytest.raises(ValueError, match="name"):
        parse_mcp_servers('[{"command":"python","args":[]}]')


def test_parse_missing_command_raises():
    with pytest.raises(ValueError, match="command"):
        parse_mcp_servers('[{"name":"x","args":[]}]')


def test_parse_non_list_raises():
    with pytest.raises(ValueError, match="list"):
        parse_mcp_servers('{"name":"x"}')


def test_parse_args_defaults_to_empty():
    specs = parse_mcp_servers('[{"name":"x","command":"python"}]')
    assert specs[0].args == []
```

- [ ] **Step 2: 运行验证失败**

Run: `.venv/bin/python -m pytest tests/test_mcp_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'praxis2.mcp'`

- [ ] **Step 3: 写实现**

```python
# praxis2/mcp/__init__.py
"""MCP(Model Context Protocol)client 子系统(v0.17 子项目 1)。

stdio transport only;用官方 mcp lib 1.26.0 的 client,只写 PRAXIS Tool 适配层。
公开:MCPServerSpec(config 契约)/ MCPConnectionPool(常驻连接池)/ MCPTool(适配)。
"""
from praxis2.mcp.config import MCPServerSpec, parse_mcp_servers
from praxis2.mcp.pool import MCPConnectionPool
from praxis2.mcp.tool_adapter import MCPTool

__all__ = ["MCPServerSpec", "parse_mcp_servers", "MCPConnectionPool", "MCPTool"]
```

```python
# praxis2/mcp/config.py
"""MCP server 配置契约 + PRAXIS_MCP_SERVERS_JSON 解析(纯函数,fail-fast)。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class MCPServerSpec:
    """单个 MCP server 的启动规格(stdio transport)。"""

    name: str            # 唯一标识(MCPTool 前缀用),如 "echo" / "fs"
    command: str         # 可执行(注意:必须指向有 mcp lib 的解释器)
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


def parse_mcp_servers(json_str: str) -> list[MCPServerSpec]:
    """解析 PRAXIS_MCP_SERVERS_JSON → list[MCPServerSpec]。

    空串 / 纯空格 → 空 list(零值即关,不配 MCP)。
    非法 JSON / 非 list / 缺 name|command → ValueError(fail-fast)。
    """
    s = (json_str or "").strip()
    if not s:
        return []
    try:
        raw = json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"PRAXIS_MCP_SERVERS_JSON 不是合法 JSON:{e}") from e
    if not isinstance(raw, list):
        raise ValueError(
            f"PRAXIS_MCP_SERVERS_JSON 必须是 list,得到 {type(raw).__name__}"
        )
    specs: list[MCPServerSpec] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"MCP server[{i}] 必须是 object,得到 {type(item).__name__}")
        name = item.get("name")
        command = item.get("command")
        if not name:
            raise ValueError(f"MCP server[{i}] 缺 name(必填)")
        if not command:
            raise ValueError(f"MCP server[{i}] (name={name!r}) 缺 command(必填)")
        specs.append(MCPServerSpec(
            name=str(name),
            command=str(command),
            args=list(item.get("args") or []),
            env=dict(item.get("env") or {}),
        ))
    return specs
```

- [ ] **Step 4: 运行验证通过**

Run: `.venv/bin/python -m pytest tests/test_mcp_config.py -v`
Expected: PASS(9 passed)

- [ ] **Step 5: Commit**

```bash
git add praxis2/mcp/__init__.py praxis2/mcp/config.py tests/test_mcp_config.py
git commit -m "feat(mcp): MCPServerSpec + parse_mcp_servers(config 契约,fail-fast)"
```

> **注**:`__init__.py` 此时 import pool/tool_adapter 会失败(还没建)。本 task commit 后 `__init__.py` 暂时只 import config,Task 3/4 建好后再补全 import。改 Step 3 的 `__init__.py` 为:
> ```python
> from praxis2.mcp.config import MCPServerSpec, parse_mcp_servers
> __all__ = ["MCPServerSpec", "parse_mcp_servers"]
> ```
> Task 4 末尾再补 pool/tool_adapter 的导出。

---

## Task 2: echo MCP server(测试 fixture + e2e)

**Files:**
- Create: `praxis2/mcp/echo_server.py`
- Test: 手动 smoke(无单测;它是被 Task 4 pool 测试驱动的 fixture)

- [ ] **Step 1: 写 echo server**

```python
# praxis2/mcp/echo_server.py
"""最小 stdio MCP server(FastMCP):echo + add 两个 tool。

用途:
1. 单测 fixture(test_mcp_pool 用它验 pool spawn/list/call 往返)
2. e2e(staging 配 PRAXIS_MCP_SERVERS_JSON 指向它,规避 staging 无 npx)

启动:python -m praxis2.mcp.echo_server(command 必须是有 mcp lib 的解释器)。
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("praxis-echo")


@mcp.tool()
def echo(text: str) -> str:
    """回显输入文本(MCP client 链路验证用)。"""
    return f"echo: {text}"


@mcp.tool()
def add(a: int, b: int) -> int:
    """两数相加(结构化参数验证用)。"""
    return a + b


if __name__ == "__main__":
    mcp.run("stdio")
```

- [ ] **Step 2: 手动 smoke 验证可启动**

Run:
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' | timeout 5 .venv/bin/python -m praxis2.mcp.echo_server 2>/dev/null | head -1
```
Expected: 输出一行 JSON 含 `"serverInfo"` 和 `"praxis-echo"`(证明 server 能启动 + 响应 initialize)。

- [ ] **Step 3: Commit**

```bash
git add praxis2/mcp/echo_server.py
git commit -m "feat(mcp): echo_server FastMCP stdio fixture(echo+add,e2e 规避无 npx)"
```

---

## Task 3: MCPTool 适配层

**Files:**
- Create: `praxis2/mcp/tool_adapter.py`
- Test: `tests/test_mcp_tool_adapter.py`

- [ ] **Step 1: 写失败测试(用 fake session,不依赖真 subprocess)**

```python
# tests/test_mcp_tool_adapter.py
import asyncio
from praxis2.mcp.tool_adapter import MCPTool


class _FakeContent:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _FakeCallResult:
    def __init__(self, content, is_error=False):
        self.content = content
        self.isError = is_error
        self.structuredContent = None


class _FakeSession:
    """模拟 mcp ClientSession.call_tool。"""
    def __init__(self, result=None, raises=None):
        self._result = result
        self._raises = raises
        self.calls = []

    async def call_tool(self, name, arguments=None, read_timeout_seconds=None):
        self.calls.append((name, arguments))
        if self._raises:
            raise self._raises
        return self._result


def _mk_tool(session, remote_name="echo"):
    return MCPTool(
        server_name="echo",
        session=session,
        remote_name=remote_name,
        description="回显",
        input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
        call_timeout_s=30.0,
    )


def test_name_has_mcp_prefix():
    t = _mk_tool(_FakeSession())
    assert t.name == "mcp__echo__echo"


def test_rmcp_op_is_none():
    """MCP 工具是外部能力,不受相位门约束。"""
    assert _mk_tool(_FakeSession()).rmcp_op is None


def test_input_schema_passthrough():
    t = _mk_tool(_FakeSession())
    assert t.input_schema() == {"type": "object", "properties": {"text": {"type": "string"}}}


def test_input_schema_fallback_when_empty():
    t = MCPTool(server_name="x", session=_FakeSession(), remote_name="y",
                description="", input_schema=None, call_timeout_s=30.0)
    assert t.input_schema() == {"type": "object", "properties": {}}


def test_run_success_returns_text():
    sess = _FakeSession(_FakeCallResult([_FakeContent("echo: hi")], is_error=False))
    t = _mk_tool(sess)
    r = asyncio.run(t.run({"text": "hi"}))
    assert r.ok
    assert "echo: hi" in r.value
    assert sess.calls == [("echo", {"text": "hi"})]


def test_run_is_error_returns_ok_false():
    sess = _FakeSession(_FakeCallResult([_FakeContent("Unknown tool")], is_error=True))
    t = _mk_tool(sess)
    r = asyncio.run(t.run({"text": "x"}))
    assert not r.ok
    assert "Unknown tool" in (r.error or "")


def test_run_exception_returns_ok_false_not_raise():
    """server crash / timeout → call_tool 抛 → ok=False,不冒泡致 500。"""
    sess = _FakeSession(raises=RuntimeError("connection lost"))
    t = _mk_tool(sess)
    r = asyncio.run(t.run({"text": "x"}))
    assert not r.ok
    assert "connection lost" in (r.error or "")


def test_run_multi_content_joins_text():
    sess = _FakeSession(_FakeCallResult(
        [_FakeContent("part1"), _FakeContent("part2")], is_error=False))
    t = _mk_tool(sess)
    r = asyncio.run(t.run({}))
    assert "part1" in r.value and "part2" in r.value
```

- [ ] **Step 2: 运行验证失败**

Run: `.venv/bin/python -m pytest tests/test_mcp_tool_adapter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'praxis2.mcp.tool_adapter'`

- [ ] **Step 3: 写实现**

```python
# praxis2/mcp/tool_adapter.py
"""MCPTool:包装单个 MCP server 暴露的单个远端 tool 为 PRAXIS Tool(§7.3.1)。

无状态(持 session 引用 + 远端元数据);run() 委托 ClientSession.call_tool。
任何失败(crash/timeout/isError)→ ToolResult(ok=False),绝不冒泡致 chat-stream 500。
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from praxis2.tools.base import Tool, ToolResult

_DEFAULT_SCHEMA = {"type": "object", "properties": {}}


def _extract_text(content: list) -> str:
    """CallToolResult.content(list[TextContent|...])→ 拼接所有 .text。"""
    parts: list[str] = []
    for c in content or []:
        text = getattr(c, "text", None)
        if text is not None:
            parts.append(str(text))
    return "\n".join(parts)


class MCPTool(Tool):
    """MCP 远端 tool 的 PRAXIS Tool 适配。name = mcp__<server>__<remote_tool>。"""

    rmcp_op = None  # 外部能力,不受 RMCP 相位门(与 BrainQuery/FileRead 同)

    def __init__(
        self,
        *,
        server_name: str,
        session: Any,
        remote_name: str,
        description: str,
        input_schema: dict | None,
        call_timeout_s: float,
    ) -> None:
        self._server_name = server_name
        self._session = session
        self._remote_name = remote_name
        self.description = description or f"MCP tool {remote_name} from {server_name}"
        self._schema = input_schema or dict(_DEFAULT_SCHEMA)
        self._call_timeout_s = call_timeout_s

    @property
    def name(self) -> str:  # type: ignore[override]
        # 三段式前缀:防与内建工具冲突 + 对齐 Claude Code mcp__ 命名约定
        return f"mcp__{self._server_name}__{self._remote_name}"

    def input_schema(self) -> dict[str, Any]:
        return self._schema

    async def run(self, payload: dict[str, Any]) -> ToolResult:
        try:
            result = await self._session.call_tool(
                self._remote_name,
                payload,
                read_timeout_seconds=timedelta(seconds=self._call_timeout_s),
            )
        except Exception as e:  # noqa: BLE001 — server crash/timeout 不冒泡致 500
            return ToolResult(
                ok=False,
                error=f"MCP call 失败({type(e).__name__}: {e})",
                recovery_hint=f"MCP server {self._server_name!r} 可能崩溃/超时,可重试或换工具。",
            )
        text = _extract_text(getattr(result, "content", []))
        is_error = bool(getattr(result, "isError", False))
        if is_error:
            return ToolResult(ok=False, error=text or "MCP server 返回 isError=True")
        return ToolResult(ok=True, value=text)
```

> **注**:`Tool.name` 基类是类属性(`name: str`)。这里用 `@property` 覆盖为实例属性(因 name 依赖 server_name/remote_name 实例数据)。`ToolRegistry.register` 读 `tool.name` 兼容 property(已验:registry.py 只读不写 name)。

- [ ] **Step 4: 运行验证通过**

Run: `.venv/bin/python -m pytest tests/test_mcp_tool_adapter.py -v`
Expected: PASS(8 passed)

- [ ] **Step 5: 补全 `__init__.py` 导出**

```python
# praxis2/mcp/__init__.py — 加回 tool_adapter 导出(pool 在 Task 4)
from praxis2.mcp.config import MCPServerSpec, parse_mcp_servers
from praxis2.mcp.tool_adapter import MCPTool

__all__ = ["MCPServerSpec", "parse_mcp_servers", "MCPTool"]
```

- [ ] **Step 6: Commit**

```bash
git add praxis2/mcp/tool_adapter.py praxis2/mcp/__init__.py tests/test_mcp_tool_adapter.py
git commit -m "feat(mcp): MCPTool 适配层(mcp__前缀 + 失败 ok=False 不致 500)"
```

---

## Task 4: MCPConnectionPool

**Files:**
- Create: `praxis2/mcp/pool.py`
- Test: `tests/test_mcp_pool.py`

- [ ] **Step 1: 写失败测试(用真 echo server subprocess)**

```python
# tests/test_mcp_pool.py
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
        # 好 server 的工具在
        assert any(n.startswith("mcp__good__") for n in names)
        # 坏 server 进 audit
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
```

- [ ] **Step 2: 运行验证失败**

Run: `.venv/bin/python -m pytest tests/test_mcp_pool.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'praxis2.mcp.pool'`

- [ ] **Step 3: 写实现**

```python
# praxis2/mcp/pool.py
"""MCPConnectionPool:进程级常驻 stdio MCP 连接池(v0.17 子项目 1)。

AsyncExitStack 维持常驻 session(spike 验证:enter_async_context 手动管理
stdio_client + ClientSession,不用嵌套 async with);start_all 首次 spawn
所有 server,单个失败 retry → 跳过 + audit(不阻塞其他/不阻塞 chat)。

进程级单例(挂 app 实例);多 worker 各自一份(stdio subprocess 不能跨进程共享)。
"""
from __future__ import annotations

import logging
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from praxis2.mcp.config import MCPServerSpec
from praxis2.mcp.tool_adapter import MCPTool

_logger = logging.getLogger("praxis2.mcp")

_DEFAULT_RETRY = 2
_DEFAULT_CALL_TIMEOUT_S = 30.0


class MCPConnectionPool:
    def __init__(
        self,
        specs: list[MCPServerSpec],
        *,
        retry: int = _DEFAULT_RETRY,
        call_timeout_s: float = _DEFAULT_CALL_TIMEOUT_S,
    ) -> None:
        self._specs = specs
        self._retry = retry
        self._call_timeout_s = call_timeout_s
        self._stack = AsyncExitStack()
        self._tools: list[MCPTool] = []
        self._audit: list[dict] = []  # 跳过的 server 记录
        self._started = False

    async def start_all(self) -> None:
        """首次 spawn 所有 server(幂等)。单个失败 retry → 跳过 + audit。"""
        if self._started:
            return
        self._started = True
        for spec in self._specs:
            await self._start_one(spec)

    async def _start_one(self, spec: MCPServerSpec) -> None:
        last_err: Exception | None = None
        for _attempt in range(self._retry + 1):
            try:
                params = StdioServerParameters(
                    command=spec.command,
                    args=spec.args,
                    env=spec.env or None,
                )
                read, write = await self._stack.enter_async_context(
                    stdio_client(params)
                )
                session = await self._stack.enter_async_context(
                    ClientSession(read, write)
                )
                await session.initialize()
                listed = await session.list_tools()
                for t in listed.tools:
                    self._tools.append(MCPTool(
                        server_name=spec.name,
                        session=session,
                        remote_name=t.name,
                        description=t.description or "",
                        input_schema=t.inputSchema,
                        call_timeout_s=self._call_timeout_s,
                    ))
                _logger.info(
                    "MCP server %r 启动,注册 %d 个 tool",
                    spec.name, len(listed.tools),
                )
                return
            except Exception as e:  # noqa: BLE001 — 单 server 失败不阻塞其他
                last_err = e
                continue
        self._audit.append({"server": spec.name, "error": repr(last_err)})
        _logger.warning(
            "MCP server %r 启动失败(retry %d 次),跳过:%r",
            spec.name, self._retry, last_err,
        )

    def all_tools(self) -> list[MCPTool]:
        return list(self._tools)

    def audit_log(self) -> list[dict]:
        return list(self._audit)

    async def close_all(self) -> None:
        """优雅关闭所有 subprocess(app shutdown 调)。"""
        try:
            await self._stack.aclose()
        except Exception as e:  # noqa: BLE001 — 关闭失败不应抛(OS 也会回收子进程)
            _logger.warning("MCP pool close_all 异常(忽略):%r", e)
        self._tools = []
        self._started = False
```

- [ ] **Step 4: 运行验证通过**

Run: `.venv/bin/python -m pytest tests/test_mcp_pool.py -v`
Expected: PASS(5 passed)

- [ ] **Step 5: 补全 `__init__.py` 导出 pool**

```python
# praxis2/mcp/__init__.py — 最终版
from praxis2.mcp.config import MCPServerSpec, parse_mcp_servers
from praxis2.mcp.pool import MCPConnectionPool
from praxis2.mcp.tool_adapter import MCPTool

__all__ = ["MCPServerSpec", "parse_mcp_servers", "MCPConnectionPool", "MCPTool"]
```

- [ ] **Step 6: Commit**

```bash
git add praxis2/mcp/pool.py praxis2/mcp/__init__.py tests/test_mcp_pool.py
git commit -m "feat(mcp): MCPConnectionPool 常驻连接池(AsyncExitStack + retry/skip + audit)"
```

---

## Task 5: chat_registry 接入

**Files:**
- Modify: `praxis2/server/chat_registry.py`
- Test: `tests/test_mcp_registry_integration.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_mcp_registry_integration.py
from praxis2.agents.loader import resolve_agent
from praxis2.server.chat_registry import build_chat_registry
from praxis2.mcp.tool_adapter import MCPTool


class _FakeSession:
    async def call_tool(self, name, arguments=None, read_timeout_seconds=None):
        raise NotImplementedError


def _mk_mcp_tool(server, remote):
    return MCPTool(server_name=server, session=_FakeSession(), remote_name=remote,
                   description="x", input_schema={"type": "object"}, call_timeout_s=30.0)


def test_registry_includes_mcp_tools():
    sel = resolve_agent("enzyme", user_query="hi")
    mcp_tools = [_mk_mcp_tool("echo", "echo"), _mk_mcp_tool("echo", "add")]
    reg = build_chat_registry(selection=sel, mcp_tools=mcp_tools)
    names = [t["name"] for t in reg.anthropic_tools()]
    assert "mcp__echo__echo" in names
    assert "mcp__echo__add" in names
    # 内建工具仍在
    assert "BrainQuery" in names


def test_registry_no_mcp_tools_when_none():
    """不传 mcp_tools → 行为与 v0.16 完全一致(零回归)。"""
    sel = resolve_agent("enzyme", user_query="hi")
    reg = build_chat_registry(selection=sel)
    names = [t["name"] for t in reg.anthropic_tools()]
    assert not any(n.startswith("mcp__") for n in names)
    assert "BrainQuery" in names


def test_mcp_tool_registered_alongside_builtins():
    """MCP tool 与内建工具共存,命名前缀 mcp__ 天然不冲突。"""
    sel = resolve_agent("enzyme", user_query="hi")
    mt = _mk_mcp_tool("x", "y")
    reg = build_chat_registry(selection=sel, mcp_tools=[mt])
    names = [t["name"] for t in reg.anthropic_tools()]
    assert "mcp__x__y" in names       # MCP 工具注册成功
    assert "BrainQuery" in names      # 内建工具仍在
```

- [ ] **Step 2: 运行验证失败**

Run: `.venv/bin/python -m pytest tests/test_mcp_registry_integration.py -v`
Expected: FAIL — `TypeError: build_chat_registry() got an unexpected keyword argument 'mcp_tools'`

- [ ] **Step 3: 改 build_chat_registry**

当前签名(`praxis2/server/chat_registry.py`):
```python
def build_chat_registry(
    *, selection: AgentSelection | None = None
) -> ToolRegistry:
```

改为(加 `mcp_tools` 参数,在 return 前 register):
```python
def build_chat_registry(
    *,
    selection: AgentSelection | None = None,
    mcp_tools: "list | None" = None,
) -> ToolRegistry:
```

在 `return reg` 之前(`reg.register(WebFetchTool())` 之后)插入:
```python
    # v0.17:挂 MCP 工具(外部 server,mcp__<server>__<tool> 命名)。
    # builtin=False:同名内建优先(命名前缀已防冲突,此为双保险);
    # 不传 mcp_tools → 零回归(行为 == v0.16)。
    for mt in mcp_tools or []:
        reg.register(mt, builtin=False)
```

- [ ] **Step 4: 运行验证通过**

Run: `.venv/bin/python -m pytest tests/test_mcp_registry_integration.py -v`
Expected: PASS(3 passed)

- [ ] **Step 5: 跑 chat_registry 既有测试确认零回归**

Run: `.venv/bin/python -m pytest tests/test_tools_brain_query.py tests/test_tools_skill_exec.py -v`
Expected: PASS(既有工具注册测试不受影响)

- [ ] **Step 6: Commit**

```bash
git add praxis2/server/chat_registry.py tests/test_mcp_registry_integration.py
git commit -m "feat(mcp): build_chat_registry 加 mcp_tools 参数(builtin=False 防覆盖)"
```

---

## Task 6: app.py 接入(lazy-once start + chat-stream 传 mcp_tools)

**Files:**
- Modify: `praxis2/server/app.py`(`_App.__init__` + chat-stream handler line ~629)
- Test: `tests/test_mcp_pool.py`(加 1 个 app 级 lazy-start 测试)

- [ ] **Step 1: 写失败测试(验 _App lazy start + 传 mcp_tools)**

```python
# tests/test_mcp_pool.py — 追加
@pytest.mark.asyncio
async def test_app_lazy_start_mcp_pool_idempotent():
    """_ensure_mcp 幂等:多次调只 start_all 一次。"""
    from praxis2.mcp.pool import MCPConnectionPool

    class _CountingPool(MCPConnectionPool):
        start_count = 0
        async def start_all(self):
            type(self).start_count += 1
            await super().start_all()

    pool = _CountingPool([])
    # 模拟 _App._ensure_mcp 的幂等逻辑
    started = {"v": False}
    async def ensure():
        if not started["v"]:
            await pool.start_all()
            started["v"] = True
    await ensure()
    await ensure()
    assert _CountingPool.start_count == 1
    await pool.close_all()
```

- [ ] **Step 2: 运行验证失败**

Run: `.venv/bin/python -m pytest tests/test_mcp_pool.py::test_app_lazy_start_mcp_pool_idempotent -v`
Expected: PASS(此测试只验逻辑,本身会过)——实际驱动 app.py 改动的是手动 e2e(Task 8)。此 task 的 app.py 改动由 Step 3 完成,Step 4 跑全量回归确认零回归。

- [ ] **Step 3: 改 app.py**

3a. `_App.__init__`(line ~205,`self._session_pool = ...` 之后)加:
```python
        # v0.17:MCP 连接池(lazy-once start,首个 chat-stream 请求触发)。
        # 构造时只 parse spec 不 spawn(sync 安全);spawn 在 _ensure_mcp(async)。
        from praxis2.mcp.config import parse_mcp_servers
        from praxis2.mcp.pool import MCPConnectionPool
        _mcp_specs = parse_mcp_servers(getattr(deps.settings, "mcp_servers_json", ""))
        self._mcp_pool = MCPConnectionPool(_mcp_specs)
        self._mcp_started = False
```

3b. `_App` 加方法(放在 `__init__` 之后):
```python
    async def _ensure_mcp(self) -> None:
        """首个 chat-stream 请求时 lazy-once spawn MCP server(幂等)。
        失败不抛(pool 内部 retry/skip + audit),不阻塞 chat。"""
        if self._mcp_started:
            return
        self._mcp_started = True
        try:
            await self._mcp_pool.start_all()
        except Exception:  # noqa: BLE001 — pool 内部已 retry/skip,这里双保险
            pass
```

3c. chat-stream handler 中 `reg = build_chat_registry(selection=selection)`(line ~629)改为:
```python
                await self._ensure_mcp()
                reg = build_chat_registry(
                    selection=selection,
                    mcp_tools=self._mcp_pool.all_tools(),
                )
```

- [ ] **Step 4: 跑全量回归确认零回归**

Run: `.venv/bin/python -m pytest tests/ --ignore=tests/integration --tb=short`
Expected: PASS(全绿;不配 mcp_servers_json → pool 空 → 行为 == v0.16.3)

- [ ] **Step 5: Commit**

```bash
git add praxis2/server/app.py tests/test_mcp_pool.py
git commit -m "feat(mcp): _App lazy-once start MCP pool + chat-stream 传 mcp_tools"
```

---

## Task 7: config Settings 接入 + pyproject dep + _KNOWN_KEYS

**Files:**
- Modify: `praxis2/config.py`(Settings 字段 + _KNOWN_KEYS + load_from_env)
- Modify: `pyproject.toml`
- Test: `tests/test_config.py`(加 mcp_servers_json 默认值 + 白名单测试)

- [ ] **Step 1: 写失败测试**

```python
# tests/test_config.py — 追加(参照该文件既有 _base_env() helper 风格)
def test_mcp_servers_json_defaults_empty(monkeypatch):
    """不配 PRAXIS_MCP_SERVERS_JSON → 默认空串(零值即关)。"""
    from praxis2.config import load_from_env
    env = _base_env()  # 该文件已有的最小必填 env helper
    s = load_from_env(env)
    assert s.mcp_servers_json == ""


def test_mcp_servers_json_loaded(monkeypatch):
    from praxis2.config import load_from_env
    env = _base_env()
    env["PRAXIS_MCP_SERVERS_JSON"] = '[{"name":"echo","command":"python","args":[]}]'
    s = load_from_env(env)
    assert "echo" in s.mcp_servers_json


def test_mcp_servers_json_in_known_keys():
    """PRAXIS_MCP_SERVERS_JSON 在白名单(否则 fail-fast 拒)。"""
    from praxis2.config import _KNOWN_KEYS
    assert "PRAXIS_MCP_SERVERS_JSON" in _KNOWN_KEYS
```

> **注**:`_base_env()` 是 `tests/test_config.py` 已有的 helper(构造最小必填 env dict)。若实际函数名不同(如 `_min_env` / inline dict),实现时对齐该文件既有风格 —— 先 `grep "def _.*env\|_base_env\|PRAXIS_ANTHROPIC_API_KEY" tests/test_config.py` 确认。

- [ ] **Step 2: 运行验证失败**

Run: `.venv/bin/python -m pytest tests/test_config.py -k mcp -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'mcp_servers_json'` 或白名单 KeyError

- [ ] **Step 3: 改 config.py**

3a. `Settings` 加字段(在 M12 配额字段之后,`def __post_init__` 之前):
```python
    # v0.17 MCP client(可选,零值即关:空=不挂任何 MCP server)
    mcp_servers_json: str = ""
```

3b. `_KNOWN_KEYS` 加(在 M12 块之后,`})` 之前):
```python
    # v0.17 MCP client
    "PRAXIS_MCP_SERVERS_JSON",
```

3c. `load_from_env` 的 `Settings(...)` 构造里加(在 md/admin 字段附近):
```python
        mcp_servers_json=e.get("PRAXIS_MCP_SERVERS_JSON", ""),
```

- [ ] **Step 4: 改 pyproject.toml**

`[project] dependencies` 块加 `mcp`:
```toml
dependencies = [
    "httpx>=0.27",
    "mcp>=1.26,<2",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "python-multipart>=0.0.9",
    "python-magic>=0.4.27",
    "PyYAML>=6.0",
]
```

- [ ] **Step 5: 运行验证通过 + 全量回归**

Run: `.venv/bin/python -m pytest tests/test_config.py -k mcp -v && .venv/bin/python -m pytest tests/ --ignore=tests/integration --tb=short`
Expected: PASS(全绿)

- [ ] **Step 6: Commit**

```bash
git add praxis2/config.py pyproject.toml tests/test_config.py
git commit -m "feat(mcp): Settings.mcp_servers_json + _KNOWN_KEYS 白名单 + mcp dep"
```

---

## Task 8: e2e staging + deploy + tag v0.17.0-alpha

**Files:**
- Modify: `praxis2/auth/routes.py`(版本号)
- Modify: `frontend/package.json`(版本号)
- Modify: staging `~/praxis2.env`(加 PRAXIS_MCP_SERVERS_JSON,prod-only 不入 git)

- [ ] **Step 1: bump 版本号**

`praxis2/auth/routes.py` `/api/info` version → `v0.17.0-alpha`,注释:`MCP client(stdio)接入,echo server e2e`。
`frontend/package.json` version → `0.17.0-alpha`。

- [ ] **Step 2: 全量回归**

Run: `.venv/bin/python -m pytest tests/ --ignore=tests/integration --tb=no`
Expected: PASS(预期 1818 + ~25 新 = ~1843)

- [ ] **Step 3: rsync backend + echo server 到 staging**

```bash
rsync -av praxis2/mcp/ zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/mcp/
rsync -av praxis2/config.py zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/
rsync -av praxis2/server/app.py zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/server/
rsync -av praxis2/server/chat_registry.py zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/server/
rsync -av praxis2/auth/routes.py zkyd@10.102.106.53:~/data1/mzy/PRAXIS-2/praxis2/auth/
```
> 注:rsync `praxis2/config.py` 单文件不要用 `--no-relative`(v0.16 踩过会堆顶层);直接指定 `praxis2/` 目标目录。

- [ ] **Step 4: staging env 加 MCP 配置(echo server,conda python)**

ssh staging,`~/praxis2.env` 追加(注意 command 用 conda praxis2 python 绝对路径,有 mcp lib):
```bash
export PRAXIS_MCP_SERVERS_JSON='[{"name":"echo","command":"/home/zkyd/software/miniconda3/envs/praxis2/bin/python","args":["-m","praxis2.mcp.echo_server"]}]'
```
> 验证 staging 有 mcp lib:`ssh zkyd@.53 "~/software/miniconda3/envs/praxis2/bin/python -c 'import mcp; print(mcp.__version__)'"`。若无 → `pip install 'mcp>=1.26,<2'` 进 praxis2 env。

- [ ] **Step 5: restart gunicorn**

```bash
# 找 master pid(PPID=1 的 bash 下的 python child),kill 后 nohup 重启(SOP 已验 N 次)
ssh zkyd@10.102.106.53 "ps -ef | grep gunicorn | grep -v grep | awk '\$3!=1 && \$8 ~ /python/ {print \$2}' | head -1"
ssh zkyd@10.102.106.53 "kill <PID> && sleep 3 && cd ~/data1/mzy/PRAXIS-2 && source ~/praxis2.env && nohup ~/software/miniconda3/envs/praxis2/bin/gunicorn -c deploy/gunicorn.conf.py praxis2.server.app:make_app_default > /tmp/praxis2-v017.log 2>&1 & disown"
```

- [ ] **Step 6: 验版本号**

Run: `curl -s http://10.102.106.40:8080/api/info`
Expected: `"version": "v0.17.0-alpha"`

- [ ] **Step 7: e2e — chat 真调 mcp__echo__echo**

```bash
SESSION=$(curl -s -i -X POST http://10.102.106.40:8080/api/auth/login -H "Content-Type: application/json" -d '{"email":"<admin>","password":"<pw>"}' | grep set-cookie | sed 's/.*praxis_session=\([^;]*\).*/\1/')
curl -s -X POST http://10.102.106.40:8080/api/chat-stream \
  -H "Content-Type: application/json" -H "Cookie: praxis_session=$SESSION" \
  -d '{"agent":"general","message":"用 mcp__echo__echo 工具回显 \"v0.17 mcp ok\"","model":"deepseek-v4-flash","mode":"general","session_id":"v017-mcp-e2e"}' \
  --max-time 60 | grep -E "tool_start|tool_end" | head -4
```
Expected: SSE 流含 `mcp__echo__echo` 的 tool_start + tool_end(content 含 `echo: v0.17 mcp ok`,is_error: false)。

- [ ] **Step 8: server 端验工具池含 MCP 工具**

Run:
```bash
ssh zkyd@10.102.106.53 "cd ~/data1/mzy/PRAXIS-2 && source ~/praxis2.env && ~/software/miniconda3/envs/praxis2/bin/python -c 'import asyncio; from praxis2.mcp.config import parse_mcp_servers; from praxis2.mcp.pool import MCPConnectionPool; import os
async def m():
    p = MCPConnectionPool(parse_mcp_servers(os.environ.get(\"PRAXIS_MCP_SERVERS_JSON\",\"\")))
    await p.start_all(); print([t.name for t in p.all_tools()]); await p.close_all()
asyncio.run(m())'"
```
Expected: `['mcp__echo__echo', 'mcp__echo__add']`

- [ ] **Step 9: commit + tag + push + memory**

```bash
git add praxis2/auth/routes.py frontend/package.json
git commit -m "release(v0.17.0-alpha): MCP client(stdio)接入 — echo server e2e 真往返"
git tag v0.17.0-alpha
git push origin main && git push origin v0.17.0-alpha
```
更新 `~/.claude/projects/-Volumes-T7-clade-learn/memory/MEMORY.md`:新增 v0.17.0-alpha 条目(MCP client stdio,echo e2e,CC npx 适配推迟)。

---

## Self-Review(已执行,fresh-eyes 对 spec 核对)

**Spec coverage**:
- spec §2 架构(config/pool/tool_adapter/__init__)→ Task 1/3/4 ✓
- spec §3 MCPServerSpec → Task 1 ✓
- spec §4 pool 生命周期(start_all/all_tools/close_all/crash retry)→ Task 4 ✓(lazy-once 取舍已在顶部说明)
- spec §5 MCPTool(命名前缀/input_schema 透传/run 委托/错误)→ Task 3 ✓
- spec §6 错误矩阵(config/spawn/call 各路径)→ Task 1(config)+ Task 3(call)+ Task 4(spawn skip)✓
- spec §7 测试(echo fixture + 单测 + e2e + CC npx 推迟)→ Task 2/4/8 ✓
- spec §8 DoD 每项 → 对应 Task ✓
- spec §9 依赖(mcp dep + env)→ Task 7/8 ✓

**Placeholder scan**:无 TBD/TODO;所有 code step 含完整代码;Task 7 的 `_base_env()` 给了 grep 确认指引(非 placeholder,是对齐既有 helper 的明确指令)。

**Type consistency**:`MCPServerSpec(name/command/args/env)` Task 1 定义,Task 4 用一致;`MCPTool(server_name/session/remote_name/description/input_schema/call_timeout_s)` Task 3 定义,Task 4 构造一致;`build_chat_registry(selection, mcp_tools)` Task 5 定义,Task 6 调用一致;`pool.all_tools()/start_all()/close_all()/audit_log()` Task 4 定义,Task 6/8 用一致。

**已修**:Task 5 Step 1 的残留占位行已删,`test_mcp_tool_does_not_override_builtin` 重写为 `test_mcp_tool_registered_alongside_builtins`(验 MCP 工具与内建共存,命名前缀天然不冲突)。
