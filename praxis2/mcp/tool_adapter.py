from __future__ import annotations

from datetime import timedelta
from typing import Any

from praxis2.tools.base import Tool, ToolResult

_DEFAULT_SCHEMA = {"type": "object", "properties": {}}


def _extract_text(content: list) -> str:

    parts: list[str] = []
    for c in content or []:
        text = getattr(c, "text", None)
        if text is not None:
            parts.append(str(text))
    return "\n".join(parts)


class MCPTool(Tool):
    rmcp_op = None

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
        except Exception as e:  # noqa: BLE001
            return ToolResult(
                ok=False,
                error=f"MCP call failed ({type(e).__name__}: {e})",
                recovery_hint=(
                    f"MCP server {self._server_name!r}may have stopped or timed out; retry or select another tool."
                ),
            )
        text = _extract_text(getattr(result, "content", []))
        is_error = bool(getattr(result, "isError", False))
        if is_error:
            return ToolResult(ok=False, error=text or "MCP server returned isError=True")
        return ToolResult(ok=True, value=text)
