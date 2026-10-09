from praxis2.core.query import query
from praxis2.core.seams import AllowAllPermission, MinimalCompactor
from praxis2.core.state import State, TerminalReason
from praxis2.tools.base import Tool, ToolResult
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from tests._llm_fakes import (
    TURN_AFTER_TOOL,
    TURN_BOOM_TOOL,
    TURN_TOOLUSE,
    FakeLLMClient,
)


class Echo(Tool):
    name = "echo"

    def input_schema(self):
        return {"type": "object", "properties": {"t": {"type": "string"}}}

    async def run(self, payload):
        return ToolResult(ok=True, value=payload["t"])


class Boom(Tool):
    name = "boom"

    def input_schema(self):
        return {"type": "object", "properties": {}}

    async def run(self, payload):
        return ToolResult(ok=False, error="\u70b8\u4e86", recovery_hint="\u88c5 X \u540e\u91cd\u8bd5")


_API_TOOL_RESULT_KEYS = {"type", "tool_use_id", "content", "is_error"}


def _settings():
    class S:
        model = "m"
        max_tokens = 64
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2

    return S()


async def test_two_turn_closed_loop_tool_then_final_answer():
    reg = ToolRegistry()
    reg.register(Echo())
    runner = SerialToolRunner(reg, recovery_budget=3, permission=AllowAllPermission())

    client = FakeLLMClient(turns=[TURN_TOOLUSE, TURN_AFTER_TOOL])
    st = State()
    st.messages = [{"role": "user", "content": "\u67e5 hi"}]
    events = [
        e
        async for e in query(
            st,
            client=client,
            registry=reg,
            settings=_settings(),
            runner=runner,
            compactor=MinimalCompactor(),
            system="\u52a9\u624b",
        )
    ]
    types = [e["type"] for e in events]

    assert types == ["text", "tool_use", "tool_result", "text", "end"]
    tr = next(e for e in events if e["type"] == "tool_result")
    assert tr["is_error"] is False and tr["content"] == "hi"
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}

    assert st.messages[1]["role"] == "assistant"
    assert st.messages[1]["content"][0]["type"] == "tool_use"
    assert st.messages[2]["role"] == "user"
    assert st.messages[2]["content"][0]["type"] == "tool_result"
    assert st.turn_count == 2
    await client.aclose()


async def test_max_turns_terminates_when_model_keeps_calling_tools():

    reg = ToolRegistry()
    reg.register(Echo())
    runner = SerialToolRunner(reg, recovery_budget=99, permission=AllowAllPermission())

    client = FakeLLMClient(turns=[TURN_TOOLUSE] * 10)

    class S:
        model = "m"
        max_tokens = 64
        max_turns = 3
        recovery_budget = 99
        max_output_recovery = 2

    st = State()
    st.messages = [{"role": "user", "content": "\u5faa\u73af\u5427"}]
    last = None
    async for e in query(
        st,
        client=client,
        registry=reg,
        settings=S(),
        runner=runner,
        compactor=MinimalCompactor(),
    ):
        last = e
    assert last == {"type": "end", "reason": TerminalReason.MAX_TURNS.value}
    assert st.turn_count >= 3
    await client.aclose()


async def test_error_tool_result_serialized_api_valid_with_folded_content():

    reg = ToolRegistry()
    reg.register(Boom())
    runner = SerialToolRunner(reg, recovery_budget=3, permission=AllowAllPermission())

    client = FakeLLMClient(turns=[TURN_BOOM_TOOL, TURN_AFTER_TOOL])
    st = State()
    st.messages = [{"role": "user", "content": "\u5e72\u6d3b"}]
    events = [
        e
        async for e in query(
            st,
            client=client,
            registry=reg,
            settings=_settings(),
            runner=runner,
            compactor=MinimalCompactor(),
        )
    ]
    tr_msg = next(
        m
        for m in st.messages
        if m["role"] == "user"
        and isinstance(m["content"], list)
        and m["content"]
        and m["content"][0].get("type") == "tool_result"
    )
    block = tr_msg["content"][0]
    assert set(block.keys()) == _API_TOOL_RESULT_KEYS
    assert block["is_error"] is True
    assert "\u88c5 X \u540e\u91cd\u8bd5" in block["content"]
    assert "[Remaining recovery budget]" in block["content"]

    yielded = next(e for e in events if e["type"] == "tool_result")
    assert yielded["recovery_hint"] == "\u88c5 X \u540e\u91cd\u8bd5"
    await client.aclose()
