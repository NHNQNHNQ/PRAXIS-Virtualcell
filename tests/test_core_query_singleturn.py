from praxis2.core.query import query
from praxis2.core.seams import AllowAllPermission, MinimalCompactor
from praxis2.core.state import State, TerminalReason
from praxis2.tools.base import Tool, ToolResult
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from tests._llm_fakes import TURN_FINAL_TEXT, TURN_TOOLUSE, FakeLLMClient


class Echo(Tool):
    name = "echo"

    def input_schema(self):
        return {"type": "object", "properties": {"t": {"type": "string"}}}

    async def run(self, payload):
        return ToolResult(ok=True, value=payload["t"])


def _deps():
    reg = ToolRegistry()
    reg.register(Echo())
    runner = SerialToolRunner(reg, recovery_budget=3, permission=AllowAllPermission())
    return reg, runner


def _settings(**over):
    class S:
        model = "m"
        max_tokens = 64
        max_turns = over.get("max_turns", 20)
        recovery_budget = 3
        max_output_recovery = 2

    return S()


async def test_single_turn_final_text_terminates_stop():
    reg, runner = _deps()
    client = FakeLLMClient(turns=[TURN_FINAL_TEXT])
    st = State()
    st.messages = [{"role": "user", "content": "\u95ee\u4e2a\u95ee\u9898"}]
    events = [
        e
        async for e in query(
            st,
            client=client,
            registry=reg,
            settings=_settings(),
            runner=runner,
            compactor=MinimalCompactor(),
            system="\u4f60\u662f\u52a9\u624b",
        )
    ]
    assert {"type": "text", "text": "The answer is 42"} in events
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    assert st.turn_count == 1
    await client.aclose()


async def test_text_and_tooluse_interleave_order_preserved():

    reg, runner = _deps()
    client = FakeLLMClient(turns=[TURN_TOOLUSE])
    st = State()
    st.messages = [{"role": "user", "content": "\u67e5 hi"}]
    seen = []
    async for e in query(
        st,
        client=client,
        registry=reg,
        settings=_settings(max_turns=1),
        runner=runner,
        compactor=MinimalCompactor(),
    ):
        seen.append(e)
        if e["type"] == "tool_result":
            break
    types = [e["type"] for e in seen]
    assert types[0] == "text" and types[1] == "tool_use"
    assert seen[0] == {"type": "text", "text": "I will check."}
    assert seen[1] == {"type": "tool_use", "id": "tu_1", "name": "echo", "input": {"t": "hi"}}
    await client.aclose()
