"""MCP server 配置契约 + PRAXIS_MCP_SERVERS_JSON 解析(纯函数,fail-fast)。"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field


@dataclass
class MCPServerSpec:
    """单个 MCP server 的启动规格(stdio transport)。"""

    name: str            # 唯一标识(MCPTool 前缀用),如 "echo" / "fs"
    command: str         # 可执行(注意:必须指向有 mcp lib 的解释器)
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    startup_timeout_s: float | None = None  # None=pool 默认；可按 server 覆盖

    def __post_init__(self) -> None:
        timeout = self.startup_timeout_s
        if timeout is None:
            return
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise ValueError("startup_timeout_s must be a finite positive number")
        try:
            timeout = float(timeout)
        except OverflowError as exc:
            raise ValueError(
                "startup_timeout_s must be a finite positive number"
            ) from exc
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("startup_timeout_s must be a finite positive number")
        self.startup_timeout_s = timeout


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
        raw_args = item.get("args") or []
        if not isinstance(raw_args, list):
            raise ValueError(
                f"MCP server[{i}] (name={name!r}) args 必须是 list,"
                f"得到 {type(raw_args).__name__}"
            )
        raw_env = item.get("env") or {}
        if not isinstance(raw_env, dict):
            raise ValueError(
                f"MCP server[{i}] (name={name!r}) env 必须是 object,"
                f"得到 {type(raw_env).__name__}"
            )
        specs.append(MCPServerSpec(
            name=str(name),
            command=str(command),
            args=list(raw_args),
            env=dict(raw_env),
            startup_timeout_s=item.get("startup_timeout_s"),
        ))
    return specs
