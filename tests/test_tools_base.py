import pytest

from praxis2.tools.base import Tool, ToolResult


def test_toolresult_ok_and_error_shape():
    ok = ToolResult(ok=True, value={"n": 1})
    assert ok.ok and ok.value == {"n": 1} and ok.error is None
    err = ToolResult(ok=False, error="\u7f3a\u5c11\u5305 numpy", recovery_hint="\u5728 env bio \u88c5 numpy")
    assert err.ok is False and err.value is None
    assert err.error == "\u7f3a\u5c11\u5305 numpy" and err.recovery_hint == "\u5728 env bio \u88c5 numpy"


def test_tool_defaults_are_conservative():

    class T(Tool):
        name = "t"

        def input_schema(self):
            return {"type": "object", "properties": {}}

        async def run(self, payload):
            return ToolResult(ok=True, value="r")

    t = T()
    assert t.is_concurrency_safe({}) is False
    t.validate_input({})


def test_tool_is_abstract():
    with pytest.raises(TypeError):
        Tool()


async def test_concrete_tool_runs():
    class Echo(Tool):
        name = "echo"
        description = "\u56de\u663e text"

        def input_schema(self):
            return {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            }

        async def run(self, payload):
            return ToolResult(ok=True, value=payload["text"])

    r = await Echo().run({"text": "hi"})
    assert r.ok and r.value == "hi"
