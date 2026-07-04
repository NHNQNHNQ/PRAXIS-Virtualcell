"""Phase 4:ModuleRouter 读 LLM 候选(决策 P1/P2)。
铁律:primary 永由确定性规则定(LLM 不改);LLM 只增删 secondary 且 ⊆ candidates;
engine/verdict 仍由 route()+synthesize 定(LLM 无法把 downgrade 改 accept)。"""
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
    # module_support 默认沿用 SpeciesContext;传入则覆写(用于构造"某模块 unsupported"场景)
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
    """决策 P1:LLM selected 不含 primary,primary 仍由确定性规则定(LLM 不改 primary)。"""
    p = _plan_with_candidates(_HUMAN_GENE, selected=["stress_processor"])
    assert p["primary"] == "genetic_hub"      # 确定性 primary,LLM 没选也保留
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["module"] == "genetic_hub"


def test_llm_adds_secondary_from_selection():
    """决策 P2:LLM 选了合法 secondary(stress_processor)→ 进 plan secondary。"""
    p = _plan_with_candidates(_HUMAN_GENE, selected=["genetic_hub", "stress_processor"])
    assert "stress_processor" in p["secondary"]


def test_llm_cannot_change_verdict_to_accept():
    """红线:LLM 选了某 module,但其 route/species 若是 caution/abstain,verdict 仍不 accept。
    bacteria gene→expression primary=genetic_hub 是 abstain,LLM 选它也改不成 accept。"""
    p = _plan_with_candidates(
        {"species": "bacteria", "perturbation_object": "gene",
         "target_output": "expression", "perturbation_targets": ["b0720"]},
        selected=["genetic_hub"])
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["verdict"] != "accept"        # LLM 无法把 abstain 捞成 accept


def test_offline_path_unchanged_without_candidates():
    """无 module_candidates(OFFLINE)→ 走 Phase 3 原路径(secondary 由 pick_secondary)。"""
    ctx = _ctx({"species": "human", "perturbation_object": "gene",
                "target_output": "growth", "perturbation_targets": ["MYC"]})
    bus = MessageBus()
    ModuleRouterAgent().handle(AgentMessage(
        message_id="c2", sender="SpeciesContextAgent", receiver="ModuleRouterAgent",
        message_type="module_route",
        payload={"request": {"species": "human", "perturbation_object": "gene",
                             "target_output": "growth", "perturbation_targets": ["MYC"]},
                 "module_support": ctx["module_support"],
                 "mismatch_queries": ctx["mismatch_queries"]},  # 无 module_candidates
        timestamp="t2"), bus)
    p = bus.latest("module_plan_ready").payload
    assert "mitochondrial_energy_metabolism" in p["secondary"]   # Phase 3 确定性 secondary


def test_llm_risk_flags_surfaced_in_notes():
    """LLM 失败标记(llm_unavailable)透传进 plan notes(可追溯)。"""
    p = _plan_with_candidates(_HUMAN_GENE, selected=["genetic_hub"],
                              risk_flags=["llm_unavailable"])
    assert any("llm_unavailable" in n for n in p["notes"])


def test_llm_out_of_candidate_secondary_dropped():
    """决策 P2:LLM selected 里越候选的合法 module 被剔出 secondary(secondary 必 ⊆ candidates)。
    构造真正越候选但合法的 module:membrane_system ∈ MODULE_ORDER(合法名,过 ModulePlanEntry 白名单),
    但把 human 的 membrane_system 覆写成 support=unsupported 后,它既非确定性 primary(genetic_hub)
    也非确定性 secondary([]),故 ∉ build_candidate_modules(req, module_support)。LLM 选它 → 必被 P2 剔除。
    """
    from praxis_virtualcell.biological_modules import modules as M
    from praxis_virtualcell.llm_orchestration import safety_contract as SC
    from praxis_virtualcell.agents.species_schema import normalize_request

    ctx = _ctx(_HUMAN_GENE)
    # 覆写 membrane_system → unsupported(它就此掉出 candidate 全集,但仍是合法 module 名)
    ms = {mid: dict(rec) for mid, rec in ctx["module_support"].items()}
    ms["membrane_system"]["support"] = "unsupported"
    ms["membrane_system"]["verdict"] = "reject"

    # 前置核实:越候选 module ∈ MODULE_ORDER(合法),但 ∉ 该 module_support 下的候选全集
    req = normalize_request(_HUMAN_GENE)
    candidates = SC.build_candidate_modules(req, ms)
    assert "membrane_system" in M.MODULE_ORDER          # 合法 module 名(不会被白名单拒)
    assert "membrane_system" not in candidates          # 真正越候选(unsupported 且非确定性 primary/secondary)

    # LLM 越候选选了 membrane_system → 必被 P2(and m in candidates)剔出 secondary
    p = _plan_with_candidates(_HUMAN_GENE,
                              selected=["genetic_hub", "membrane_system"],
                              module_support=ms)
    assert "membrane_system" not in p["secondary"]      # 越候选合法 module 被剔(真守卫 P2)
    assert "membrane_system" not in [e["module"] for e in p["entries"]]
    assert all(s in candidates for s in p["secondary"])  # secondary 必 ⊆ candidates
