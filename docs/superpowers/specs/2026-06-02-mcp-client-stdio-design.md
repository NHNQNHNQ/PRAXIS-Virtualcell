# v0.17 子项目 1:MCP client(stdio)设计

**日期**: 2026-06-02 · **状态**: 设计已批准,待 plan
**范围**: v0.17 拆分后的第一个子项目(第二个 = BashTool,独立 spec)
**前置**: v0.16.3 已 ship,14d 观察期到 2026-06-16(本子项目是加法,不破主链)

---

## 0. 目标与非目标

### 目标
让 PRAXIS 智能体能调用外部 MCP(Model Context Protocol)server 暴露的工具,
一次性解锁 MCP 生态的现成能力(filesystem / git / sqlite / sequential-thinking 等)。

### 非目标(本子项目明确不做)
- **HTTP/SSE transport** — 只做 stdio,HTTP 推 v0.18(staging 现无 HTTP MCP server 需求)
- **自写 JSON-RPC protocol** — 用官方 `mcp` lib 1.26.0(已装),只写 PRAXIS Tool 适配层
- **CC npx 生态适配** — staging node v12.22.9 无 npx,推迟到运维装 node 18+(见 §7)
- **BashTool / 本地 shell** — v0.17 第二个子项目,独立 spec
- **MCP server 沙盒强化** — MCP server 是 admin 配的受信 subprocess,不做额外沙盒

---

## 1. 关键决策记录(brainstorm 结论)

| # | 决策 | 理由 |
|---|---|---|
| 1 | 先做 MCP client(不是 BashTool) | 安全面小(受信 subprocess,无需 sandbox+白名单+ASK 三层)+ 一次性解锁大量能力 + mcp lib 已装 |
| 2 | 只做 stdio transport | 覆盖 MCP 生态 90%+ server;HTTP 推 v0.18 |
| 3 | 用 mcp lib 官方 client + 只写适配层 | next-steps §2.1.1 已定方向 + 避免 over-engineering(不自写 protocol) |
| 4 | 进程级常驻连接池 | npx/python server 启动几百 ms~秒级,每请求 spawn 不可接受;常驻池一次性开销 |

---

## 2. 架构总览

```
praxis2/mcp/
  __init__.py        # 包标识 + 导出 MCPConnectionPool / MCPTool / MCPServerSpec
  config.py          # parse PRAXIS_MCP_SERVERS_JSON → list[MCPServerSpec]
  pool.py            # MCPConnectionPool:进程级常驻 stdio 连接 + crash retry
  tool_adapter.py    # MCPTool(Tool):包装单个 MCP server 暴露的一个 tool
```
(3 个实质模块 config/pool/tool_adapter + `__init__.py` 导出,§8 DoD 的"四模块"即此。)

### 数据流

```
make_app()
  → load config.mcp_servers_json → list[MCPServerSpec]
  → MCPConnectionPool.start_all()
       每个 server: stdio_client() spawn subprocess
                    → ClientSession.initialize()
                    → list_tools() → [tool_spec, ...]
                    → 每个 tool_spec 包成 MCPTool 实例缓存
  → app._mcp_pool = pool(挂 app 实例,类似 _session_pool)

build_chat_registry(selection)
  → reg.register(内建 5 工具)
  → for mcp_tool in app._mcp_pool.all_tools(): reg.register(mcp_tool, builtin=False)
  → query() 把 reg.openai_tools() 给 LLM,模型可发起 mcp__* tool_use
```

### 组件边界(每个单元一个清晰职责)

- **config.py**:纯函数 `parse_mcp_servers(json_str) -> list[MCPServerSpec]`,
  解析 + 校验(name/command 必填),失败 fail-fast ConfigError。无 IO、无状态。
- **pool.py**:`MCPConnectionPool` 管理 subprocess 生命周期 + session 缓存 + crash retry。
  依赖 mcp lib(stdio_client/ClientSession)。唯一有状态 + IO 的单元。
- **tool_adapter.py**:`MCPTool(Tool)` 无状态包装,持有 session 引用 + remote tool 元数据。
  run() 委托 `session.call_tool()`。依赖 Tool 基类 + pool 提供的 session。

---

## 3. MCPServerSpec(config 契约)

```python
@dataclass
class MCPServerSpec:
    name: str            # 唯一标识(MCPTool 前缀用),如 "fs" / "echo"
    command: str         # 可执行,如 "python" / "node"
    args: list[str]      # 参数,如 ["-m", "my_mcp_fs", "/sandbox"]
    env: dict[str, str]  # 可选额外环境变量(默认空,继承父进程)
```

`PRAXIS_MCP_SERVERS_JSON` 格式:
```json
[
  {"name": "echo", "command": "python", "args": ["-m", "tests.fixtures.echo_mcp_server"]},
  {"name": "fs", "command": "python", "args": ["-m", "mcp_server_filesystem", "/data"]}
]
```

`config.py:Settings` 加字段:
```python
mcp_servers_json: str = ""   # 零值即关(无 MCP server),与现有 fail-fast 模式一致
```
解析时机:`MCPConnectionPool.start_all()` 内调 `parse_mcp_servers(settings.mcp_servers_json)`;
空串 → 空 list → pool 不 spawn 任何 server(零回归:不配 MCP 时行为与 v0.16 完全一致)。

---

## 4. MCPConnectionPool 生命周期

```python
class MCPConnectionPool:
    def __init__(self, specs: list[MCPServerSpec], *, retry: int = 2, call_timeout_s: float = 30.0): ...

    async def start_all(self) -> None:
        """make_app 时一次。每个 server spawn + initialize + list_tools,
        失败 retry `retry` 次仍失败 → 跳过该 server + audit log(不阻塞其他/不阻塞 chat)。"""

    def all_tools(self) -> list[MCPTool]:
        """返回所有已连接 server 的全部 MCPTool(build_chat_registry 用)。"""

    async def close_all(self) -> None:
        """app shutdown 优雅 kill 所有 subprocess。"""
```

- **进程级单例**:挂 app 实例(`app._mcp_pool`)。多 worker 各自一份
  (stdio subprocess 不能跨进程共享,与 SessionPool worker 级缓存同理)。
- **crash retry**:start_all 时某 server initialize/list_tools 抛 → retry 2 次 →
  仍失败:`_logger.warning` + audit log,**跳过该 server**,继续下一个。
  pool 永不因单个 server 失败而整体崩溃。
- **mid-call crash**:server 在 call_tool 中途死 → 异常在 MCPTool.run() 捕获(§5),
  不影响 pool(下次 call 仍尝试,失败再返 ok=False)。本 MVP **不做自动重连**
  (重连推 v0.18;mid-call crash 在 staging 受信 server 下罕见)。

---

## 5. MCPTool 适配层

```python
class MCPTool(Tool):
    """包装单个 MCP server 的单个远端 tool。无状态(持 session 引用 + 远端元数据)。"""
    rmcp_op = None  # MCP 工具是外部能力,不受 RMCP 相位门约束(与 BrainQuery/FileRead 同)

    def __init__(self, *, server_name: str, session, remote_name: str,
                 description: str, input_schema: dict, call_timeout_s: float): ...

    @property
    def name(self) -> str:
        return f"mcp__{self._server_name}__{self._remote_name}"  # 前缀防冲突,对齐 CC 命名

    def input_schema(self) -> dict:
        return self._remote_input_schema  # 直接透传 list_tools 返回的 inputSchema

    async def run(self, payload) -> ToolResult:
        try:
            result = await self._session.call_tool(
                self._remote_name, payload,
                read_timeout_seconds=timedelta(seconds=self._call_timeout_s),
            )
        except Exception as e:  # noqa: BLE001 — server crash/timeout 不冒泡致 500
            return ToolResult(ok=False, error=f"MCP call 失败({type(e).__name__}: {e})")
        # CallToolResult.isError + .content(list[TextContent|...])
        text = _extract_text(result.content)
        return ToolResult(ok=not result.isError, value=text,
                          error=None if not result.isError else text)
```

### 命名前缀

`mcp__<server>__<tool>` 三段式:
- 防与内建 5 工具(SkillExec/BrainQuery/RMCPWriteCase/FileRead/WebFetch)冲突
- 对齐 Claude Code 的 `mcp__<server>__<tool>` 约定(用户/模型熟悉)
- `ToolRegistry.register(builtin=False)`:内建工具优先,MCP 工具同名不覆盖内建
  (§7.3.4 已有逻辑,零改动)

### 序列化(零改动)

`anthropic_tools()` / `openai_tools()` 遍历 `_tools.values()` 自动包含 MCPTool。
不需改 registry。

---

## 6. 错误处理矩阵

| 失败点 | 行为 | 用户/模型可见 |
|---|---|---|
| config JSON 非法 | `parse_mcp_servers` 抛 ConfigError | make_app fail-fast(启动即报,不静默) |
| server spawn 失败 | retry 2 → 跳过 + audit log | 该 server 工具不出现在池,chat 正常 |
| initialize/list_tools 失败 | retry 2 → 跳过 + audit log | 同上 |
| call_tool 超时/crash | MCPTool.run() 捕获 → ok=False | tool_result is_error,模型自救 |
| server 返 isError=True | ok=False + error=content | tool_result is_error,模型自救 |

核心不变式:**任何 MCP 失败都不致 chat-stream 500,不阻塞其他工具**。

---

## 7. 测试策略(应对 staging node v12 无 npx)

### 约束发现
staging node v12.22.9 且无 npx → 大多数 CC MCP server(`npx @modelcontextprotocol/
server-*`)在 staging **跑不了**。但 Python-based stdio MCP server 可以(staging 有 conda/python)。

### 单测
- **`tests/fixtures/echo_mcp_server.py`**:用 mcp lib 的 **server API** 写一个最小
  stdio MCP server,暴露 1-2 个 tool(如 `echo(text)` / `add(a,b)`)
- `test_mcp_config.py`:`parse_mcp_servers` 解析 + fail-fast(空串/非法 JSON/缺 name)
- `test_mcp_pool.py`:pool spawn echo server + initialize + list_tools + close_all 往返
- `test_mcp_tool_adapter.py`:MCPTool.run() 调 echo → 验返回;命名前缀;crash/timeout → ok=False
- `test_mcp_registry_integration.py`:build_chat_registry 含 MCPTool + 命名不冲突内建

### e2e(staging)
- staging 配 `PRAXIS_MCP_SERVERS_JSON` 指向 Python echo server(repo 内,不依赖 npx)
- chat 里让 AI 调 `mcp__echo__echo` → 验 SSE tool_start/tool_end 真往返
- curl + SSE,对齐 v0.16 e2e 套路

### CC npx 生态适配(§2.1.3)——推迟
staging node v12 无 npx → 推迟到运维装 node 18+ + npx 后,再写
`mcp-from-claude-code.py` 扫 `~/.claude/mcp.json` 转 config。
**本 MVP 不阻塞在此**(用 Python server 完成端到端验证已足够证明链路)。

---

## 8. DoD

- [ ] `praxis2/mcp/{__init__,config,pool,tool_adapter}.py` 四模块
- [ ] `tests/fixtures/echo_mcp_server.py` Python stdio MCP server fixture
- [ ] 单测:config 解析 + fail-fast / pool spawn-list-call-close 往返 /
      MCPTool 命名前缀 + crash/timeout ok=False / registry 集成不冲突
- [ ] `config.py:Settings.mcp_servers_json` + load_from_env 接入
- [ ] `app.py` make_app 接 `_mcp_pool.start_all()` + shutdown close_all
- [ ] `chat_registry.py` 从 pool 取 MCPTool register
- [ ] 全量回归绿(零回归:不配 MCP 时行为与 v0.16 完全一致)
- [ ] e2e:staging Python echo MCP server,chat 真调 `mcp__echo__*`
- [ ] commit + push + tag v0.17.0-alpha + memory
- [ ] 备注:CC npx 生态适配(§2.1.3)推迟到 staging 装 node 18+

---

## 9. 依赖 + 部署影响

- **pyproject**:`mcp>=1.26,<2` 加进 dependencies(当前已装但未声明)
- **staging env**:`PRAXIS_MCP_SERVERS_JSON`(可选,空=关;MVP 配 echo server)
- **不动**:litellm / FE(纯 backend 加法)/ 现有 5 工具 / SessionPool / 主链
- **回滚**:不配 `PRAXIS_MCP_SERVERS_JSON` → pool 空 → 行为 == v0.16.3,
  git revert mcp/ 模块即可

---

## 10. 后续(本子项目之后)

- v0.17 子项目 2:**BashTool**(本地 + 远端 shell,sandbox+白名单+ASK 三层,独立 spec)
- v0.18:MCP HTTP/SSE transport + mid-call 自动重连 + CC npx 生态适配(需 node 18+)
