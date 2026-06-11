"""MCP(Model Context Protocol)client 子系统(v0.17 子项目 1)。

stdio transport only;用官方 mcp lib 1.26.0 的 client,只写 PRAXIS Tool 适配层。
公开:MCPServerSpec/parse_mcp_servers(config 契约)、MCPTool(适配层)、
MCPConnectionPool(常驻连接池)。
"""
from praxis2.mcp.config import MCPServerSpec, parse_mcp_servers
from praxis2.mcp.pool import MCPConnectionPool
from praxis2.mcp.tool_adapter import MCPTool

__all__ = ["MCPServerSpec", "parse_mcp_servers", "MCPConnectionPool", "MCPTool"]
