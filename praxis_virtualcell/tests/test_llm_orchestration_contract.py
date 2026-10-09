"""Tests for llm orchestration contract."""
import ast
import json

import pytest

from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import (
    LLM_MODES,
    Mode,
    RuntimeConfig,
    assert_llm_boundaries,
)
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.llm_orchestration import safety_contract as SC
from praxis_virtualcell.llm_orchestration.module_planner import LLMModulePlanner


class FakeLLMClient:
    def __init__(self, content):
        self.enabled = True
        self._content = content

    def complete(self, messages, *, json_mode=False, max_tokens=1024):
        return {"disabled": False, "content": self._content, "error": None}



@pytest.mark.parametrize("mode", [Mode.LLM_ORCHESTRATED, Mode.LLM_ORCHESTRATED_STRICT])
def test_three_flags_false_all_orchestrated_modes(mode):
    c = RuntimeConfig(mode=mode, deepseek_api_key="sk-fake")
    assert c.allow_llm_to_modify_core_decision is False
    assert c.allow_llm_to_modify_prediction is False
    assert c.allow_llm_to_override_hard_rules is False
    assert_llm_boundaries(c)


@pytest.mark.parametrize("flag", [
    "allow_llm_to_modify_core_decision",
    "allow_llm_to_modify_prediction",
    "allow_llm_to_override_hard_rules",
])
def test_assert_boundaries_still_raises_under_orchestrated(flag):
    """Verify assert boundaries still raises under orchestrated."""
    c = RuntimeConfig(mode=Mode.LLM_ORCHESTRATED, deepseek_api_key="sk-fake")
    object.__setattr__(c, flag, True)
    with pytest.raises(Exception):  # noqa: B017
        assert_llm_boundaries(c)


def test_orchestrated_modes_in_llm_modes():
    assert Mode.LLM_ORCHESTRATED in LLM_MODES
    assert Mode.LLM_ORCHESTRATED_STRICT in LLM_MODES
    assert Mode.OFFLINE not in LLM_MODES



def _support_all_strong():
    return {mid: {"support": "strong", "verdict": "accept"} for mid in M.MODULE_ORDER}


def _planner_msg(content):
    bus = MessageBus()
    LLMModulePlanner(FakeLLMClient(content)).handle(AgentMessage(
        "c1", "SpeciesContextAgent", "LLMModulePlanner", "module_plan_request",
        {"request": {"species": "human", "perturbation_object": "gene",
                     "target_output": "expression", "perturbation_targets": ["AHR"]},
         "module_support": _support_all_strong(), "mismatch_queries": {}}, "t1"), bus)
    return bus


def test_planner_emits_agentmessage_not_plan():
    bus = _planner_msg(json.dumps({"selected_modules": ["genetic_hub"],
                                   "reasoning_summary": "", "risk_flags": []}))

    assert bus.latest("module_candidates_llm") is not None
    assert bus.latest("module_plan_ready") is None


def test_planner_output_is_agentmessage_type():
    bus = _planner_msg(json.dumps({"selected_modules": ["genetic_hub"],
                                   "reasoning_summary": "", "risk_flags": []}))
    msg = bus.latest("module_candidates_llm")
    assert isinstance(msg, AgentMessage)
    assert msg.receiver == "ModuleRouterAgent"



def test_llm_cannot_select_unsupported_module():
    """Verify llm cannot select unsupported module."""
    sup = _support_all_strong()
    sup["degradation_machinery"] = {"support": "unsupported", "verdict": "reject"}
    from praxis_virtualcell.agents.species_schema import normalize_request
    req = normalize_request({"species": "human", "perturbation_object": "gene",
                             "target_output": "expression", "perturbation_targets": ["AHR"]})
    cands = SC.build_candidate_modules(req, sup)
    assert "degradation_machinery" not in cands
    out = SC.sanitize_llm_plan(
        json.dumps({"selected_modules": ["genetic_hub", "degradation_machinery"]}),
        cands, primary="genetic_hub")
    assert "degradation_machinery" not in out["selected_modules"]


def test_assert_plan_within_bounds_catches_unsupported_leak():
    plan = {"primary": "genetic_hub", "secondary": ["degradation_machinery"],
            "entries": [{"module": "genetic_hub"}, {"module": "degradation_machinery"}]}
    assert SC.assert_plan_within_bounds(plan, ["genetic_hub"]) != []



def _plan_with_llm(request, selected):
    bus = MessageBus()
    SpeciesContextAgent().handle(AgentMessage(
        "c1", "SpeciesBrain", "SpeciesContextAgent", "species_context",
        {"request": request}, "t1"), bus)
    ctx = bus.latest("species_context_ready").payload
    ModuleRouterAgent().handle(AgentMessage(
        "c2", "LLMModulePlanner", "ModuleRouterAgent", "module_route",
        {"request": request, "module_support": ctx["module_support"],
         "mismatch_queries": ctx["mismatch_queries"],
         "module_candidates": {"selected": selected, "candidates": [],
                               "reasoning_summary": "", "risk_flags": []}}, "t2"), bus)
    return bus.latest("module_plan_ready").payload


def test_llm_cannot_upgrade_bacteria_expression_to_accept():
    p = _plan_with_llm(
        {"species": "bacteria", "perturbation_object": "gene",
         "target_output": "expression", "perturbation_targets": ["b0720"]},
        selected=["genetic_hub"])
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["verdict"] != "accept"


def test_llm_cannot_upgrade_mouse_ortholog_caution_to_accept():
    p = _plan_with_llm(
        {"species": "mouse", "perturbation_object": "gene",
         "target_output": "expression", "perturbation_targets": ["Gata1"]},
        selected=["genetic_hub"])
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["verdict"] == "caution"


def test_llm_cannot_change_primary():
    """Verify llm cannot change primary."""
    p = _plan_with_llm(
        {"species": "human", "perturbation_object": "gene",
         "target_output": "expression", "perturbation_targets": ["AHR"]},
        selected=["stress_processor", "cytoplasmic_metabolism"])
    assert p["primary"] == "genetic_hub"


def test_llm_mismatch_still_downgrades():
    """Verify llm mismatch still downgrades."""

    p = _plan_with_llm(
        {"species": "bacteria", "perturbation_object": "gene",
         "target_output": "growth", "perturbation_targets": ["lon"]},
        selected=["cytoplasmic_metabolism", "degradation_machinery"])
    degs = [e for e in p["entries"] if e["module"] == "degradation_machinery"]
    for e in degs:
        assert e["verdict"] != "accept"



def test_llm_unavailable_falls_back_to_primary():
    out = SC.sanitize_llm_plan(None, ["genetic_hub", "stress_processor"], primary="genetic_hub")
    assert "llm_unavailable" in out["risk_flags"]
    assert "genetic_hub" in out["selected_modules"]


def test_llm_parse_failed_falls_back():
    out = SC.sanitize_llm_plan("{bad", ["genetic_hub"], primary="genetic_hub")
    assert "llm_parse_failed" in out["risk_flags"]
    assert out["selected_modules"] == ["genetic_hub"]



def test_offline_deterministic_modules_import_no_llm():
    """Verify offline deterministic modules import no llm."""
    files = [
        "praxis_virtualcell/agents/module_rules.py",
        "praxis_virtualcell/biological_modules/module_plan.py",
        "praxis_virtualcell/agents/species_context_agent.py",
        "praxis_virtualcell/llm_orchestration/safety_contract.py",
    ]


    bad = []
    for f in files:
        tree = ast.parse(open(f, encoding="utf-8").read(), filename=f)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any("agents_llm" in a.name for a in node.names):
                    bad.append(f)
            elif isinstance(node, ast.ImportFrom):
                if node.module and "agents_llm" in node.module:
                    bad.append(f)
    assert bad == [], f"Deterministic OFFLINE files must not import agents_llm:  {bad}"


def test_safety_contract_has_no_llm_client_import():
    src = open("praxis_virtualcell/llm_orchestration/safety_contract.py", encoding="utf-8").read()
    assert "llm_client" not in src
    assert "httpx" not in src



def test_llm_selected_only_affects_secondary_not_prediction_fields():
    """Verify llm selected only affects secondary not prediction fields."""
    p = _plan_with_llm(
        {"species": "human", "perturbation_object": "gene",
         "target_output": "expression", "perturbation_targets": ["AHR"]},
        selected=["genetic_hub", "stress_processor"])
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["engine"] == "donor_predictor"
    assert prim["route_disposition"] == "accept"
