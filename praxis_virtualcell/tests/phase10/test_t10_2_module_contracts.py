import hashlib
import json as _json
from types import SimpleNamespace

import pytest

from praxis_virtualcell.agents.model_applicability import ModelApplicabilityAgent
from praxis_virtualcell.agents.request_adapter import request_to_module_input
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.core.exceptions import PraxisVCError, UnsupportedEngine
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.predictors.case_dispatch import dispatch_runner, map_case_delta
from praxis_virtualcell.predictors.case_runner_agent import CaseRunnerPredictorAgent
from praxis_virtualcell.workflows.run_virtualcell_query import run_query


def test_unsupported_engine_is_praxisvc_error():
    assert issubclass(UnsupportedEngine, PraxisVCError)


def test_request_to_module_input_maps_keys():
    req = {"species": "bacteria", "perturbation_type": "gene",
           "perturbation_targets": ["b0720"], "output_modality": "growth"}
    raw = request_to_module_input(req)
    assert raw["species"] == "bacteria"
    assert raw["perturbation_object"] == "gene"      # perturbation_type → perturbation_object
    assert raw["target_output"] == "growth"          # output_modality → target_output
    assert raw["perturbation_targets"] == ["b0720"]


def test_request_to_module_input_default_expression():
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "output_modality": "delta_expression"}
    assert request_to_module_input(req)["target_output"] == "expression"


def test_dispatch_runner_gem_fba_bacteria():
    raw = {"species": "bacteria", "perturbation_object": "gene"}
    from praxis_virtualcell.predictors.mechanistic.ecoli_gem import run_ecoli_growth_case
    assert dispatch_runner("gem_fba", raw) is run_ecoli_growth_case


def test_dispatch_runner_gem_fba_yeast():
    raw = {"species": "yeast", "perturbation_object": "gene"}
    from praxis_virtualcell.predictors.mechanistic.yeast_gem import run_yeast_growth_case
    assert dispatch_runner("gem_fba", raw) is run_yeast_growth_case


def test_dispatch_runner_gem_fba_gene_combination():
    raw = {"species": "bacteria", "perturbation_object": "gene_combination"}
    from praxis_virtualcell.predictors.mechanistic.ecoli_gem import run_ecoli_growth_case
    assert dispatch_runner("gem_fba", raw) is run_ecoli_growth_case


def test_dispatch_runner_unsupported():
    with pytest.raises(UnsupportedEngine):
        dispatch_runner("state_scoring", {"species": "human", "perturbation_object": "gene"})


def test_map_case_delta_gem_fba():
    report = SimpleNamespace(raw_output={"knockouts": [
        {"gene": "b0720", "ratio": 0.0}, {"gene": "x", "ratio": 1.0}, {"gene": "y", "ratio": None}]})
    # ratio-1: essential 0.0→-1.0, 无效应 1.0→0.0, None 跳过
    assert map_case_delta("gem_fba", report) == [-1.0, 0.0]


def test_map_case_delta_unsupported_engine():
    with pytest.raises(UnsupportedEngine):
        map_case_delta("state_scoring", SimpleNamespace(raw_output={"knockouts": []}))


_BACT_GROWTH = {"species": "bacteria", "perturbation_type": "gene",
                "perturbation_targets": ["b0720"], "input_modality": "scRNA",
                "output_modality": "growth", "task_type": "predict_delta_expression"}


def test_case_runner_run_prediction_gem_fba():
    agent = CaseRunnerPredictorAgent()
    out = agent.run_prediction({"request": _BACT_GROWTH})
    assert out["prediction"]["delta"] == [-1.0]         # b0720 essential
    assert out["uncertainty"]["disposition"] == "accept"
    assert out["provenance"]["engine"] == "gem_fba"
    assert out["provenance"]["tool"] == "cobrapy"
    assert out["provenance"]["case_id"]


def test_case_runner_assess_applicability_reject_unsupported():
    agent = CaseRunnerPredictorAgent()
    # human gene expression → route donor_predictor(非真实 engine)→ dispatch UnsupportedEngine → reject
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    score, reject = agent.assess_applicability(req, {})
    assert reject is not None and score == 0.0


def _run_applicability(req):
    bus = MessageBus()
    bus.set_context(trace_id="t", task_id="t")
    agent = ModelApplicabilityAgent()
    msg = AgentMessage("m1", "SpeciesBrain", "ModelApplicability", "decide",
                       {"request": req, "brain_context": {"species": req["species"]}}, "t0001")
    agent.handle(msg, bus)
    return bus.latest("applicability_decided").payload


def test_applicability_gem_fba_routes_to_case_runner():
    out = _run_applicability(_BACT_GROWTH)
    assert out["applicable"] == ["CaseRunner"]
    assert out["rejected_candidates"] == []
    assert out["brain_context"]["routing"]["real_engine"] == "gem_fba"


def test_applicability_donor_predictor_keeps_mock_enumeration():
    # human AHR gene→expression: route donor_predictor(非真实 engine)→ 走现状 mock 枚举
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    out = _run_applicability(req)
    assert "CaseRunner" not in out["applicable"]
    assert set(out["rejected_candidates"]) <= {"MockLinear", "MockCPA", "MockGEARS"}
    assert "real_engine" not in out["brain_context"].get("routing", {})


def test_applicability_boundary_request_falls_back_to_mock():
    # 空 perturbation_targets → normalize_request 抛 SchemaError → engine 判不出 → 落回 mock 枚举(不崩)
    req = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": [],
           "input_modality": "scRNA", "output_modality": "growth",
           "task_type": "predict_delta_expression"}
    out = _run_applicability(req)
    assert "CaseRunner" not in out["applicable"]
    assert "real_engine" not in out["brain_context"].get("routing", {})


_CFG = RuntimeConfig(mode=Mode.OFFLINE)


def test_bacteria_growth_runs_real_fba_end_to_end():
    out = run_query(dict(_BACT_GROWTH), config=_CFG)
    rd = out["reliability_decision"]
    assert rd["abstain"] is False                        # 接入真实 GEM → 不再 abstain
    sr = out["structured_report"]
    assert "CaseRunner" in sr["provenance"]["models_used"]
    assert out["llm_used_for_prediction"] is False       # 仍零 LLM
    # 真实预测:b0720 essential → delta [-1.0]
    assert sr["prediction"]["delta"] == [-1.0]


def _canon(obj):
    return hashlib.sha256(_json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def test_real_request_rerun_byte_equal():
    outs = [run_query(dict(_BACT_GROWTH), config=_CFG) for _ in range(3)]
    assert len({_canon(o["structured_report"]) for o in outs}) == 1
    assert len({_canon(o["trace"]) for o in outs}) == 1


def test_mock_request_unchanged_by_adapter():
    # AHR(donor_predictor)仍走 3 mock,models_used 不含 CaseRunner
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    used = out["structured_report"]["provenance"]["models_used"]
    assert "CaseRunner" not in used                       # mock 请求不碰 adapter


def test_gem_fba_provenance_honest():
    out = run_query(dict(_BACT_GROWTH), config=_CFG)
    prov = out["structured_report"]["provenance"]
    # 真实预测 provenance 可追溯:采纳 CaseRunner
    assert "CaseRunner" in prov["models_used"]
    # 判别性:module_plan 记录真实 gem_fba 引擎(区分于 mock 路径的 donor_predictor)
    assert prov["module_plan"]["entries"][0]["engine"] == "gem_fba"
    # provenance 完整性:加载的 species 规则来源(yaml 文件路径列表)非空
    assert prov["rules_referenced"]


def test_yeast_growth_also_real_fba():
    req = {"species": "yeast", "perturbation_type": "gene", "perturbation_targets": ["YBR166C"],
           "input_modality": "scRNA", "output_modality": "growth",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    assert out["reliability_decision"]["abstain"] is False
    assert "CaseRunner" in out["structured_report"]["provenance"]["models_used"]


def test_all_targets_not_in_gem_abstains_honestly():
    # 全部基因不在 GEM → 机制 disposition=abstain → 主链如实 abstain(不再 abstain=False+prediction=None)
    req = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b9999"],
           "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    assert out["reliability_decision"]["abstain"] is True
    sr = out["structured_report"]
    assert sr["prediction"] is None
    assert "CaseRunner" not in sr["provenance"]["models_used"]
    assert "CaseRunner" in sr["provenance"]["models_rejected"]
    assert sr["provenance"]["model_cautions"]["CaseRunner"] == ["all_targets_not_in_gem"]


def test_partial_targets_surface_caution():
    # 部分基因不在 GEM → disposition=caution → 给出 partial 预测,但 caution 如实透出(不静默吞)
    req = {"species": "bacteria", "perturbation_type": "gene_combination",
           "perturbation_targets": ["b0720", "b9999"],
           "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    assert out["reliability_decision"]["abstain"] is False
    assert out["structured_report"]["prediction"]["delta"] == [-1.0]   # partial 预测仍在
    prov = out["structured_report"]["provenance"]
    mc = prov["model_cautions"]
    assert "CaseRunner" in mc
    assert any("targets_not_in_gem" in f for f in mc["CaseRunner"])


def test_markdown_surfaces_gem_abstain_reason():
    from praxis_virtualcell.io.report_markdown import render_report_md
    req = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b9999"],
           "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    md = render_report_md({"mode": "offline", "request": req, "report": out["structured_report"]})
    assert "all_targets_not_in_gem" in md          # 拒因如实出现在人读报告
    assert "CaseRunner` — 未记录原因" not in md      # 不再误导


def test_dispatch_runner_gem_fba_medium():
    from praxis_virtualcell.predictors.mechanistic.medium_shift import run_medium_shift_case
    raw = {"species": "bacteria", "perturbation_object": "medium"}
    assert dispatch_runner("gem_fba", raw) is run_medium_shift_case


def test_dispatch_runner_gem_fba_medium_yeast_unsupported():
    # 无 yeast medium runner → 诚实抛 UnsupportedEngine(会被 CaseRunner 转 abstain)
    with pytest.raises(UnsupportedEngine):
        dispatch_runner("gem_fba", {"species": "yeast", "perturbation_object": "medium"})


def test_map_case_delta_gem_fba_medium():
    report = SimpleNamespace(raw_output={"reference": "glucose minimal", "glucose_growth": 0.87392,
        "carbon_sources": [{"carbon": "acetate", "in_model": True, "ratio_vs_glucose": 0.1983},
                           {"carbon": "unobtainium", "in_model": False, "ratio_vs_glucose": None}]})
    assert map_case_delta("gem_fba", report) == [-0.8017]   # 不在模型的碳源跳过


def test_dispatch_runner_gem_fba_drug():
    from praxis_virtualcell.predictors.mechanistic.antibiotic import run_antibiotic_case
    raw = {"species": "bacteria", "perturbation_object": "drug"}
    assert dispatch_runner("gem_fba", raw) is run_antibiotic_case


def test_map_case_delta_gem_fba_drug():
    report = SimpleNamespace(raw_output={"wt_growth": 0.877, "antibiotics": [
        {"antibiotic": "trimethoprim", "target_rxn": "DHFR", "in_model": True, "ratio_vs_wt": 0.0},
        {"antibiotic": "ampicillin", "target_rxn": "non-metabolic", "known": True, "in_model": False}]})
    # in_model 且有 ratio_vs_wt 的项:ratio-1;非代谢/未知项跳过
    assert map_case_delta("gem_fba", report) == [-1.0]


def test_pathway_scoring_in_real_engines():
    from praxis_virtualcell.predictors.case_dispatch import REAL_ENGINES
    assert "pathway_scoring" in REAL_ENGINES


def test_dispatch_runner_pathway_scoring_ifn():
    from praxis_virtualcell.predictors.state.metabolic_tendency import run_metabolic_tendency_case
    raw = {"species": "human", "perturbation_object": "ligand", "perturbation_targets": ["IFNB1"]}
    assert dispatch_runner("pathway_scoring", raw) is run_metabolic_tendency_case


def test_dispatch_runner_pathway_scoring_non_ifn_unsupported():
    # 非 IFN-β 哺乳类 flux(如 TP53 基因)→ 无基因特异代谢模型 → 诚实 UnsupportedEngine
    with pytest.raises(UnsupportedEngine):
        dispatch_runner("pathway_scoring", {"species": "human", "perturbation_object": "gene",
                                            "perturbation_targets": ["TP53"]})


def test_map_case_delta_pathway_scoring():
    report = SimpleNamespace(raw_output={"max_abs_cohens_d": 0.281, "pathway_shifts": [
        {"panel": "glycolysis", "cohens_d": 0.101}, {"panel": "oxphos", "cohens_d": 0.281}]})
    assert map_case_delta("pathway_scoring", report) == [0.101, 0.281]


def test_human_ifn_flux_real_pathway_scoring():
    req = {"species": "human", "perturbation_type": "ligand", "perturbation_targets": ["IFNB1"],
           "input_modality": "scRNA", "output_modality": "flux", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is False
    assert "CaseRunner" in sr["provenance"]["models_used"]
    assert sr["prediction"]["delta"] == [0.101, 0.281]
    assert any("weak_pathway_effect" in f for f in sr["provenance"]["model_cautions"]["CaseRunner"])


def test_human_gene_flux_non_ifn_abstains_honestly():
    # 任意哺乳类基因 flux(非 IFN-β)→ 无基因特异代谢模型 → 诚实 abstain,不再返回固定 IFN 数值
    for sp, tg in (("human", ["TP53"]), ("mouse", ["Tp53"])):
        req = {"species": sp, "perturbation_type": "gene", "perturbation_targets": tg,
               "input_modality": "scRNA", "output_modality": "flux", "task_type": "predict_delta_expression"}
        out = run_query(dict(req), config=_CFG)
        assert out["reliability_decision"]["abstain"] is True
        assert out["structured_report"]["prediction"] is None
        assert "CaseRunner" in out["structured_report"]["provenance"]["models_rejected"]


def test_bacteria_medium_shift_real_fba():
    req = {"species": "bacteria", "perturbation_type": "medium", "perturbation_targets": ["acetate"],
           "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is False
    assert "CaseRunner" in sr["provenance"]["models_used"]
    assert sr["prediction"]["delta"] == [-0.8017]        # 乙酸 0.1983×葡萄糖 → 真实 FBA


def test_bacteria_antibiotic_real_fba():
    req = {"species": "bacteria", "perturbation_type": "drug", "perturbation_targets": ["trimethoprim"],
           "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is False
    assert sr["prediction"]["delta"] == [-1.0]            # DHFR 抑制 growth 0


def test_bacteria_antibiotic_non_metabolic_abstains():
    # 非代谢靶(ampicillin)→ 机制 abstain → 主链如实弃权 + 原因透出
    req = {"species": "bacteria", "perturbation_type": "drug", "perturbation_targets": ["ampicillin"],
           "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is True
    assert sr["prediction"] is None
    assert "CaseRunner" in sr["provenance"]["models_rejected"]
    assert any("non_metabolic_target" in f for f in sr["provenance"]["model_cautions"]["CaseRunner"])


def test_b2_real_requests_rerun_byte_equal():
    # 三条 B2 真实请求各重跑 3 次,structured_report 与 trace 字节稳(确定性红线)
    for req in (
        {"species": "bacteria", "perturbation_type": "medium", "perturbation_targets": ["acetate"],
         "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"},
        {"species": "bacteria", "perturbation_type": "drug", "perturbation_targets": ["trimethoprim"],
         "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"},
        {"species": "human", "perturbation_type": "ligand", "perturbation_targets": ["IFNB1"],
         "input_modality": "scRNA", "output_modality": "flux", "task_type": "predict_delta_expression"}):
        outs = [run_query(dict(req), config=_CFG) for _ in range(3)]
        assert len({_canon(o["structured_report"]) for o in outs}) == 1
        assert len({_canon(o["trace"]) for o in outs}) == 1


def test_b2_mock_expression_request_unchanged():
    # B2 加了 gem_fba medium/drug + pathway_scoring 引擎;确认它们不泄漏到 expression/mock 路径:
    # human gene→delta_expression 仍只走 donor_predictor 的 3 个 mock,无任何真实 CaseRunner 接管。
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    used = out["structured_report"]["provenance"]["models_used"]
    assert "CaseRunner" not in used
    assert set(used) <= {"MockLinear", "MockCPA", "MockGEARS"}   # 只 mock,B2 引擎零泄漏


def test_dispatch_runner_pathway_scoring_mouse_unsupported():
    # metabolic_tendency 是 human Kang IFN-β 数据 → mouse 即便 IFN-β 也无对应数据 → 诚实 UnsupportedEngine
    with pytest.raises(UnsupportedEngine):
        dispatch_runner("pathway_scoring", {"species": "mouse", "perturbation_object": "ligand",
                                            "perturbation_targets": ["IFNB1"]})


def test_dispatch_runner_pathway_scoring_non_beta_ifn_unsupported():
    # IFN-γ/α 不是 IFN-β(Kang 数据专指 β)→ 诚实 UnsupportedEngine
    for tg in (["interferon gamma"], ["interferon alpha"]):
        with pytest.raises(UnsupportedEngine):
            dispatch_runner("pathway_scoring", {"species": "human", "perturbation_object": "ligand",
                                                "perturbation_targets": tg})


def test_pathway_scoring_species_cytokine_leak_abstains_e2e():
    # 端到端:mouse+IFN-β 与 human+IFN-γ 都不应拿到人类 IFN-β 固定数据,应诚实 abstain
    for sp, tg in (("mouse", ["IFNB1"]), ("human", ["interferon gamma"])):
        req = {"species": sp, "perturbation_type": "ligand", "perturbation_targets": tg,
               "input_modality": "scRNA", "output_modality": "flux", "task_type": "predict_delta_expression"}
        out = run_query(dict(req), config=_CFG)
        assert out["reliability_decision"]["abstain"] is True
        assert out["structured_report"]["prediction"] is None
        assert "CaseRunner" in out["structured_report"]["provenance"]["models_rejected"]


def test_dispatch_runner_pathway_scoring_ifnb2_il6_unsupported():
    # IFNB2 是 IL-6 历史别名(非 IFN-β)→ 精确匹配下不放行,诚实 UnsupportedEngine
    with pytest.raises(UnsupportedEngine):
        dispatch_runner("pathway_scoring", {"species": "human", "perturbation_object": "ligand",
                                            "perturbation_targets": ["IFNB2"]})


def test_pathway_engines_include_embedding():
    from praxis_virtualcell.predictors.case_dispatch import REAL_ENGINES
    assert "embedding" in REAL_ENGINES


def test_dispatch_runner_embedding_signature():
    from praxis_virtualcell.predictors.embedding.drug_signature import run_drug_response_case
    raw = {"species": "human", "perturbation_object": "drug"}
    assert dispatch_runner("embedding", raw) is run_drug_response_case


def test_dispatch_runner_embedding_mouse_unsupported():
    with pytest.raises(UnsupportedEngine):
        dispatch_runner("embedding", {"species": "mouse", "perturbation_object": "drug"})


def test_map_case_delta_embedding_signature():
    report = SimpleNamespace(raw_output={"enrichment_threshold": 1.5, "per_drug": [
        {"drug": "geldanamycin", "in_db": True, "moa_enrichment": 2.646},
        {"drug": "notadrug", "in_db": False, "moa_enrichment": None}]})
    assert map_case_delta("embedding", report) == [2.646]
