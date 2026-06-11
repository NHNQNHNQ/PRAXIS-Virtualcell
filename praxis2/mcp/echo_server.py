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
