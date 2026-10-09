from mcp.server.fastmcp import FastMCP

mcp = FastMCP("praxis-echo")


@mcp.tool()
def echo(text: str) -> str:

    return f"echo: {text}"


@mcp.tool()
def add(a: int, b: int) -> int:

    return a + b


if __name__ == "__main__":
    mcp.run("stdio")
