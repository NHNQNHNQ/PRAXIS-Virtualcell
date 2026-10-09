import asyncio

from praxis2.mcp.tool_adapter import MCPTool


class _FakeContent:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _FakeCallResult:
    def __init__(self, content, is_error=False):
        self.content = content
        self.isError = is_error
        self.structuredContent = None


class _FakeSession:
    def __init__(self, result=None, raises=None):
        self._result = result
        self._raises = raises
        self.calls = []

    async def call_tool(self, name, arguments=None, read_timeout_seconds=None):
        self.calls.append((name, arguments))
        if self._raises:
            raise self._raises
        return self._result


def _mk_tool(session, remote_name="echo"):
    return MCPTool(
        server_name="echo",
        session=session,
        remote_name=remote_name,
        description="\u56de\u663e",
        input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
        call_timeout_s=30.0,
    )


def test_name_has_mcp_prefix():
    t = _mk_tool(_FakeSession())
    assert t.name == "mcp__echo__echo"


def test_rmcp_op_is_none():

    assert _mk_tool(_FakeSession()).rmcp_op is None


def test_input_schema_passthrough():
    t = _mk_tool(_FakeSession())
    assert t.input_schema() == {"type": "object", "properties": {"text": {"type": "string"}}}


def test_input_schema_fallback_when_empty():
    t = MCPTool(
        server_name="x", session=_FakeSession(), remote_name="y", description="", input_schema=None, call_timeout_s=30.0
    )
    assert t.input_schema() == {"type": "object", "properties": {}}


def test_run_success_returns_text():
    sess = _FakeSession(_FakeCallResult([_FakeContent("echo: hi")], is_error=False))
    t = _mk_tool(sess)
    r = asyncio.run(t.run({"text": "hi"}))
    assert r.ok
    assert "echo: hi" in r.value
    assert sess.calls == [("echo", {"text": "hi"})]


def test_run_is_error_returns_ok_false():
    sess = _FakeSession(_FakeCallResult([_FakeContent("Unknown tool")], is_error=True))
    t = _mk_tool(sess)
    r = asyncio.run(t.run({"text": "x"}))
    assert not r.ok
    assert "Unknown tool" in (r.error or "")


def test_run_exception_returns_ok_false_not_raise():

    sess = _FakeSession(raises=RuntimeError("connection lost"))
    t = _mk_tool(sess)
    r = asyncio.run(t.run({"text": "x"}))
    assert not r.ok
    assert "connection lost" in (r.error or "")


def test_run_multi_content_joins_text():
    sess = _FakeSession(_FakeCallResult([_FakeContent("part1"), _FakeContent("part2")], is_error=False))
    t = _mk_tool(sess)
    r = asyncio.run(t.run({}))
    assert "part1" in r.value and "part2" in r.value
