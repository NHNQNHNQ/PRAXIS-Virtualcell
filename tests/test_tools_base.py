import pytest

from praxis2.tools.base import Tool, ToolResult


def test_toolresult_ok_and_error_shape():
    ok = ToolResult(ok=True, value={"n": 1})
    assert ok.ok and ok.value == {"n": 1} and ok.error is None
    err = ToolResult(ok=False, error="缺少包 numpy", recovery_hint="在 env bio 装 numpy")
    assert err.ok is False and err.value is None
    assert err.error == "缺少包 numpy" and err.recovery_hint == "在 env bio 装 numpy"


def test_tool_defaults_are_conservative():
    # §7.3.1:默认并发不安全(保守)
    class T(Tool):
        name = "t"

        def input_schema(self):
            return {"type": "object", "properties": {}}

        async def run(self, payload):
            return ToolResult(ok=True, value="r")

    t = T()
    assert t.is_concurrency_safe({}) is False
    t.validate_input({})  # 默认放行,不抛


def test_tool_is_abstract():
    with pytest.raises(TypeError):
        Tool()  # 抽象类不能实例化


async def test_concrete_tool_runs():
    class Echo(Tool):
        name = "echo"
        description = "回显 text"

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
