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
        self._audit: list[dict] = []
        self._started = False

    async def start_all(self) -> None:

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

                await asyncio.wait_for(session.initialize(), timeout=startup_timeout_s)
                listed = await asyncio.wait_for(session.list_tools(), timeout=startup_timeout_s)
                for t in listed.tools:
                    self._tools.append(
                        MCPTool(
                            server_name=spec.name,
                            session=session,
                            remote_name=t.name,
                            description=t.description or "",
                            input_schema=t.inputSchema,
                            call_timeout_s=self._call_timeout_s,
                        )
                    )

                self._stack.push_async_callback(sub.aclose)
                _logger.info(
                    "MCP server %r started with %d tools",
                    spec.name,
                    len(listed.tools),
                )
                return
            except Exception as e:  # noqa: BLE001
                last_err = e

                try:
                    await sub.aclose()
                except Exception:  # noqa: BLE001
                    pass
                continue
        self._audit.append({"server": spec.name, "error": repr(last_err)})
        _logger.warning(
            "MCP server %r failed to start after %d retries; skipped: %r",
            spec.name,
            self._retry,
            last_err,
        )

    def all_tools(self) -> list[MCPTool]:
        return list(self._tools)

    def audit_log(self) -> list[dict]:
        return list(self._audit)

    async def close_all(self) -> None:

        try:
            await self._stack.aclose()
        except RuntimeError as e:
            if "cancel scope" in str(e):
                _logger.debug("MCP pool close_all task mismatch; process cleanup remains available: %r", e)
            else:
                _logger.warning("MCP pool close_all RuntimeError ignored: %r", e)
        except Exception as e:  # noqa: BLE001
            _logger.warning("MCP pool close_all error ignored: %r", e)
        self._tools = []
        self._started = False
