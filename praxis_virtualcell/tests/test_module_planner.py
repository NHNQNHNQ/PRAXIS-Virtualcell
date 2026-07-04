"""Phase 4:LLMModulePlanner(进 bus,复刻 LLMRouter"只能从候选选")。
用 FakeLLMClient 离线跑(不真调 API,不打 @pytest.mark.llm,保 skip 基线 25)。
铁律:LLM 选中集必 ⊆ candidates;产 module_candidates_llm(不产 ModulePlan);LLM 失败 → fail-closed。"""
import json

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.llm_orchestration.module_planner import LLMModulePlanner


class FakeLLMClient:
    """离线假 client:按预置 content 返回,不联网。enabled=True 以走 complete 分支。"""
    def __init__(self, content):
        self.enabled = True
        self._content = content
        self.calls = []

    def complete(self, messages, *, json_mode=False, max_tokens=1024):
        self.calls.append(messages)
        return {"disabled": False, "content": self._content, "error": None}


def _support_all_strong():
    from praxis_virtualcell.biological_modules import modules as M
    return {mid: {"support": "strong", "verdict": "accept"} for mid in M.MODULE_ORDER}


def _run(content):
    bus = MessageBus()
    LLMModulePlanner(FakeLLMClient(content)).handle(AgentMessage(
        message_id="c1", sender="SpeciesContextAgent", receiver="LLMModulePlanner",
        message_type="module_plan_request",
        payload={"request": {"species": "human", "perturbation_object": "gene",
                             "target_output": "expression", "perturbation_targets": ["AHR"]},
                 "module_support": _support_all_strong(), "mismatch_queries": {}},
        timestamp="t1"), bus)
    return bus.latest("module_candidates_llm")


def test_emits_module_candidates_llm_not_module_plan():
    """红线 3:planner 产 module_candidates_llm(候选),不产 ModulePlan。"""
    msg = _run(json.dumps({"selected_modules": ["genetic_hub", "stress_processor"],
                           "reasoning_summary": "gene expression + stress", "risk_flags": []}))
    assert msg is not None
    assert msg.message_type == "module_candidates_llm"
    assert msg.receiver == "ModuleRouterAgent"
    # 不产 ModulePlan(module_plan_ready 由 ModuleRouter 产,不在此)
    mc = msg.payload["module_candidates"]
    assert set(mc["selected"]) <= set(mc["candidates"])   # 选中 ⊆ 候选


def test_llm_selection_filtered_to_candidates():
    """LLM 选了 candidate 外/发明的 module → 被剔(只能从候选选)。"""
    msg = _run(json.dumps({"selected_modules": ["genetic_hub", "not_a_module", "INVENTED"],
                           "reasoning_summary": "", "risk_flags": []}))
    sel = msg.payload["module_candidates"]["selected"]
    assert "not_a_module" not in sel
    assert "INVENTED" not in sel
    assert "genetic_hub" in sel


def test_llm_empty_content_fail_closed():
    """LLM 返回空 → llm_unavailable + 回退保底含 primary(不丢主模块)。"""
    msg = _run(None)
    mc = msg.payload["module_candidates"]
    assert "llm_unavailable" in mc["risk_flags"]
    assert "genetic_hub" in mc["selected"]


def test_llm_bad_json_fail_closed():
    msg = _run("not json{")
    mc = msg.payload["module_candidates"]
    assert "llm_parse_failed" in mc["risk_flags"]
    assert "genetic_hub" in mc["selected"]


def test_payload_passes_through_request_and_support():
    """透传 request/module_support/mismatch_queries 供下游 ModuleRouter 复用(不丢上下文)。"""
    msg = _run(json.dumps({"selected_modules": ["genetic_hub"], "reasoning_summary": "", "risk_flags": []}))
    assert msg.payload["request"]["species"] == "human"
    assert "module_support" in msg.payload
    assert "mismatch_queries" in msg.payload


def test_planner_calls_llm_with_candidates_in_prompt():
    """system 约束 + user 带 candidates(供审计 prompt 里确实给了候选集)。"""
    fc = FakeLLMClient(json.dumps({"selected_modules": ["genetic_hub"], "reasoning_summary": "", "risk_flags": []}))
    bus = MessageBus()
    LLMModulePlanner(fc).handle(AgentMessage(
        message_id="c1", sender="SpeciesContextAgent", receiver="LLMModulePlanner",
        message_type="module_plan_request",
        payload={"request": {"species": "human", "perturbation_object": "gene",
                             "target_output": "expression", "perturbation_targets": ["AHR"]},
                 "module_support": _support_all_strong(), "mismatch_queries": {}}, timestamp="t1"), bus)
    user_msg = fc.calls[0][-1]["content"]
    assert "genetic_hub" in user_msg          # candidates 在 prompt 里
