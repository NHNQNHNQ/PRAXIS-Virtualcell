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
