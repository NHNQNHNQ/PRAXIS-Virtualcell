"""Tests for module consistency."""
from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.governance.module_consistency import check_module_plan


def _plan_for(request):
    bus = MessageBus()
    SpeciesContextAgent().handle(AgentMessage(
        message_id="c1", sender="SpeciesBrain", receiver="SpeciesContextAgent",
        message_type="species_context", payload={"request": request}, timestamp="t1"), bus)
    ctx = bus.latest("species_context_ready").payload
    ModuleRouterAgent().handle(AgentMessage(
        message_id="c2", sender="SpeciesContextAgent", receiver="ModuleRouterAgent",
        message_type="module_route",
        payload={"request": request, "module_support": ctx["module_support"],
                 "mismatch_queries": ctx["mismatch_queries"]}, timestamp="t2"), bus)
    return bus.latest("module_plan_ready").payload


def test_clean_plan_has_no_violations():
    p = _plan_for({"species": "human", "perturbation_object": "gene",
                   "target_output": "expression", "perturbation_targets": ["AHR"]})
    assert check_module_plan(p) == []


def test_reject_plan_has_no_violations_either():
    """Verify reject plan has no violations either."""
    p = _plan_for({"species": "bacteria", "perturbation_object": "gene",
                   "target_output": "expression", "perturbation_targets": ["b0720"]})
    assert check_module_plan(p) == []


def test_detects_verdict_more_optimistic_than_route():
    """Verify detects verdict more optimistic than route."""
    bad = {"species": "human", "request": {}, "primary": "genetic_hub",
           "secondary": [], "overall_verdict": "accept", "notes": [],
           "entries": [{"module": "genetic_hub", "role": "primary", "engine": "reject",
                        "route_disposition": "abstain", "species_support": "strong",
                        "species_verdict": "accept", "verdict": "accept",
                        "caution_flags": [], "data_gated": False, "pillars": [],
                        "available_models": [], "reason": "x", "mismatch": None}]}
    v = check_module_plan(bad)
    assert any("more_optimistic" in x or "verdict" in x for x in v)


def test_detects_mismatch_entry_accepted():
    """Verify detects mismatch entry accepted."""
    bad = {"species": "bacteria", "request": {}, "primary": "degradation_machinery",
           "secondary": [], "overall_verdict": "accept", "notes": [],
           "entries": [{"module": "degradation_machinery", "role": "primary", "engine": "reject",
                        "route_disposition": "accept", "species_support": "weak",
                        "species_verdict": "accept", "verdict": "accept",
                        "caution_flags": [], "data_gated": False, "pillars": [],
                        "available_models": [], "reason": "x", "mismatch": "caution"}]}
    v = check_module_plan(bad)
    assert any("mismatch" in x for x in v)


def test_detects_engine_out_of_module_whitelist():
    """Verify detects engine out of module whitelist."""
    bad = {"species": "human", "request": {}, "primary": "genetic_hub",
           "secondary": [], "overall_verdict": "accept", "notes": [],
           "entries": [{"module": "genetic_hub", "role": "primary", "engine": "gem_fba",
                        "route_disposition": "accept", "species_support": "strong",
                        "species_verdict": "accept", "verdict": "accept",
                        "caution_flags": [], "data_gated": False, "pillars": [],
                        "available_models": [], "reason": "x", "mismatch": None}]}
    v = check_module_plan(bad)
    assert any("whitelist" in x or "engine" in x for x in v)


def test_all_representative_golden_plans_are_consistent():
    """Verify all representative golden plans are consistent."""
    for req in (
        {
            "species": "human",
            "perturbation_object": "gene",
            "target_output": "expression",
            "perturbation_targets": ["AHR"],
        },
        {
            "species": "bacteria",
            "perturbation_object": "gene",
            "target_output": "growth",
            "perturbation_targets": ["b0720"],
        },
        {
            "species": "mouse",
            "perturbation_object": "gene",
            "target_output": "expression",
            "perturbation_targets": ["Gata1"],
        },
        {
            "species": "yeast",
            "perturbation_object": "gene",
            "target_output": "growth",
            "perturbation_targets": ["YBR166C"],
        },
    ):
        assert check_module_plan(_plan_for(req)) == [], f"{req} plan has consistency violations"
