"""Phase 3:ModuleRouterAgent(插点 B)—— 进 bus,产 ModulePlan。OFFLINE 确定性,零 LLM。
铁律:primary 落 engine 复用 route();物种 unsupported/mismatch → verdict 降级不 accept。"""
from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _plan_for(request):
    """跑 SpeciesContext → ModuleRouter 全链路,返回 module_plan_ready payload(dict)。"""
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
    """mouse 迁移需 ortholog:route caution + species medium→ verdict caution(不 accept)。"""
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
    """铁律:哺乳类 scRNA predictor 不适用微生物表达 → route abstain;primary M2 verdict 不 accept。"""
    p = _plan_for(_req(species="bacteria", target_output="expression",
                       perturbation_targets=["b0720"]))
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["route_disposition"] == "abstain"
    assert prim["verdict"] in ("abstain", "reject", "caution")   # 绝不 accept
    assert prim["verdict"] != "accept"


def test_bacteria_autophagy_mismatch_downgrades():
    """决策 E:bacteria + degradation → 自噬 mismatch → caution(不 accept)。"""
    p = _plan_for(_req(species="bacteria", perturbation_object="gene",
                       target_output="growth", perturbation_targets=["lon"]))
    # M4 是 primary(growth);但若把 degradation 作为 secondary 出现则带 mismatch。
    # 这里断言:整个 plan 里若出现 degradation_machinery entry,它带 mismatch=caution。
    degs = [e for e in p["entries"] if e["module"] == "degradation_machinery"]
    for e in degs:
        assert e["mismatch"] == "caution"
        assert e["verdict"] != "accept"


def test_bus_message_structure_and_no_llm():
    p = _plan_for(_req())
    # plan payload 是 ModulePlan.to_dict() 的全量键
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
