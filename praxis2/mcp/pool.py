"""MCPConnectionPool:进程级常驻 stdio MCP 连接池(v0.17 子项目 1)。

AsyncExitStack 维持常驻 session(spike 验证:enter_async_context 手动管理
stdio_client + ClientSession,不用嵌套 async with);start_all 首次 spawn
所有 server,单个失败 retry → 跳过 + audit(不阻塞其他/不阻塞 chat)。

进程级单例(挂 app 实例);多 worker 各自一份(stdio subprocess 不能跨进程共享)。
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import AsyncExitStack

from praxis2.mcp.config import MCPServerSpec
from praxis2.mcp.tool_adapter import MCPTool

_logger = logging.getLogger("praxis2.mcp")

_DEFAULT_RETRY = 2
_DEFAULT_CALL_TIMEOUT_S = 30.0
_DEFAULT_STARTUP_TIMEOUT_S = 10.0


class MCPConnectionPool:
    def __init__(
        self,
        specs: list[MCPServerSpec],
        *,
        retry: int = _DEFAULT_RETRY,
        call_timeout_s: float = _DEFAULT_CALL_TIMEOUT_S,
        startup_timeout_s: float = _DEFAULT_STARTUP_TIMEOUT_S,
    ) -> None:
        self._specs = specs
        self._retry = retry
        self._call_timeout_s = call_timeout_s
        self._startup_timeout_s = startup_timeout_s
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
        from mcp import ClientSession, StdioServerParameters  # noqa: PLC0415
        from mcp.client.stdio import stdio_client  # noqa: PLC0415
        last_err: Exception | None = None
        startup_timeout_s = spec.startup_timeout_s or self._startup_timeout_s
        for _attempt in range(self._retry + 1):
            sub = AsyncExitStack()
            try:
                params = StdioServerParameters(
                    command=spec.command,
                    args=spec.args,
                    env=spec.env or None,
                )
                read, write = await sub.enter_async_context(stdio_client(params))
                session = await sub.enter_async_context(ClientSession(read, write))
                # 握手加超时:防 server spawn 成功但不讲 MCP 协议时永久挂起
                # (call_timeout_s 只管 call_tool,管不到 initialize/list_tools)
                await asyncio.wait_for(
                    session.initialize(), timeout=startup_timeout_s
                )
                listed = await asyncio.wait_for(
                    session.list_tools(), timeout=startup_timeout_s
                )
                for t in listed.tools:
                    self._tools.append(MCPTool(
                        server_name=spec.name,
                        session=session,
                        remote_name=t.name,
                        description=t.description or "",
                        input_schema=t.inputSchema,
                        call_timeout_s=self._call_timeout_s,
                    ))
                # 成功:把这个 server 的 cleanup 转移到主 stack(close_all 统一关)
                self._stack.push_async_callback(sub.aclose)
                _logger.info(
                    "MCP server %r 启动,注册 %d 个 tool",
                    spec.name, len(listed.tools),
                )
                return
            except Exception as e:  # noqa: BLE001 — 单 server 失败不阻塞其他
                last_err = e
                # 立即清这个 attempt 的残留(子进程/流),不污染主 stack
                try:
                    await sub.aclose()
                except Exception:  # noqa: BLE001 — cleanup 失败忽略
                    pass
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
        """优雅关闭所有 subprocess(app shutdown 调)。

        已知边界:lazy-once start 在首个请求的 task,而 shutdown 在另一 task,
        anyio 不允许跨 task 退出 cancel scope → aclose 抛 cancel-scope RuntimeError。
        此时子进程由 OS 在 worker 退出时兜底回收(已 spike 验证 call_tool 跨 task
        本身安全,仅 close 受影响)。降级 debug 日志,不冒泡。
        """
        try:
            await self._stack.aclose()
        except RuntimeError as e:
            if "cancel scope" in str(e):
                _logger.debug(
                    "MCP pool close_all 跨 task(已知,OS 兜底回收子进程):%r", e
                )
            else:
                _logger.warning("MCP pool close_all RuntimeError(忽略):%r", e)
        except Exception as e:  # noqa: BLE001 — 关闭失败不应抛(OS 也会回收子进程)
            _logger.warning("MCP pool close_all 异常(忽略):%r", e)
        self._tools = []
        self._started = False
