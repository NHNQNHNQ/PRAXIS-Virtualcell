"""Tests for module router agent."""
from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _plan_for(request):
    """Test helper: plan for."""
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


def _req(**kw):
    base = {"species": "human", "perturbation_object": "gene",
            "target_output": "expression", "perturbation_targets": ["AHR"]}
    base.update(kw)
    return base


def test_human_gene_expression_plan():
    p = _plan_for(_req())
    assert p["primary"] == "genetic_hub"
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["engine"] == "donor_predictor"
    assert prim["route_disposition"] == "accept"
    assert prim["species_verdict"] == "accept"
    assert prim["verdict"] == "accept"
    assert p["overall_verdict"] == "accept"


def test_mouse_gene_expression_is_caution():
    """Verify mouse gene expression is caution."""
    p = _plan_for(_req(species="mouse", perturbation_targets=["Gata1"]))
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["verdict"] == "caution"
    assert "ortholog_required" in prim["caution_flags"]


def test_bacteria_growth_gem_accept():
    p = _plan_for(_req(species="bacteria", target_output="growth",
                       perturbation_targets=["b0720"]))
    assert p["primary"] == "cytoplasmic_metabolism"
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["engine"] == "gem_fba"
    assert prim["verdict"] == "accept"


def test_bacteria_expression_gene_is_abstain_reject():
    """Verify bacteria expression gene is abstain reject."""
    p = _plan_for(_req(species="bacteria", target_output="expression",
                       perturbation_targets=["b0720"]))
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["route_disposition"] == "abstain"
    assert prim["verdict"] in ("abstain", "reject", "caution")
    assert prim["verdict"] != "accept"


def test_yeast_niche_mismatch_downgrades():
    """Verify yeast niche mismatch downgrades."""
    p = _plan_for(_req(species="yeast", perturbation_object="medium",
                       target_output="state", medium="niche",
                       perturbation_targets=["SNF1"]))

    assert p["primary"] == "cytoskeletal_framework"
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["module"] == "cytoskeletal_framework"

    assert prim["mismatch"] == "reject"
    assert prim["verdict"] != "accept"
    assert prim["verdict"] == "abstain"
    assert p["overall_verdict"] != "accept"
    assert p["overall_verdict"] == "abstain"


def test_bus_message_structure_and_no_llm():
    p = _plan_for(_req())

    assert set(p) >= {"species", "request", "primary", "secondary",
                      "overall_verdict", "entries", "notes"}
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert set(prim) >= {"module", "engine", "verdict", "pillars", "reason"}


def test_mammalian_growth_has_m3_secondary_entry():
    p = _plan_for(_req(species="human", target_output="growth",
                       perturbation_targets=["MYC"]))
    assert "mitochondrial_energy_metabolism" in p["secondary"]
    sec_modules = {e["module"] for e in p["entries"] if e["role"] == "secondary"}
    assert "mitochondrial_energy_metabolism" in sec_modules
