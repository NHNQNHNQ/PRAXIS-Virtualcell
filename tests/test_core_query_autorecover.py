from praxis2.core.query import query
from praxis2.core.seams import AllowAllPermission, MinimalCompactor
from praxis2.core.state import State, TerminalReason
from praxis2.tools.base import Tool, ToolResult
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from tests._llm_fakes import TURN_BOOM_TOOL, TURN_FINAL_TEXT, FakeLLMClient


class Boom(Tool):
    name = "boom"

    def input_schema(self):
        return {"type": "object", "properties": {}}

    async def run(self, payload):
        return ToolResult(
            ok=False, error="\u70b8\u4e86:\u4f9d\u8d56 X \u7f3a\u5931", recovery_hint="\u88c5 X \u540e\u91cd\u8bd5"
        )


def _reg_runner(budget):
    reg = ToolRegistry()
    reg.register(Boom())
    return reg, SerialToolRunner(reg, recovery_budget=budget, permission=AllowAllPermission())


class _S:
    model = "m"
    max_tokens = 64
    max_turns = 50
    recovery_budget = 2
    max_output_recovery = 2


async def test_failing_tool_loop_continues_not_stop_and_counts_recovery():

    reg, runner = _reg_runner(budget=3)

    class S3:
        model = "m"
        max_tokens = 64
        max_turns = 50
        recovery_budget = 3
        max_output_recovery = 2

    client = FakeLLMClient(turns=[TURN_BOOM_TOOL, TURN_BOOM_TOOL, TURN_FINAL_TEXT])
    st = State()
    st.messages = [{"role": "user", "content": "\u5e72\u6d3b"}]
    events = [
        e
        async for e in query(
            st,
            client=client,
            registry=reg,
            settings=S3(),
            runner=runner,
            compactor=MinimalCompactor(),
        )
    ]

    err_results = [e for e in events if e["type"] == "tool_result" and e["is_error"]]
    assert len(err_results) >= 1
    assert err_results[0]["recovery_hint"] == "\u88c5 X \u540e\u91cd\u8bd5"
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    assert st.recovery_attempts == 2
    await client.aclose()


async def test_recovery_budget_exhausted_escalates():

    reg, runner = _reg_runner(budget=2)

    client = FakeLLMClient(turns=[TURN_BOOM_TOOL] * 10)
    st = State()
    st.messages = [{"role": "user", "content": "\u5e72\u6d3b"}]
    last = None
    async for e in query(
        st,
        client=client,
        registry=reg,
        settings=_S(),
        runner=runner,
        compactor=MinimalCompactor(),
    ):
        last = e
    assert last == {"type": "end", "reason": TerminalReason.ESCALATED.value}
    assert st.recovery_attempts >= 2
    await client.aclose()
