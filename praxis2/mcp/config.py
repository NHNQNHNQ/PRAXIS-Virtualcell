from __future__ import annotations

import json
import math
from dataclasses import dataclass, field


@dataclass
class MCPServerSpec:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    startup_timeout_s: float | None = None

    def __post_init__(self) -> None:
        timeout = self.startup_timeout_s
        if timeout is None:
            return
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise ValueError("startup_timeout_s must be a finite positive number")
        try:
            timeout = float(timeout)
        except OverflowError as exc:
            raise ValueError("startup_timeout_s must be a finite positive number") from exc
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("startup_timeout_s must be a finite positive number")
        self.startup_timeout_s = timeout


def parse_mcp_servers(json_str: str) -> list[MCPServerSpec]:

    s = (json_str or "").strip()
    if not s:
        return []
    try:
        raw = json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"PRAXIS_MCP_SERVERS_JSON is not valid JSON:{e}") from e
    if not isinstance(raw, list):
        raise ValueError(f"PRAXIS_MCP_SERVERS_JSON must be a list; received {type(raw).__name__}")
    specs: list[MCPServerSpec] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"MCP server[{i}] must be an object; received {type(item).__name__}")
        name = item.get("name")
        command = item.get("command")
        if not name:
            raise ValueError(f"MCP server[{i}] is missing required name")
        if not command:
            raise ValueError(f"MCP server[{i}] (name={name!r}) is missing required command")
        raw_args = item.get("args") or []
        if not isinstance(raw_args, list):
            raise ValueError(f"MCP server[{i}] (name={name!r}) args must be a list; received {type(raw_args).__name__}")
        raw_env = item.get("env") or {}
        if not isinstance(raw_env, dict):
            raise ValueError(
                f"MCP server[{i}] (name={name!r}) env must be an object; received {type(raw_env).__name__}"
            )
        specs.append(
            MCPServerSpec(
                name=str(name),
                command=str(command),
                args=list(raw_args),
                env=dict(raw_env),
                startup_timeout_s=item.get("startup_timeout_s"),
            )
        )
    return specs
