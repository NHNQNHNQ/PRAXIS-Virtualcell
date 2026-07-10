import hashlib
import json as _json
from types import SimpleNamespace

import pytest

from praxis_virtualcell.agents import module_rules as MR
from praxis_virtualcell.agents.model_applicability import ModelApplicabilityAgent
from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.request_adapter import request_to_module_input
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.agents.species_schema import normalize_request as _norm
from praxis_virtualcell.biological_modules import module_gene_sets as MGS
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


def test_dispatch_runner_embedding_ligand_unsupported():
    # route 把 ligand 也判 embedding(data_gated 未接模型)→ 不当 drug 查库 → 诚实 UnsupportedEngine
    with pytest.raises(UnsupportedEngine):
        dispatch_runner("embedding", {"species": "human", "perturbation_object": "ligand"})


def test_human_ligand_not_mislabeled_as_drug():
    req = {"species": "human", "perturbation_type": "ligand", "perturbation_targets": ["TGFB1"],
           "input_modality": "scRNA", "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    prov = out["structured_report"]["provenance"]
    # ligand 无签名模型 → 诚实 abstain,但不能被误标成"药不在库"(TGFB1 是配体不是药)
    mc = prov.get("model_cautions", {})
    assert not any("drug_not_in_db" in f for f in mc.get("CaseRunner", []))


def test_dispatch_runner_embedding_dose():
    from praxis_virtualcell.predictors.embedding.drug_dose import run_drug_dose_case
    raw = {"species": "human", "perturbation_object": "drug", "perturbation_dose": 10.0}
    assert dispatch_runner("embedding", raw) is run_drug_dose_case


def test_dispatch_runner_embedding_no_dose_is_signature():
    from praxis_virtualcell.predictors.embedding.drug_signature import run_drug_response_case
    raw = {"species": "human", "perturbation_object": "drug"}
    assert dispatch_runner("embedding", raw) is run_drug_response_case


def test_map_case_delta_embedding_dose():
    report = SimpleNamespace(raw_output={"drug": "geldanamycin", "dose_response": {
        "n_doses": 6, "spearman": 0.9, "recalls": [0.04, 0.06], "insufficient": False}})
    assert map_case_delta("embedding", report) == [0.9]


def test_map_case_delta_embedding_dose_not_in_db():
    # 药在签名库但不在剂量库 → drug_dose 设 dose_response=None → 空 delta(不崩)
    report = SimpleNamespace(raw_output={"drug": "wortmannin", "dose_response": None})
    assert map_case_delta("embedding", report) == []


def test_human_drug_dose_real_e2e():
    # 带 perturbation_dose → 剂量-响应意图 → drug_dose 真实(geldanamycin spearman=0.9)
    req = {"species": "human", "perturbation_type": "drug", "perturbation_targets": ["geldanamycin"],
           "perturbation_dose": 10.0, "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is False
    assert "CaseRunner" in sr["provenance"]["models_used"]
    assert sr["prediction"]["delta"] == [0.9]


def test_human_drug_dose_not_in_db_abstains_honestly():
    # wortmannin 在签名库、不在剂量库;带 perturbation_dose → drug_dose → 诚实 abstain(不崩)
    req = {"species": "human", "perturbation_type": "drug", "perturbation_targets": ["wortmannin"],
           "perturbation_dose": 10.0, "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    assert out["reliability_decision"]["abstain"] is True
    assert out["structured_report"]["prediction"] is None
    assert "CaseRunner" in out["structured_report"]["provenance"]["models_rejected"]


def test_pathway_engines_include_state_scoring():
    from praxis_virtualcell.predictors.case_dispatch import REAL_ENGINES
    assert "state_scoring" in REAL_ENGINES


def test_dispatch_runner_state_scoring_ifn():
    from praxis_virtualcell.predictors.state.cell_state import run_cellstate_case
    raw = {"species": "human", "perturbation_object": "ligand", "perturbation_targets": ["IFNB1"]}
    assert dispatch_runner("state_scoring", raw) is run_cellstate_case


def test_dispatch_runner_state_scoring_non_ifn_unsupported():
    # cell_state 是固定 Kang IFN-β 数据 → 非 IFN-β(emt 的 ZEB1)/mouse(fate)诚实 UnsupportedEngine
    for raw in ({"species": "human", "perturbation_object": "gene", "perturbation_targets": ["ZEB1"]},
                {"species": "mouse", "perturbation_object": "gene", "perturbation_targets": ["Gata1"]}):
        with pytest.raises(UnsupportedEngine):
            dispatch_runner("state_scoring", raw)


def test_map_case_delta_state_scoring():
    report = SimpleNamespace(raw_output={"cohens_d": 2.485, "marker_coverage": 1.0,
        "per_cell_type": [{"cell_type": "B cells", "cohens_d": 3.472}]})
    assert map_case_delta("state_scoring", report) == [2.485]


def test_human_drug_signature_real_e2e():
    req = {"species": "human", "perturbation_type": "drug", "perturbation_targets": ["geldanamycin"],
           "input_modality": "scRNA", "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is False
    assert "CaseRunner" in sr["provenance"]["models_used"]
    assert sr["prediction"]["delta"] == [2.646]          # HSP90i MOA 富集


def test_human_ifn_cellstate_real_e2e():
    req = {"species": "human", "perturbation_type": "ligand", "perturbation_targets": ["IFNB1"],
           "input_modality": "scRNA", "output_modality": "state", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is False
    assert "CaseRunner" in sr["provenance"]["models_used"]
    assert sr["prediction"]["delta"] == [2.485]          # ISG 组间 Cohen's d


def test_stress_limitation_paths_abstain_honestly():
    # emt(human gene ZEB1→state,状态刻画非扰动)、fate(mouse gene Gata1→state)、mouse+drug(物种守卫)
    # → 均经 CaseRunner 诚实 abstain,不虚构固定数据(类别错误/无数据)
    cases = [
        {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["ZEB1"],
         "output_modality": "state"},
        {"species": "mouse", "perturbation_type": "gene", "perturbation_targets": ["Gata1"],
         "output_modality": "state"},
        {"species": "mouse", "perturbation_type": "drug", "perturbation_targets": ["geldanamycin"],
         "output_modality": "delta_expression"},
    ]
    for c in cases:
        req = {**c, "input_modality": "scRNA", "task_type": "predict_delta_expression"}
        out = run_query(dict(req), config=_CFG)
        assert out["reliability_decision"]["abstain"] is True, c
        assert out["structured_report"]["prediction"] is None, c
        assert "CaseRunner" in out["structured_report"]["provenance"]["models_rejected"], c


def test_b3_real_requests_rerun_byte_equal():
    # B3 真实请求各重跑 3 次,structured_report 与 trace 字节稳(确定性红线)
    for req in (
        {"species": "human", "perturbation_type": "drug", "perturbation_targets": ["geldanamycin"],
         "input_modality": "scRNA", "output_modality": "delta_expression", "task_type": "predict_delta_expression"},
        {"species": "human", "perturbation_type": "drug", "perturbation_targets": ["geldanamycin"],
         "perturbation_dose": 10.0, "input_modality": "scRNA", "output_modality": "delta_expression",
         "task_type": "predict_delta_expression"},
        {"species": "human", "perturbation_type": "ligand", "perturbation_targets": ["IFNB1"],
         "input_modality": "scRNA", "output_modality": "state", "task_type": "predict_delta_expression"}):
        outs = [run_query(dict(req), config=_CFG) for _ in range(3)]
        assert len({_canon(o["structured_report"]) for o in outs}) == 1
        assert len({_canon(o["trace"]) for o in outs}) == 1


def test_b3_mock_expression_gene_unchanged():
    # human gene→delta_expression 仍只走 donor_predictor 3 mock
    # (embedding/state_scoring 只吃 drug/state,不碰 gene expression)
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    used = out["structured_report"]["provenance"]["models_used"]
    assert "CaseRunner" not in used
    assert set(used) <= {"MockLinear", "MockCPA", "MockGEARS"}   # 只 mock,B3 引擎零泄漏到 gene expression


def test_is_ifn_beta_mixed_targets_unsupported():
    # 混合含非 IFN-β target → 固定 IFN-β 数据无法建模组合 → 诚实 UnsupportedEngine(两个引擎都收紧)
    with pytest.raises(UnsupportedEngine):
        dispatch_runner("state_scoring", {"species": "human", "perturbation_object": "gene",
                                          "perturbation_targets": ["IFNB1", "ZEB1"]})
    with pytest.raises(UnsupportedEngine):
        dispatch_runner("pathway_scoring", {"species": "human", "perturbation_object": "gene",
                                            "perturbation_targets": ["IFNB1", "TP53"]})


def test_mixed_ifn_target_abstains_e2e():
    # 端到端:human [IFNB1,ZEB1] state 不再拿只覆盖一半的 [2.485],而是诚实 abstain
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["IFNB1", "ZEB1"],
           "input_modality": "scRNA", "output_modality": "state", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    assert out["reliability_decision"]["abstain"] is True
    assert out["structured_report"]["prediction"] is None
    assert "CaseRunner" in out["structured_report"]["provenance"]["models_rejected"]


# ==================== P10.B4:M1/M5/M8 rule-based advisory ====================
def test_b4_gene_set_of_membrane_has_real_symbols():
    gs = MGS.gene_set_of("membrane_system")
    assert isinstance(gs, frozenset)
    assert {"SLC2A1", "FASN", "SREBF1"} <= gs
    # 非 gene-set 模块 → 空集(不崩)
    assert MGS.gene_set_of("genetic_hub") == frozenset()


def test_b4_modules_hit_by_single_hits():
    assert MGS.modules_hit_by(["SLC2A1"]) == ["membrane_system"]
    assert MGS.modules_hit_by(["RPS6"]) == ["biosynthetic_network"]
    assert MGS.modules_hit_by(["PSMB5"]) == ["degradation_machinery"]


def test_b4_modules_hit_by_mixed_hit_and_miss():
    # TP53 不在任何 gene-set → 只命中 degradation
    assert MGS.modules_hit_by(["PSMB5", "TP53"]) == ["degradation_machinery"]
    assert MGS.modules_hit_by(["TP53"]) == []


def test_b4_modules_hit_by_exact_match_no_substring():
    assert MGS.modules_hit_by(["slc2a1"]) == ["membrane_system"]   # 大小写归一
    assert MGS.modules_hit_by(["SLC2A"]) == []                     # 子串不误命中
    assert MGS.modules_hit_by(["XSLC2A1"]) == []                   # 前缀污染不误命中


def test_b4_modules_hit_by_multi_ordered_by_module_order():
    hits = MGS.modules_hit_by(["PSMB5", "SLC2A1", "RPS6"])
    assert hits == ["membrane_system", "biosynthetic_network", "degradation_machinery"]


def test_b4_gene_set_deterministic():
    assert MGS.gene_set_of("membrane_system") == MGS.gene_set_of("membrane_system")
    assert MGS.modules_hit_by(["SLC2A1"]) == MGS.modules_hit_by(["SLC2A1"])


def test_b4_modules_hit_by_empty_and_none():
    assert MGS.modules_hit_by([]) == []
    assert MGS.modules_hit_by(None) == []
    assert MGS.modules_hit_by(["", "  "]) == []


def _b4_norm_req(**kw):
    base = {"species": "human", "perturbation_object": "gene",
            "target_output": "expression", "perturbation_targets": ["SLC2A1"]}
    base.update(kw)
    return _norm(base)


def test_b4_pick_secondary_membrane_gene_adds_m1():
    sec = MR.pick_secondary(_b4_norm_req(), "genetic_hub")
    assert "membrane_system" in sec


def test_b4_pick_secondary_degradation_gene_adds_m8():
    sec = MR.pick_secondary(_b4_norm_req(perturbation_targets=["PSMB5"]), "genetic_hub")
    assert "degradation_machinery" in sec


def test_b4_pick_secondary_non_hit_gene_adds_nothing():
    sec = MR.pick_secondary(_b4_norm_req(perturbation_targets=["TP53"]), "genetic_hub")
    assert not ({"membrane_system", "biosynthetic_network", "degradation_machinery"} & set(sec))


def test_b4_pick_secondary_excludes_primary_and_dedups():
    # 防御:即便 primary 恰为 gene-set 模块也排除(现状 primary 永不为 M1/M5/M8)
    sec = MR.pick_secondary(_b4_norm_req(), "membrane_system")
    assert "membrane_system" not in sec
    # 去重:结果无重复
    assert len(sec) == len(set(sec))


def test_b4_pick_secondary_preserves_m3_for_mammalian_growth():
    # 现有 M3 逻辑不变:human growth 仍加 M3;若靶标同时命中 gene-set 则并存
    req = _b4_norm_req(target_output="growth", perturbation_targets=["SLC2A1"])
    sec = MR.pick_secondary(req, "cytoplasmic_metabolism")
    assert "mitochondrial_energy_metabolism" in sec   # M3 保留
    assert "membrane_system" in sec                   # gene-set 命中并存
    # 确定性顺序锁定(M3 由代谢规则先入,gene-set 命中随后)
    assert sec == ["mitochondrial_energy_metabolism", "membrane_system"]


def test_b4_pick_secondary_gene_gated_drug_ligand_not_activated():
    # 诚实红线:drug/ligand 请求即便靶标字面撞 gene-set 符号也不激活 M1/M5/M8(非基因扰动)
    for obj in ("drug", "ligand"):
        req = _b4_norm_req(perturbation_object=obj, perturbation_targets=["SLC2A1"])
        assert MR.gene_set_secondary(req) == []
        assert "membrane_system" not in MR.pick_secondary(req, "stress_processor")
    # gene_combination 属基因扰动 → 激活
    req_gc = _b4_norm_req(perturbation_object="gene_combination", perturbation_targets=["SLC2A1"])
    assert "membrane_system" in MR.gene_set_secondary(req_gc)


_B4_RAW_MEMBRANE = {"species": "human", "perturbation_object": "gene",
                    "target_output": "expression", "perturbation_targets": ["SLC2A1"]}


def _b4_plan_for(request):
    """SpeciesContext → ModuleRouter 全链路,返回 module_plan_ready payload(dict)。request 为 raw。"""
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


def test_b4_membrane_entry_carries_rule_based_advisory():
    p = _b4_plan_for(dict(_B4_RAW_MEMBRANE))
    m1 = next(e for e in p["entries"] if e["module"] == "membrane_system")
    assert m1["role"] == "secondary"
    assert m1["route_disposition"] == "downgrade"            # 非 accept(不伪装)、非 reject(不拖 abstain)
    assert m1["species_verdict"] == "caution"                # human membrane weak→caution
    assert m1["verdict"] == "downgrade"                      # synthesize(downgrade,caution,None)=downgrade
    assert "rule_based:membrane_system_gene_set" in m1["caution_flags"]
    assert "evidence_limited" in m1["caution_flags"]
    assert "rule_based_gene_set_advisory" in m1["reason"]


def test_b4_overall_verdict_downgrades_not_abstain():
    p = _b4_plan_for(dict(_B4_RAW_MEMBRANE))
    assert p["overall_verdict"] == "downgrade"               # 不是 abstain/reject
    # primary M2 entry 未被 advisory 污染
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["module"] == "genetic_hub"
    assert prim["verdict"] == "accept"
    assert "rule_based:membrane_system_gene_set" not in prim["caution_flags"]


def test_b4_non_gene_set_gene_no_advisory_entry():
    p = _b4_plan_for(dict(_B4_RAW_MEMBRANE, perturbation_targets=["TP53"]))
    modules = {e["module"] for e in p["entries"]}
    assert not ({"membrane_system", "biosynthetic_network", "degradation_machinery"} & modules)
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["verdict"] == "accept"                       # 非命中基因行为不变


def test_b4_advisory_entry_has_no_numeric_delta_field():
    p = _b4_plan_for(dict(_B4_RAW_MEMBRANE))
    m1 = next(e for e in p["entries"] if e["module"] == "membrane_system")
    # ModulePlanEntry 无任何数值 delta/prediction 字段(定性 advisory,零伪造)
    assert "delta" not in m1
    assert "prediction" not in m1


def test_b4_advisory_never_relaxes_route_abstain():
    # 诚实红线(code review 抓出):advisory 只能变严格,不能比 route() 更乐观。
    # 微生物 gene→expression(route 判 abstain,mammalian scRNA predictor 不适用)+ 命中 gene-set 基因
    # → M1 entry 保持 abstain,不被 advisory 放宽成 downgrade。
    p = _b4_plan_for({"species": "bacteria", "perturbation_object": "gene",
                      "target_output": "expression", "perturbation_targets": ["FASN"]})
    m1 = next(e for e in p["entries"] if e["module"] == "membrane_system")
    assert m1["route_disposition"] == "abstain"   # route() 原判,advisory 不放宽
    assert m1["verdict"] == "abstain"
    # advisory 标注仍如实叠加(rule_based/evidence_limited),只是不放宽 disposition
    assert "rule_based:membrane_system_gene_set" in m1["caution_flags"]
    assert "evidence_limited" in m1["caution_flags"]
    assert p["overall_verdict"] == "abstain"


_B4_RUNQ = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["SLC2A1"],
            "input_modality": "scRNA", "output_modality": "delta_expression",
            "task_type": "predict_delta_expression"}


def test_b4_all_three_modules_runnable_e2e():
    # G2 8/8:M1/M5/M8 各至少一个基因请求经 run_query 进 module_plan 并产 advisory
    # (这些基因在 mock 下会 abstain=OOD,但 module_plan 仍如实带 advisory —— 正是分离的体现)
    for gene, module in [("SLC2A1", "membrane_system"), ("RPS6", "biosynthetic_network"),
                         ("PSMB5", "degradation_machinery")]:
        out = run_query(dict(_B4_RUNQ, perturbation_targets=[gene]), config=_CFG)
        entries = out["structured_report"]["provenance"]["module_plan"]["entries"]
        entry = next((e for e in entries if e["module"] == module), None)
        assert entry is not None, f"{gene} 未激活 {module}"
        assert f"rule_based:{module}_gene_set" in entry["caution_flags"]
        assert "evidence_limited" in entry["caution_flags"]
        assert entry["route_disposition"] == "downgrade"


def test_b4_advisory_walled_from_reliability_e2e():
    # module_plan advisory 是 provenance,不喂 reliability 推理/预测路径:
    #  ① mock 预测器照常跑(models_used 有 MockLinear)——advisory 不 gate 预测;
    #  ② advisory 的 rule_based 痕迹只在 provenance.module_plan 出现,不泄漏进任何 reliability
    #     推理字段(abstain_reasons/downgrade_reasons/caution_flags/failed_checks/model_disagreement
    #     等 structured_report 顶层字段)—— 去掉 provenance 后整份 report 不含 advisory 串;
    #  ③ llm_used_for_prediction 恒 False;④ 反证:advisory 确实在 provenance.module_plan(非整份缺失)。
    out = run_query(dict(_B4_RUNQ), config=_CFG)
    sr = out["structured_report"]
    assert out["llm_used_for_prediction"] is False
    assert "MockLinear" in sr["provenance"]["models_used"]        # 预测器照跑,未被 advisory 短路
    # 强隔离:扫描 structured_report 去 provenance 后的全部 reliability 推理面
    sr_no_prov = _json.dumps({k: v for k, v in sr.items() if k != "provenance"},
                             ensure_ascii=False, default=str)
    assert "rule_based:membrane_system_gene_set" not in sr_no_prov
    assert "membrane_system" not in sr_no_prov
    # 反证:advisory 确实存在(在 provenance.module_plan),证明上面的排除非空断言
    m1 = next(e for e in sr["provenance"]["module_plan"]["entries"]
              if e["module"] == "membrane_system")
    assert m1["verdict"] == "downgrade"
    assert "rule_based:membrane_system_gene_set" in m1["caution_flags"]


def test_b4_non_gene_set_gene_no_advisory_e2e():
    # 非 gene-set 基因(TP53):module_plan 不含 M1/M5/M8
    out = run_query(dict(_B4_RUNQ, perturbation_targets=["TP53"]), config=_CFG)
    modules = {e["module"] for e in out["structured_report"]["provenance"]["module_plan"]["entries"]}
    assert not ({"membrane_system", "biosynthetic_network", "degradation_machinery"} & modules)


def test_b4_membrane_request_deterministic_byte_equal():
    outs = [run_query(dict(_B4_RUNQ), config=_CFG) for _ in range(3)]
    assert len({_canon(o["structured_report"]) for o in outs}) == 1
    assert len({_canon(o["trace"]) for o in outs}) == 1
