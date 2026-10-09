"""Tests for module router llm."""
from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _ctx(request):
    bus = MessageBus()
    SpeciesContextAgent().handle(AgentMessage(
        message_id="c1", sender="SpeciesBrain", receiver="SpeciesContextAgent",
        message_type="species_context", payload={"request": request}, timestamp="t1"), bus)
    return bus.latest("species_context_ready").payload


def _plan_with_candidates(request, selected, risk_flags=None, module_support=None):
    ctx = _ctx(request)

    ms = module_support if module_support is not None else ctx["module_support"]
    bus = MessageBus()
    ModuleRouterAgent().handle(AgentMessage(
        message_id="c2", sender="LLMModulePlanner", receiver="ModuleRouterAgent",
        message_type="module_route",
        payload={"request": request, "module_support": ms,
                 "mismatch_queries": ctx["mismatch_queries"],
                 "module_candidates": {"selected": selected, "candidates": [],
                                       "reasoning_summary": "", "risk_flags": risk_flags or []}},
        timestamp="t2"), bus)
    return bus.latest("module_plan_ready").payload


_HUMAN_GENE = {"species": "human", "perturbation_object": "gene",
               "target_output": "expression", "perturbation_targets": ["AHR"]}


def test_primary_unchanged_even_if_llm_omits_it():
    """Verify primary unchanged even if llm omits it."""
    p = _plan_with_candidates(_HUMAN_GENE, selected=["stress_processor"])
    assert p["primary"] == "genetic_hub"
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["module"] == "genetic_hub"


def test_llm_adds_secondary_from_selection():
    """Verify llm adds secondary from selection."""
    p = _plan_with_candidates(_HUMAN_GENE, selected=["genetic_hub", "stress_processor"])
    assert "stress_processor" in p["secondary"]


def test_llm_cannot_change_verdict_to_accept():
    """Verify llm cannot change verdict to accept."""
    p = _plan_with_candidates(
        {"species": "bacteria", "perturbation_object": "gene",
         "target_output": "expression", "perturbation_targets": ["b0720"]},
        selected=["genetic_hub"])
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["verdict"] != "accept"


def test_offline_path_unchanged_without_candidates():
    """Verify offline path unchanged without candidates."""
    ctx = _ctx({"species": "human", "perturbation_object": "gene",
                "target_output": "growth", "perturbation_targets": ["MYC"]})
    bus = MessageBus()
    ModuleRouterAgent().handle(AgentMessage(
        message_id="c2", sender="SpeciesContextAgent", receiver="ModuleRouterAgent",
        message_type="module_route",
        payload={"request": {"species": "human", "perturbation_object": "gene",
                             "target_output": "growth", "perturbation_targets": ["MYC"]},
                 "module_support": ctx["module_support"],
                 "mismatch_queries": ctx["mismatch_queries"]},
        timestamp="t2"), bus)
    p = bus.latest("module_plan_ready").payload
    assert "mitochondrial_energy_metabolism" in p["secondary"]


def test_llm_risk_flags_surfaced_in_notes():
    """Verify llm risk flags surfaced in notes."""
    p = _plan_with_candidates(_HUMAN_GENE, selected=["genetic_hub"],
                              risk_flags=["llm_unavailable"])
    assert any("llm_unavailable" in n for n in p["notes"])


def test_llm_out_of_candidate_secondary_dropped():
    """Verify llm out of candidate secondary dropped."""
    from praxis_virtualcell.agents.species_schema import normalize_request
    from praxis_virtualcell.biological_modules import modules as M
    from praxis_virtualcell.llm_orchestration import safety_contract as SC

    ctx = _ctx(_HUMAN_GENE)

    ms = {mid: dict(rec) for mid, rec in ctx["module_support"].items()}
    ms["membrane_system"]["support"] = "unsupported"
    ms["membrane_system"]["verdict"] = "reject"


    req = normalize_request(_HUMAN_GENE)
    candidates = SC.build_candidate_modules(req, ms)
    assert "membrane_system" in M.MODULE_ORDER
    assert "membrane_system" not in candidates


    p = _plan_with_candidates(_HUMAN_GENE,
                              selected=["genetic_hub", "membrane_system"],
                              module_support=ms)
    assert "membrane_system" not in p["secondary"]
    assert "membrane_system" not in [e["module"] for e in p["entries"]]
    assert all(s in candidates for s in p["secondary"])
