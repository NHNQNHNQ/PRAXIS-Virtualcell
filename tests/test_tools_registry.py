from praxis2.tools.base import Tool, ToolResult
from praxis2.tools.registry import ToolRegistry


class _Stub(Tool):
    def __init__(self, name, desc=""):
        self.name = name
        self.description = desc

    def input_schema(self):
        return {"type": "object", "properties": {"x": {"type": "string"}}}

    async def run(self, payload):
        return ToolResult(ok=True, value=self.name)


def test_register_and_get():
    r = ToolRegistry()
    r.register(_Stub("a"))
    assert r.get("a") is not None
    assert r.get("missing") is None


def test_builtin_wins_name_conflict():
    # §7.3.4:名字冲突内建优先,后注册的非内建被忽略
    r = ToolRegistry()
    builtin = _Stub("dup", "builtin")
    external = _Stub("dup", "external")
    r.register(builtin, builtin=True)
    r.register(external, builtin=False)
    assert r.get("dup").description == "builtin"


def test_anthropic_tools_shape():
    r = ToolRegistry()
    r.register(_Stub("echo", "回显"))
    tools = r.anthropic_tools()
    assert tools == [
        {
            "name": "echo",
            "description": "回显",
            "input_schema": {"type": "object", "properties": {"x": {"type": "string"}}},
        }
    ]


def test_openai_tools_shape():
    """M10.5:openai_tools() 返 [{type:'function', function:{...}}] 形。"""
    r = ToolRegistry()
    r.register(_Stub("fake_tool", "Fake tool for test"))
    tools = r.openai_tools()
    assert len(tools) == 1
    t = tools[0]
    assert t["type"] == "function"
    assert t["function"]["name"] == "fake_tool"
    assert t["function"]["description"] == "Fake tool for test"
    assert t["function"]["parameters"]["type"] == "object"
    assert t["function"]["parameters"]["properties"]["x"]["type"] == "string"


def test_openai_tools_empty_when_no_tools():
    """openai_tools() 无注册工具时返空列表。"""
    r = ToolRegistry()
    assert r.openai_tools() == []


def test_anthropic_tools_still_works():
    """backward:M10.5 保留 anthropic_tools()(v0.12 cleanup window 删)。"""
    r = ToolRegistry()
    r.register(_Stub("f", "d"))
    out = r.anthropic_tools()
    assert out[0]["name"] == "f"
    assert "input_schema" in out[0]
