from praxis2.core.query import query
from praxis2.core.seams import MinimalCompactor
from praxis2.core.state import State, TerminalReason
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from tests._llm_fakes import TURN_FINAL_TEXT, FakeLLMClient


class _S:
    model = "m"
    max_tokens = 64
    max_turns = 20
    recovery_budget = 3
    max_output_recovery = 2


class _SpyCompactor:
    def __init__(self):
        self.calls = 0

    async def compact(self, state):
        self.calls += 1
        state.messages = state.messages[-1:]


async def test_precompact_gate_fires_once_before_streaming():
    client = FakeLLMClient(turns=[TURN_FINAL_TEXT])
    cmp = _SpyCompactor()
    st = State()
    st.messages = [{"role": "user", "content": "q"}]
    fired = {"n": 0}

    def gate(s):
        fired["n"] += 1
        return fired["n"] == 1

    last = None
    async for e in query(
        st,
        client=client,
        registry=ToolRegistry(),
        settings=_S(),
        runner=SerialToolRunner(ToolRegistry(), recovery_budget=3),
        compactor=cmp,
        precompact_gate=gate,
    ):
        last = e
    assert cmp.calls == 1
    assert last == {"type": "end", "reason": TerminalReason.STOP.value}
    await client.aclose()


async def test_no_gate_behaves_exactly_as_m3():
    client = FakeLLMClient(turns=[TURN_FINAL_TEXT])
    st = State()
    st.messages = [{"role": "user", "content": "q"}]
    last = None
    async for e in query(
        st,
        client=client,
        registry=ToolRegistry(),
        settings=_S(),
        runner=SerialToolRunner(ToolRegistry(), recovery_budget=3),
        compactor=MinimalCompactor(),
    ):
        last = e
    assert last == {"type": "end", "reason": TerminalReason.STOP.value}
    assert st.turn_count == 1
    await client.aclose()
