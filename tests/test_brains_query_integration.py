import httpx
import respx

from praxis2.agents.loader import resolve_agent
from praxis2.brains.migrate import build_fixture_brain
from praxis2.brains.retrieve_first import retrieve_first
from praxis2.core.prompt import build_effective_system_prompt, to_api_system
from praxis2.core.query import query
from praxis2.core.rmcp import Phase, get_phase, set_phase
from praxis2.core.seams import MinimalCompactor
from praxis2.core.state import State, TerminalReason
from praxis2.llm.client import AnthropicClient
from praxis2.tools.base import Tool, ToolResult
from praxis2.tools.permission import PhaseAwarePermission, RulePermissionPolicy
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from tests.cassette import load


class SkillRunner(Tool):
    name = "skill_runner"
    rmcp_op = "call_skill"

    def input_schema(self):
        return {"type": "object", "properties": {"skill": {"type": "string"}}}

    async def run(self, payload):
        return ToolResult(ok=True, value=f"Skill {payload.get('skill')} executed successfully")


def _settings():
    class S:
        model = "m"
        max_tokens = 64
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2

    return S()


@respx.mock
async def test_same_query_path_retrieve_inject_then_execute_allowed():

    sel = resolve_agent("Virtualcell", user_query="\u51b7\u51bb\u7535\u955c \u4e09\u7ef4\u91cd\u6784")
    st = State()
    rf = retrieve_first(
        st,
        sel,
        domain_docs=build_fixture_brain("Virtualcell"),
        common_docs=build_fixture_brain("_common"),
        user_query="Virtualcell \u9886\u57df",
        skill_summary="## skill: wf1\n- description: \u91cd\u6784\u6d41\u7a0b",
        memory_text="- [Rule](rmcp.md) — RMCP",
    )
    assert get_phase(st) is Phase.RETRIEVE
    assert rf.degraded_to_bare is False
    eff = build_effective_system_prompt(agent=rf.sections)
    api_system = to_api_system(eff)
    blob = " ".join(b["text"] for b in api_system)
    assert "Virtualcell" in blob or "\u9886\u57df" in blob
    assert "RMCP" in blob

    set_phase(st, Phase.ANTI_FILTER)
    set_phase(st, Phase.PLAN)
    set_phase(st, Phase.EXECUTE)

    reg = ToolRegistry()
    reg.register(SkillRunner())
    runner = SerialToolRunner(
        reg,
        recovery_budget=3,
        permission=PhaseAwarePermission(RulePermissionPolicy([])),
    )
    client = AnthropicClient(api_key="sk", base_url="https://up.example")

    respx.post("https://up.example/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(
                200,
                text=load("openai_retrieve_then_skill.sse"),
                headers={"content-type": "text/event-stream"},
            ),
            httpx.Response(
                200,
                text=load("openai_skill_final.sse"),
                headers={"content-type": "text/event-stream"},
            ),
        ]
    )
    st.messages = [{"role": "user", "content": "\u6267\u884c\u91cd\u6784\u6280\u80fd"}]
    events = []
    async for e in query(
        st,
        client=client,
        registry=reg,
        settings=_settings(),
        runner=runner,
        compactor=MinimalCompactor(),
        system=api_system,
    ):
        events.append(e)
    tr = [e for e in events if e["type"] == "tool_result"]
    assert tr and tr[0]["is_error"] is False
    assert "executed successfully" in tr[0]["content"]
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    await client.aclose()


@respx.mock
async def test_bare_mode_common_only_degraded_no_domain():

    sel = resolve_agent("bare", user_query="\u968f\u4fbf\u95ee")
    st = State()
    rf = retrieve_first(
        st,
        sel,
        domain_docs=[],
        common_docs=build_fixture_brain("_common"),
        user_query="\u968f\u4fbf\u95ee",
    )
    assert rf.degraded_to_bare is True
    assert get_phase(st) is Phase.INIT
    eff = build_effective_system_prompt(agent=rf.sections)
    blob = " ".join(b["text"] for b in to_api_system(eff))
    assert "RMCP" in blob or "_common" in blob
    assert "Retrieval fallback" in blob
