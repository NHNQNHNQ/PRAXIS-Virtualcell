from praxis2.core.query import query
from praxis2.core.rmcp import Phase, get_phase
from praxis2.core.seams import MinimalCompactor
from praxis2.core.state import State, TerminalReason
from praxis2.hooks.builtin import (
    advance_phase_on_real_retrieval,
    make_tool_use_presence_stop_hook,
)
from praxis2.tools.base import Tool, ToolResult
from praxis2.tools.bash_policy import BashCommandPolicy
from praxis2.tools.permission import RetrieveFirstPermission
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from tests._llm_fakes import FakeLLMClient


def _settings():
    class S:
        model = "m"
        max_tokens = 64
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2

    return S()


class _FakeBrainQuery(Tool):
    name = "BrainQuery"
    rmcp_op = None

    def input_schema(self):
        return {"type": "object"}

    async def run(self, payload):
        self.last_retrieval_real_hit = True
        return ToolResult(ok=True, value={"hits": [{"slug": "x"}], "source": "filesystem"})


class _FakeSkill(Tool):
    name = "SkillExec"
    rmcp_op = "call_skill"

    def input_schema(self):
        return {"type": "object"}

    async def run(self, payload):
        return ToolResult(ok=True, value={"result": "docked"})


def _turn_tool_use(tid, name):

    return [
        {"type": "text", "text": ""},
        {"type": "tool_use", "id": tid, "name": name, "input": {}},
        {"type": "message_stop", "stop_reason": "tool_use", "usage": {}},
    ]


def _turn_final(text):

    return [
        {"type": "text", "text": text},
        {"type": "message_stop", "stop_reason": "end_turn", "usage": {}},
    ]


def _runner():

    reg = ToolRegistry()
    reg.register(_FakeBrainQuery())
    reg.register(_FakeSkill())

    perm = RetrieveFirstPermission(BashCommandPolicy())
    runner = SerialToolRunner(
        reg,
        recovery_budget=3,
        permission=perm,
        post_hooks=[advance_phase_on_real_retrieval],
    )
    return reg, runner


async def test_premature_execute_denied_then_retrieve_unlocks():

    reg, runner = _runner()
    client = FakeLLMClient(
        turns=[
            _turn_tool_use("tu1", "SkillExec"),
            _turn_tool_use("tu2", "BrainQuery"),
            _turn_tool_use("tu3", "SkillExec"),
            _turn_final("completed"),
        ]
    )
    st = State()
    st.messages = [{"role": "user", "content": "\u5bf9\u63a5 imatinib \u5230 1iep"}]

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

    tool_results = [e for e in events if e.get("type") == "tool_result"]

    assert any(e.get("is_error") and "Retrieval is required" in (e.get("content") or "") for e in tool_results), (
        f"SkillExec without retrieval must be denied; tool results={tool_results}"
    )

    assert get_phase(st) is not Phase.INIT, f"Successful BrainQuery must advance beyond INIT; observed={get_phase(st)}"

    assert any(not e.get("is_error") for e in tool_results), (
        f"SkillExec after retrieval must be allowed; tool results={tool_results}"
    )

    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}

    await client.aclose()


async def test_claim_without_tools_vetoed_then_stops():

    reg, runner = _runner()
    claim_text = "\u6211\u5df2\u5bf9\u63a5\u5b8c\u6210,\u6700\u4f73\u4eb2\u548c\u529b -9.2 kcal/mol\u3002"
    client = FakeLLMClient(
        turns=[
            _turn_final(claim_text),
            _turn_final(claim_text),
        ]
    )
    st = State()
    st.messages = [{"role": "user", "content": "\u5bf9\u63a5\u5e76\u7ed9\u5206"}]

    events = [
        e
        async for e in query(
            st,
            client=client,
            registry=reg,
            settings=_settings(),
            runner=runner,
            compactor=MinimalCompactor(),
            stop_hook=make_tool_use_presence_stop_hook(),
        )
    ]

    assert st.stop_hook_veto_count == 1, f"Expected one veto; veto count={st.stop_hook_veto_count}"

    assert any(
        m["role"] == "user" and "Unsupported execution claim" in str(m.get("content", "")) for m in st.messages
    ), f"Expected an unsupported-execution warning; messages={st.messages}"

    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}

    await client.aclose()
