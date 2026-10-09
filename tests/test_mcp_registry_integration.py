from praxis2.agents.loader import resolve_agent
from praxis2.mcp.tool_adapter import MCPTool
from praxis2.server.chat_registry import build_chat_registry


class _FakeSession:
    async def call_tool(self, name, arguments=None, read_timeout_seconds=None):
        raise NotImplementedError


def _mk_mcp_tool(server, remote):
    return MCPTool(
        server_name=server,
        session=_FakeSession(),
        remote_name=remote,
        description="x",
        input_schema={"type": "object"},
        call_timeout_s=30.0,
    )


def test_registry_includes_mcp_tools():
    sel = resolve_agent("virtualcell", user_query="hi")
    mcp_tools = [_mk_mcp_tool("echo", "echo"), _mk_mcp_tool("echo", "add")]
    reg = build_chat_registry(selection=sel, mcp_tools=mcp_tools)
    names = [t["name"] for t in reg.anthropic_tools()]
    assert "mcp__echo__echo" in names
    assert "mcp__echo__add" in names
    assert "BrainQuery" in names


def test_registry_no_mcp_tools_when_none():

    sel = resolve_agent("virtualcell", user_query="hi")
    reg = build_chat_registry(selection=sel)
    names = [t["name"] for t in reg.anthropic_tools()]
    assert not any(n.startswith("mcp__") for n in names)
    assert "BrainQuery" in names


def test_mcp_tool_registered_alongside_builtins():

    sel = resolve_agent("virtualcell", user_query="hi")
    mt = _mk_mcp_tool("x", "y")
    reg = build_chat_registry(selection=sel, mcp_tools=[mt])
    names = [t["name"] for t in reg.anthropic_tools()]
    assert "mcp__x__y" in names
    assert "BrainQuery" in names


def test_registry_includes_bash_when_sandbox_given(tmp_path):
    from praxis2.agents.loader import resolve_agent
    from praxis2.server.chat_registry import build_chat_registry

    sel = resolve_agent("general", user_query="hi")
    reg = build_chat_registry(selection=sel, bash_sandbox_root=str(tmp_path))
    assert "Bash" in [t["name"] for t in reg.anthropic_tools()]


def test_registry_no_bash_when_sandbox_none():

    from praxis2.agents.loader import resolve_agent
    from praxis2.server.chat_registry import build_chat_registry

    sel = resolve_agent("general", user_query="hi")
    reg = build_chat_registry(selection=sel)
    assert "Bash" not in [t["name"] for t in reg.anthropic_tools()]
    assert "BrainQuery" in [t["name"] for t in reg.anthropic_tools()]
