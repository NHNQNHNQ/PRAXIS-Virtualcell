"""§7.5.0 末句验证:所有 agent 模式共用同一 query()/prompt 路径,不产生第二条代码路径。

test_same_query_path_retrieve_inject_then_execute_allowed:
    resolve_agent → retrieve_first(推进 RETRIEVE)→ build_effective_system_prompt(agent=)
    → to_api_system → set_phase 模拟到 EXECUTE → query() 跑 rmcp_op="call_skill"
    经真实 PhaseAwarePermission 放行闭环。

test_bare_mode_common_only_degraded_no_domain:
    bare 模式 prompt 层:仅 _common(S13)+ 显式降级不静默。
    query() 路径唯一性由 test_same_query_path 覆盖(本测试止于 prompt 层)
"""

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
    rmcp_op = "call_skill"  # execute 类:相位门约束

    def input_schema(self):
        return {"type": "object", "properties": {"skill": {"type": "string"}}}

    async def run(self, payload):
        return ToolResult(ok=True, value=f"技能 {payload.get('skill')} 执行 ok")


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
    # §7.5.0 末句:所有模式共用同一 query()/prompt 路径,不产生第二条代码路径
    sel = resolve_agent("Cryo", user_query="冷冻电镜 三维重构")
    st = State()
    rf = retrieve_first(
        st,
        sel,
        domain_docs=build_fixture_brain("Cryo"),
        common_docs=build_fixture_brain("_common"),
        user_query="冷冻电镜 三维重构怎么做",
        skill_summary="## skill: wf1\n- description: 重构流程",
        memory_text="- [Rule](rmcp.md) — RMCP",
    )
    assert get_phase(st) is Phase.RETRIEVE
    assert rf.degraded_to_bare is False
    eff = build_effective_system_prompt(agent=rf.sections)
    api_system = to_api_system(eff)
    blob = " ".join(b["text"] for b in api_system)
    assert "冷冻电镜" in blob or "三维重构" in blob
    assert "RMCP" in blob

    # 跳过 AF/PLAN 工具调用直接推进 EXECUTE 以测 skill 放行
    # (RETRIEVE→ANTI_FILTER→PLAN→EXECUTE 是 M3 S7 合法链,沿用 M3 体例)
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
    # M10.5 切 OpenAI /v1/chat/completions:用 OpenAI 风格 cassette 对齐
    # client._http.post("/v1/chat/completions") 实际 wire(旧 m5_*.sse 仍保留
    # 给 m6/m7 用,那些测试不真 parse SSE 流)。
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
    st.messages = [{"role": "user", "content": "执行重构技能"}]
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
    assert "执行 ok" in tr[0]["content"]
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    await client.aclose()


@respx.mock
async def test_bare_mode_common_only_degraded_no_domain():
    # bare 模式 prompt 层:仅 _common(S13)+ 显式降级不静默。
    # query() 路径唯一性由 test_same_query_path 覆盖(本测试止于 prompt 层)
    sel = resolve_agent("bare", user_query="随便问")
    st = State()
    rf = retrieve_first(
        st,
        sel,
        domain_docs=[],
        common_docs=build_fixture_brain("_common"),
        user_query="随便问",
    )
    assert rf.degraded_to_bare is True
    assert get_phase(st) is Phase.INIT
    eff = build_effective_system_prompt(agent=rf.sections)
    blob = " ".join(b["text"] for b in to_api_system(eff))
    assert "RMCP" in blob or "_common" in blob
    assert "降级" in blob
