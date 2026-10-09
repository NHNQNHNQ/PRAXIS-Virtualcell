from praxis2.core.query import query
from praxis2.core.seams import AllowAllPermission, MinimalCompactor, StopDecision
from praxis2.core.state import State, TerminalReason
from praxis2.hooks.builtin import make_rmcp_stop_gate
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from tests._llm_fakes import TURN_FINAL_TEXT, FakeLLMClient


def _settings():
    class S:
        model = "m"
        max_tokens = 64
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2

    return S()


def _two_finals_client():
    return FakeLLMClient(turns=[TURN_FINAL_TEXT, TURN_FINAL_TEXT])


async def test_stop_hook_vetoes_then_forces_one_more_turn():

    reg = ToolRegistry()
    runner = SerialToolRunner(reg, recovery_budget=3, permission=AllowAllPermission())
    client = _two_finals_client()
    st = State()
    st.messages = [{"role": "user", "content": "\u7ed9\u7ed3\u8bba"}]

    real_gate = make_rmcp_stop_gate()

    def gate_with_recovery(state: State) -> StopDecision:
        dec = real_gate(state)
        if dec.veto:
            state.tool_use_context["evidence_ok"] = True
            state.tool_use_context["anti_filter_ok"] = True
        return dec

    events = [
        e
        async for e in query(
            st,
            client=client,
            registry=reg,
            settings=_settings(),
            runner=runner,
            compactor=MinimalCompactor(),
            stop_hook=gate_with_recovery,
        )
    ]

    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    injected = [m for m in st.messages if m["role"] == "user" and "RMCP final-state veto" in str(m["content"])]
    assert len(injected) == 1

    assert st.pending_stop_reasons == []
    await client.aclose()


async def test_stop_hook_passes_when_evidence_ok():
    reg = ToolRegistry()
    runner = SerialToolRunner(reg, recovery_budget=3, permission=AllowAllPermission())
    client = FakeLLMClient(turns=[TURN_FINAL_TEXT])
    st = State()
    st.messages = [{"role": "user", "content": "\u7ed9\u7ed3\u8bba"}]
    st.tool_use_context["evidence_ok"] = True
    st.tool_use_context["anti_filter_ok"] = True
    events = [
        e
        async for e in query(
            st,
            client=client,
            registry=reg,
            settings=_settings(),
            runner=runner,
            compactor=MinimalCompactor(),
            stop_hook=make_rmcp_stop_gate(),
        )
    ]
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    assert not any("RMCP final-state veto" in str(m["content"]) for m in st.messages)
    await client.aclose()


async def test_stop_hook_rechecks_each_terminal_until_satisfied():

    reg = ToolRegistry()
    runner = SerialToolRunner(reg, recovery_budget=3, permission=AllowAllPermission())

    client = FakeLLMClient(turns=[TURN_FINAL_TEXT, TURN_FINAL_TEXT, TURN_FINAL_TEXT])

    call_count = {"n": 0}

    def always_veto(state: State) -> StopDecision:
        call_count["n"] += 1
        return StopDecision(veto=True, message=f"[veto-{call_count['n']}] Persistent test veto")

    class S:
        model = "m"
        max_tokens = 64

        max_turns = 2
        recovery_budget = 3
        max_output_recovery = 2

    st = State()
    st.messages = [{"role": "user", "content": "\u7ed9\u7ed3\u8bba"}]
    events = [
        e
        async for e in query(
            st,
            client=client,
            registry=reg,
            settings=S(),
            runner=runner,
            compactor=MinimalCompactor(),
            stop_hook=always_veto,
        )
    ]

    assert call_count["n"] == 3
    assert events[-1] == {"type": "end", "reason": TerminalReason.MAX_TURNS.value}

    assert len(st.pending_stop_reasons) == 3
    assert all("veto-" in r for r in st.pending_stop_reasons)
    await client.aclose()


async def test_stop_hook_passes_after_evidence_set_mid_turns():

    reg = ToolRegistry()
    runner = SerialToolRunner(reg, recovery_budget=3, permission=AllowAllPermission())
    client = _two_finals_client()

    call_count = {"n": 0}
    stop_hook = make_rmcp_stop_gate()

    def gate_with_mid_inject(state: State) -> StopDecision:
        call_count["n"] += 1
        dec = stop_hook(state)

        if call_count["n"] == 1:
            state.tool_use_context["evidence_ok"] = True
            state.tool_use_context["anti_filter_ok"] = True
        return dec

    st = State()
    st.messages = [{"role": "user", "content": "\u7ed9\u7ed3\u8bba"}]
    events = [
        e
        async for e in query(
            st,
            client=client,
            registry=reg,
            settings=_settings(),
            runner=runner,
            compactor=MinimalCompactor(),
            stop_hook=gate_with_mid_inject,
        )
    ]

    assert call_count["n"] == 2
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}

    assert st.pending_stop_reasons == []
    await client.aclose()
