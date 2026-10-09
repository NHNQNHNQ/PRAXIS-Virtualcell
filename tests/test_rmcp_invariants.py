from praxis2.core.query import query
from praxis2.core.rmcp import Phase, get_phase, set_phase
from praxis2.core.seams import MinimalCompactor, PermissionDecision
from praxis2.core.state import State, TerminalReason
from praxis2.hooks.builtin import advance_phase_on_retrieve, doi_required, make_rmcp_stop_gate
from praxis2.tools.base import Tool, ToolResult
from praxis2.tools.permission import PhaseAwarePermission, RulePermissionPolicy
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from tests._llm_fakes import TURN_FINAL_TEXT, FakeLLMClient


class _RetrieveTool:
    name = "retrieve_cases"
    rmcp_op = "retrieve_cases"


class _ExecTool:
    name = "skill_runner"
    rmcp_op = "call_skill"


def _ok(tid="tu1"):
    return {
        "type": "tool_result",
        "tool_use_id": tid,
        "is_error": False,
        "content": "\u547d\u4e2d 3 \u6761\u6848\u4f8b",
    }


def test_invariant1_execute_denied_until_retrieve_advances_phase():

    pol = PhaseAwarePermission(RulePermissionPolicy([]))
    st = State()  # INIT
    assert pol.check(tool=_ExecTool(), payload={}, state=st).decision is PermissionDecision.DENY

    advance_phase_on_retrieve(_RetrieveTool(), {"id": "tu1"}, _ok(), st)
    assert get_phase(st) is Phase.RETRIEVE

    set_phase(st, Phase.EXECUTE)
    assert pol.check(tool=_ExecTool(), payload={}, state=st).decision is PermissionDecision.ALLOW


def test_advance_phase_on_retrieve_idempotent_and_only_on_success():
    st = State()
    advance_phase_on_retrieve(_RetrieveTool(), {"id": "t"}, _ok(), st)
    advance_phase_on_retrieve(_RetrieveTool(), {"id": "t"}, _ok(), st)
    assert get_phase(st) is Phase.RETRIEVE

    st2 = State()
    err = {"type": "tool_result", "tool_use_id": "t", "is_error": True, "content": "\u68c0\u7d22\u5931\u8d25"}
    advance_phase_on_retrieve(_RetrieveTool(), {"id": "t"}, err, st2)
    assert get_phase(st2) is Phase.INIT


def test_non_retrieve_tool_does_not_advance_phase():
    st = State()

    class _U:
        name = "read"
        rmcp_op = None

    advance_phase_on_retrieve(_U(), {"id": "t"}, _ok(), st)
    assert get_phase(st) is Phase.INIT


class WriteCase(Tool):
    name = "write_case"
    rmcp_op = "write_case"

    def input_schema(self):
        return {"type": "object", "properties": {}}

    async def run(self, payload):
        return ToolResult(ok=True, value="\u6848\u4f8b\u6b63\u6587,\u65e0 doi")


def _settings3():
    class S:
        model = "m"
        max_tokens = 64
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2

    return S()


async def test_inv2_doi_veto_through_real_runner_post_hooks():

    reg = ToolRegistry()
    reg.register(WriteCase())
    runner = SerialToolRunner(reg, recovery_budget=3, post_hooks=[doi_required])
    st = State()

    set_phase(st, Phase.SEAL)
    results = await runner.run_turn([{"id": "tu1", "name": "write_case", "input": {}}], st)
    assert results[0]["is_error"] is True
    assert "DOI" in results[0]["content"] and "Required condition" in results[0]["content"]


async def test_inv3_stop_gate_vetoes_final_through_query():

    reg = ToolRegistry()
    runner = SerialToolRunner(reg, recovery_budget=3)

    client = FakeLLMClient(turns=[TURN_FINAL_TEXT, TURN_FINAL_TEXT])
    st = State()
    st.messages = [{"role": "user", "content": "\u7ed9\u7ed3\u8bba"}]

    real_gate = make_rmcp_stop_gate()

    def gate_with_recovery(state):
        dec = real_gate(state)
        if dec.veto:
            state.tool_use_context["evidence_ok"] = True
            state.tool_use_context["anti_filter_ok"] = True
        return dec

    last = None
    async for e in query(
        st,
        client=client,
        registry=reg,
        settings=_settings3(),
        runner=runner,
        compactor=MinimalCompactor(),
        stop_hook=gate_with_recovery,
    ):
        last = e
    assert last == {"type": "end", "reason": TerminalReason.STOP.value}

    assert client._idx == 2
    assert sum(1 for m in st.messages if m["role"] == "user" and "RMCP final-state veto" in str(m["content"])) == 1
    await client.aclose()
