"""Tests for module planner."""
import json

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.llm_orchestration.module_planner import LLMModulePlanner


class FakeLLMClient:
    """Test fixture: FakeLLMClient."""
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
    """Verify emits module candidates llm not module plan."""
    msg = _run(json.dumps({"selected_modules": ["genetic_hub", "stress_processor"],
                           "reasoning_summary": "gene expression + stress", "risk_flags": []}))
    assert msg is not None
    assert msg.message_type == "module_candidates_llm"
    assert msg.receiver == "ModuleRouterAgent"

    mc = msg.payload["module_candidates"]
    assert set(mc["selected"]) <= set(mc["candidates"])


def test_llm_selection_filtered_to_candidates():
    """Verify llm selection filtered to candidates."""
    msg = _run(json.dumps({"selected_modules": ["genetic_hub", "not_a_module", "INVENTED"],
                           "reasoning_summary": "", "risk_flags": []}))
    sel = msg.payload["module_candidates"]["selected"]
    assert "not_a_module" not in sel
    assert "INVENTED" not in sel
    assert "genetic_hub" in sel


def test_llm_empty_content_fail_closed():
    """Verify llm empty content fail closed."""
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
    """Verify payload passes through request and support."""
    msg = _run(json.dumps({"selected_modules": ["genetic_hub"], "reasoning_summary": "", "risk_flags": []}))
    assert msg.payload["request"]["species"] == "human"
    assert "module_support" in msg.payload
    assert "mismatch_queries" in msg.payload


def test_planner_calls_llm_with_candidates_in_prompt():
    """Verify planner calls llm with candidates in prompt."""
    fc = FakeLLMClient(json.dumps({"selected_modules": ["genetic_hub"], "reasoning_summary": "", "risk_flags": []}))
    bus = MessageBus()
    LLMModulePlanner(fc).handle(AgentMessage(
        message_id="c1", sender="SpeciesContextAgent", receiver="LLMModulePlanner",
        message_type="module_plan_request",
        payload={"request": {"species": "human", "perturbation_object": "gene",
                             "target_output": "expression", "perturbation_targets": ["AHR"]},
                 "module_support": _support_all_strong(), "mismatch_queries": {}}, timestamp="t1"), bus)
    user_msg = fc.calls[0][-1]["content"]
    assert "genetic_hub" in user_msg
