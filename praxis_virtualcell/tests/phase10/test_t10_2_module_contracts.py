import hashlib
import importlib.util
import json as _json
from types import SimpleNamespace

import pytest

from praxis_virtualcell.agents import model_applicability as MA
from praxis_virtualcell.agents import module_rules as MR
from praxis_virtualcell.agents.case_report import CaseReport as _CaseReport
from praxis_virtualcell.agents.model_applicability import ModelApplicabilityAgent
from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.request_adapter import request_to_module_input
from praxis_virtualcell.agents.species_brain import SpeciesBrainAgent
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.agents.species_schema import normalize_request as _norm
from praxis_virtualcell.biological_modules import module_gene_sets as MGS
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.core.exceptions import PraxisVCError, UnsupportedEngine
from praxis_virtualcell.core.exceptions import UnsupportedEngine as _UnsupportedEngine
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.predictors import case_dispatch as CD
from praxis_virtualcell.predictors.case_dispatch import dispatch_runner, map_case_delta
from praxis_virtualcell.predictors.case_runner_agent import CaseRunnerPredictorAgent
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_HAS_TORCH = importlib.util.find_spec("torch") is not None


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


def test_case_runner_assess_applicability_reject_unsupported(monkeypatch):
    monkeypatch.setattr(CD, "gears_available", lambda: False)
    agent = CaseRunnerPredictorAgent()

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

    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    out = _run_applicability(req)
    assert "CaseRunner" not in out["applicable"]
    assert set(out["rejected_candidates"]) <= {"MockLinear", "MockCPA", "MockGEARS"}
    assert "real_engine" not in out["brain_context"].get("routing", {})


def test_applicability_boundary_request_falls_back_to_mock():

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
    assert rd["abstain"] is False
    sr = out["structured_report"]
    assert "CaseRunner" in sr["provenance"]["models_used"]
    assert out["llm_used_for_prediction"] is False

    assert sr["prediction"]["delta"] == [-1.0]


def _canon(obj):
    return hashlib.sha256(_json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def test_real_request_rerun_byte_equal():
    outs = [run_query(dict(_BACT_GROWTH), config=_CFG) for _ in range(3)]
    assert len({_canon(o["structured_report"]) for o in outs}) == 1
    assert len({_canon(o["trace"]) for o in outs}) == 1


def test_mock_request_unchanged_by_adapter():

    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    used = out["structured_report"]["provenance"]["models_used"]
    assert "CaseRunner" not in used


def test_gem_fba_provenance_honest():
    out = run_query(dict(_BACT_GROWTH), config=_CFG)
    prov = out["structured_report"]["provenance"]

    assert "CaseRunner" in prov["models_used"]

    assert prov["module_plan"]["entries"][0]["engine"] == "gem_fba"

    assert prov["rules_referenced"]


def test_yeast_growth_also_real_fba():
    req = {"species": "yeast", "perturbation_type": "gene", "perturbation_targets": ["YBR166C"],
           "input_modality": "scRNA", "output_modality": "growth",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    assert out["reliability_decision"]["abstain"] is False
    assert "CaseRunner" in out["structured_report"]["provenance"]["models_used"]


def test_all_targets_not_in_gem_abstains_honestly():

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

    req = {"species": "bacteria", "perturbation_type": "gene_combination",
           "perturbation_targets": ["b0720", "b9999"],
           "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    assert out["reliability_decision"]["abstain"] is False
    assert out["structured_report"]["prediction"]["delta"] == [-1.0]
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
    assert "all_targets_not_in_gem" in md
    assert "CaseRunner` — Reason not recorded" not in md


def test_dispatch_runner_gem_fba_medium():
    from praxis_virtualcell.predictors.mechanistic.medium_shift import run_medium_shift_case
    raw = {"species": "bacteria", "perturbation_object": "medium"}
    assert dispatch_runner("gem_fba", raw) is run_medium_shift_case


def test_dispatch_runner_gem_fba_medium_yeast_unsupported():

    with pytest.raises(UnsupportedEngine):
        dispatch_runner("gem_fba", {"species": "yeast", "perturbation_object": "medium"})


def test_map_case_delta_gem_fba_medium():
    report = SimpleNamespace(raw_output={"reference": "glucose minimal", "glucose_growth": 0.87392,
        "carbon_sources": [{"carbon": "acetate", "in_model": True, "ratio_vs_glucose": 0.1983},
                           {"carbon": "unobtainium", "in_model": False, "ratio_vs_glucose": None}]})
    assert map_case_delta("gem_fba", report) == [-0.8017]


def test_dispatch_runner_gem_fba_drug():
    from praxis_virtualcell.predictors.mechanistic.antibiotic import run_antibiotic_case
    raw = {"species": "bacteria", "perturbation_object": "drug"}
    assert dispatch_runner("gem_fba", raw) is run_antibiotic_case


def test_map_case_delta_gem_fba_drug():
    report = SimpleNamespace(raw_output={"wt_growth": 0.877, "antibiotics": [
        {"antibiotic": "trimethoprim", "target_rxn": "DHFR", "in_model": True, "ratio_vs_wt": 0.0},
        {"antibiotic": "ampicillin", "target_rxn": "non-metabolic", "known": True, "in_model": False}]})

    assert map_case_delta("gem_fba", report) == [-1.0]


def test_pathway_scoring_in_real_engines():
    from praxis_virtualcell.predictors.case_dispatch import REAL_ENGINES
    assert "pathway_scoring" in REAL_ENGINES


def test_dispatch_runner_pathway_scoring_ifn():
    from praxis_virtualcell.predictors.state.metabolic_tendency import run_metabolic_tendency_case
    raw = {"species": "human", "perturbation_object": "ligand", "perturbation_targets": ["IFNB1"]}
    assert dispatch_runner("pathway_scoring", raw) is run_metabolic_tendency_case


def test_dispatch_runner_pathway_scoring_non_ifn_unsupported():

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
    assert sr["prediction"]["delta"] == [-0.8017]


def test_bacteria_antibiotic_real_fba():
    req = {"species": "bacteria", "perturbation_type": "drug", "perturbation_targets": ["trimethoprim"],
           "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is False
    assert sr["prediction"]["delta"] == [-1.0]


def test_bacteria_antibiotic_non_metabolic_abstains():

    req = {"species": "bacteria", "perturbation_type": "drug", "perturbation_targets": ["ampicillin"],
           "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is True
    assert sr["prediction"] is None
    assert "CaseRunner" in sr["provenance"]["models_rejected"]
    assert any("non_metabolic_target" in f for f in sr["provenance"]["model_cautions"]["CaseRunner"])


def test_b2_real_requests_rerun_byte_equal():

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


    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    used = out["structured_report"]["provenance"]["models_used"]
    assert "CaseRunner" not in used
    assert set(used) <= {"MockLinear", "MockCPA", "MockGEARS"}


def test_dispatch_runner_pathway_scoring_mouse_unsupported():

    with pytest.raises(UnsupportedEngine):
        dispatch_runner("pathway_scoring", {"species": "mouse", "perturbation_object": "ligand",
                                            "perturbation_targets": ["IFNB1"]})


def test_dispatch_runner_pathway_scoring_non_beta_ifn_unsupported():

    for tg in (["interferon gamma"], ["interferon alpha"]):
        with pytest.raises(UnsupportedEngine):
            dispatch_runner("pathway_scoring", {"species": "human", "perturbation_object": "ligand",
                                                "perturbation_targets": tg})


def test_pathway_scoring_species_cytokine_leak_abstains_e2e():

    for sp, tg in (("mouse", ["IFNB1"]), ("human", ["interferon gamma"])):
        req = {"species": sp, "perturbation_type": "ligand", "perturbation_targets": tg,
               "input_modality": "scRNA", "output_modality": "flux", "task_type": "predict_delta_expression"}
        out = run_query(dict(req), config=_CFG)
        assert out["reliability_decision"]["abstain"] is True
        assert out["structured_report"]["prediction"] is None
        assert "CaseRunner" in out["structured_report"]["provenance"]["models_rejected"]


def test_dispatch_runner_pathway_scoring_ifnb2_il6_unsupported():

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

    with pytest.raises(UnsupportedEngine):
        dispatch_runner("embedding", {"species": "human", "perturbation_object": "ligand"})


def test_human_ligand_not_mislabeled_as_drug():
    req = {"species": "human", "perturbation_type": "ligand", "perturbation_targets": ["TGFB1"],
           "input_modality": "scRNA", "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    prov = out["structured_report"]["provenance"]

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

    report = SimpleNamespace(raw_output={"drug": "wortmannin", "dose_response": None})
    assert map_case_delta("embedding", report) == []


def test_human_drug_dose_real_e2e():

    req = {"species": "human", "perturbation_type": "drug", "perturbation_targets": ["geldanamycin"],
           "perturbation_dose": 10.0, "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is False
    assert "CaseRunner" in sr["provenance"]["models_used"]
    assert sr["prediction"]["delta"] == [0.9]


def test_human_drug_dose_not_in_db_abstains_honestly():

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
    assert sr["prediction"]["delta"] == [2.646]


def test_human_ifn_cellstate_real_e2e():
    req = {"species": "human", "perturbation_type": "ligand", "perturbation_targets": ["IFNB1"],
           "input_modality": "scRNA", "output_modality": "state", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is False
    assert "CaseRunner" in sr["provenance"]["models_used"]
    assert sr["prediction"]["delta"] == [2.485]


def test_stress_limitation_paths_abstain_honestly():


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


    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    used = out["structured_report"]["provenance"]["models_used"]
    assert "CaseRunner" not in used
    assert set(used) <= {"MockLinear", "MockCPA", "MockGEARS"}


def test_is_ifn_beta_mixed_targets_unsupported():

    with pytest.raises(UnsupportedEngine):
        dispatch_runner("state_scoring", {"species": "human", "perturbation_object": "gene",
                                          "perturbation_targets": ["IFNB1", "ZEB1"]})
    with pytest.raises(UnsupportedEngine):
        dispatch_runner("pathway_scoring", {"species": "human", "perturbation_object": "gene",
                                            "perturbation_targets": ["IFNB1", "TP53"]})


def test_mixed_ifn_target_abstains_e2e():

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

    assert MGS.gene_set_of("genetic_hub") == frozenset()


def test_b4_modules_hit_by_single_hits():
    assert MGS.modules_hit_by(["SLC2A1"]) == ["membrane_system"]
    assert MGS.modules_hit_by(["RPS6"]) == ["biosynthetic_network"]
    assert MGS.modules_hit_by(["PSMB5"]) == ["degradation_machinery"]


def test_b4_modules_hit_by_mixed_hit_and_miss():

    assert MGS.modules_hit_by(["PSMB5", "TP53"]) == ["degradation_machinery"]
    assert MGS.modules_hit_by(["TP53"]) == []


def test_b4_modules_hit_by_exact_match_no_substring():
    assert MGS.modules_hit_by(["slc2a1"]) == ["membrane_system"]
    assert MGS.modules_hit_by(["SLC2A"]) == []
    assert MGS.modules_hit_by(["XSLC2A1"]) == []


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

    sec = MR.pick_secondary(_b4_norm_req(), "membrane_system")
    assert "membrane_system" not in sec

    assert len(sec) == len(set(sec))


def test_b4_pick_secondary_preserves_m3_for_mammalian_growth():

    req = _b4_norm_req(target_output="growth", perturbation_targets=["SLC2A1"])
    sec = MR.pick_secondary(req, "cytoplasmic_metabolism")
    assert "mitochondrial_energy_metabolism" in sec
    assert "membrane_system" in sec

    assert sec == ["mitochondrial_energy_metabolism", "membrane_system"]


def test_b4_pick_secondary_gene_gated_drug_ligand_not_activated():

    for obj in ("drug", "ligand"):
        req = _b4_norm_req(perturbation_object=obj, perturbation_targets=["SLC2A1"])
        assert MR.gene_set_secondary(req) == []
        assert "membrane_system" not in MR.pick_secondary(req, "stress_processor")

    req_gc = _b4_norm_req(perturbation_object="gene_combination", perturbation_targets=["SLC2A1"])
    assert "membrane_system" in MR.gene_set_secondary(req_gc)


_B4_RAW_MEMBRANE = {"species": "human", "perturbation_object": "gene",
                    "target_output": "expression", "perturbation_targets": ["SLC2A1"]}


def _b4_plan_for(request):
    """Test helper: b4 plan for."""
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
    assert m1["route_disposition"] == "downgrade"
    assert m1["species_verdict"] == "caution"                # human membrane weak→caution
    assert m1["verdict"] == "downgrade"                      # synthesize(downgrade,caution,None)=downgrade
    assert "rule_based:membrane_system_gene_set" in m1["caution_flags"]
    assert "evidence_limited" in m1["caution_flags"]
    assert "rule_based_gene_set_advisory" in m1["reason"]


def test_b4_overall_verdict_downgrades_not_abstain():
    p = _b4_plan_for(dict(_B4_RAW_MEMBRANE))
    assert p["overall_verdict"] == "downgrade"

    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["module"] == "genetic_hub"
    assert prim["verdict"] == "accept"
    assert "rule_based:membrane_system_gene_set" not in prim["caution_flags"]


def test_b4_non_gene_set_gene_no_advisory_entry():
    p = _b4_plan_for(dict(_B4_RAW_MEMBRANE, perturbation_targets=["TP53"]))
    modules = {e["module"] for e in p["entries"]}
    assert not ({"membrane_system", "biosynthetic_network", "degradation_machinery"} & modules)
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["verdict"] == "accept"


def test_b4_advisory_entry_has_no_numeric_delta_field():
    p = _b4_plan_for(dict(_B4_RAW_MEMBRANE))
    m1 = next(e for e in p["entries"] if e["module"] == "membrane_system")

    assert "delta" not in m1
    assert "prediction" not in m1


def test_b4_advisory_never_relaxes_route_abstain():



    p = _b4_plan_for({"species": "bacteria", "perturbation_object": "gene",
                      "target_output": "expression", "perturbation_targets": ["FASN"]})
    m1 = next(e for e in p["entries"] if e["module"] == "membrane_system")
    assert m1["route_disposition"] == "abstain"
    assert m1["verdict"] == "abstain"

    assert "rule_based:membrane_system_gene_set" in m1["caution_flags"]
    assert "evidence_limited" in m1["caution_flags"]
    assert p["overall_verdict"] == "abstain"


_B4_RUNQ = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["SLC2A1"],
            "input_modality": "scRNA", "output_modality": "delta_expression",
            "task_type": "predict_delta_expression"}


def test_b4_all_three_modules_runnable_e2e():


    for gene, module in [("SLC2A1", "membrane_system"), ("RPS6", "biosynthetic_network"),
                         ("PSMB5", "degradation_machinery")]:
        out = run_query(dict(_B4_RUNQ, perturbation_targets=[gene]), config=_CFG)
        entries = out["structured_report"]["provenance"]["module_plan"]["entries"]
        entry = next((e for e in entries if e["module"] == module), None)
        assert entry is not None, f"{gene} failed to activate {module}"
        assert f"rule_based:{module}_gene_set" in entry["caution_flags"]
        assert "evidence_limited" in entry["caution_flags"]
        assert entry["route_disposition"] == "downgrade"


def test_b4_advisory_walled_from_reliability_e2e():






    out = run_query(dict(_B4_RUNQ), config=_CFG)
    sr = out["structured_report"]
    assert out["llm_used_for_prediction"] is False
    assert "MockLinear" in sr["provenance"]["models_used"]

    sr_no_prov = _json.dumps({k: v for k, v in sr.items() if k != "provenance"},
                             ensure_ascii=False, default=str)
    assert "rule_based:membrane_system_gene_set" not in sr_no_prov
    assert "membrane_system" not in sr_no_prov

    m1 = next(e for e in sr["provenance"]["module_plan"]["entries"]
              if e["module"] == "membrane_system")
    assert m1["verdict"] == "downgrade"
    assert "rule_based:membrane_system_gene_set" in m1["caution_flags"]


def test_b4_non_gene_set_gene_no_advisory_e2e():

    out = run_query(dict(_B4_RUNQ, perturbation_targets=["TP53"]), config=_CFG)
    modules = {e["module"] for e in out["structured_report"]["provenance"]["module_plan"]["entries"]}
    assert not ({"membrane_system", "biosynthetic_network", "degradation_machinery"} & modules)


def test_b4_membrane_request_deterministic_byte_equal():
    outs = [run_query(dict(_B4_RUNQ), config=_CFG) for _ in range(3)]
    assert len({_canon(o["structured_report"]) for o in outs}) == 1
    assert len({_canon(o["trace"]) for o in outs}) == 1



def test_m2_gears_available_false_without_ckpt(monkeypatch):
    monkeypatch.delenv("GEARS_CKPT", raising=False)
    assert CD.gears_available() is False


def test_m2_gears_available_false_when_gears_not_importable(monkeypatch):
    monkeypatch.setenv("GEARS_CKPT", "/fake/ckpt")
    monkeypatch.setattr(CD, "_gears_importable", lambda: False)
    assert CD.gears_available() is False


def test_m2_gears_available_true_when_ckpt_and_importable(monkeypatch):
    monkeypatch.setenv("GEARS_CKPT", "/fake/ckpt")
    monkeypatch.setattr(CD, "_gears_importable", lambda: True)
    assert CD.gears_available() is True


def test_m2_gears_available_false_when_ckpt_empty_string(monkeypatch):

    monkeypatch.setenv("GEARS_CKPT", "")
    monkeypatch.setattr(CD, "_gears_importable", lambda: True)
    assert CD.gears_available() is False



def _m2_applicable(req, brain_context=None, monkeypatch=None, gears=False):
    """Test helper: m2 applicable."""
    if monkeypatch is not None:
        monkeypatch.setattr(MA, "gears_available", lambda: gears, raising=False)
    bus = MessageBus()
    bc = brain_context or {"model_applicability": {}, "object_vocabulary": {"genes": []}}
    MA.ModelApplicabilityAgent().handle(AgentMessage(
        message_id="m1", sender="s", receiver="ModelApplicability",
        message_type="applicability", payload={"request": req, "brain_context": bc},
        timestamp="t1"), bus)
    return bus.latest("applicability_decided").payload["applicable"]


_M2_REQ = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}


def _m2_real_human_brain_context():
    """Test helper: m2 real human brain context."""
    bus = MessageBus()
    SpeciesBrainAgent(RuntimeConfig()).handle(AgentMessage(
        message_id="b1", sender="SpeciesBrain", receiver="ModelApplicability",
        message_type="brain_lookup", payload={"request": {"species": "human"}},
        timestamp="t0"), bus)
    return bus.latest("brain_retrieved").payload["brain_context"]


def test_m2_donor_predictor_mac_falls_back_to_mock(monkeypatch):



    app = _m2_applicable(dict(_M2_REQ), brain_context=_m2_real_human_brain_context(),
                          monkeypatch=monkeypatch, gears=False)
    assert "CaseRunner" not in app
    assert set(app) >= {"MockLinear", "MockCPA", "MockGEARS"}


def test_m2_donor_predictor_gated_routes_to_case_runner(monkeypatch):

    app = _m2_applicable(dict(_M2_REQ), monkeypatch=monkeypatch, gears=True)
    assert app == ["CaseRunner"]



def test_m2_dispatch_donor_predictor_human_gene_returns_runner(monkeypatch):
    from praxis_virtualcell.predictors.ml.gears_case import run_gears_case
    monkeypatch.setattr(CD, "gears_available", lambda: True)
    raw = {"species": "human", "perturbation_object": "gene",
           "target_output": "expression", "perturbation_targets": ["AHR"]}
    assert CD.dispatch_runner("donor_predictor", raw) is run_gears_case


def test_m2_dispatch_donor_predictor_non_human_unsupported(monkeypatch):

    monkeypatch.setattr(CD, "gears_available", lambda: True)
    raw = {"species": "mouse", "perturbation_object": "gene",
           "target_output": "expression", "perturbation_targets": ["Ahr"]}
    with pytest.raises(_UnsupportedEngine):
        CD.dispatch_runner("donor_predictor", raw)


def test_m2_dispatch_donor_predictor_non_gene_unsupported(monkeypatch):

    monkeypatch.setattr(CD, "gears_available", lambda: True)
    raw = {"species": "human", "perturbation_object": "drug",
           "target_output": "expression", "perturbation_targets": ["vorinostat"]}
    with pytest.raises(_UnsupportedEngine):
        CD.dispatch_runner("donor_predictor", raw)


def test_m2_dispatch_donor_predictor_unsupported_when_gears_unavailable(monkeypatch):

    monkeypatch.setattr(CD, "gears_available", lambda: False)
    raw = {"species": "human", "perturbation_object": "gene",
           "target_output": "expression", "perturbation_targets": ["AHR"]}
    with pytest.raises(_UnsupportedEngine):
        CD.dispatch_runner("donor_predictor", raw)


def test_m2_map_case_delta_gears_reads_gears_delta():
    rep = _CaseReport(case_id="c", structured_input={"x": 1},
                      object_normalization={"species": "human"},
                      models_tools_selected={"engine": "donor_predictor"},
                      raw_output={"gears_delta": [0.12, -0.34], "targets": ["AHR"],
                                  "value_type": "gears_internal_delta"},
                      baseline_comparison={"baseline": "gears ctrl"},
                      reliability_decision={"disposition": "accept", "caution_flags": [], "data_gated": False},
                      provenance_boundary={"rules_hit": ["r"], "boundary": "b"})
    assert CD.map_case_delta("donor_predictor", rep) == [0.12, -0.34]


@pytest.mark.skipif(_HAS_TORCH, reason="Requires a torch-free environment; real inference is tested remotely.")
def test_m2_gears_runner_fail_closed_without_torch():

    from praxis_virtualcell.predictors.ml.gears_case import run_gears_case
    raw = {"species": "human", "perturbation_object": "gene",
           "target_output": "expression", "perturbation_targets": ["AHR"]}
    with pytest.raises((ModuleNotFoundError, ImportError, RuntimeError)):
        run_gears_case(raw)



def test_m2_mac_genetic_hub_still_mock_e2e(monkeypatch):
    """Verify m2 mac genetic hub still mock e2e."""
    monkeypatch.delenv("GEARS_CKPT", raising=False)
    out = run_query(dict(_M2_REQ), config=_CFG)
    sr = out["structured_report"]
    used = sr["provenance"]["models_used"]
    assert "CaseRunner" not in used

    assert "CaseRunner" not in sr["provenance"]["model_cautions"]
    dumped = _json.dumps(sr, default=str, ensure_ascii=False)
    assert "gears_internal_delta" not in dumped
    assert "gears_native_absolute_expression" not in dumped
    assert "M2_gears_delta" not in dumped


def test_m2_mac_genetic_hub_deterministic_byte_equal(monkeypatch):
    """Verify m2 mac genetic hub deterministic byte equal."""
    monkeypatch.delenv("GEARS_CKPT", raising=False)
    outs = [run_query(dict(_M2_REQ), config=_CFG) for _ in range(3)]
    assert len({_canon(o["structured_report"]) for o in outs}) == 1
    assert len({_canon(o["trace"]) for o in outs}) == 1



def test_m2_applicability_mouse_gene_not_case_runner_even_on_53(monkeypatch):

    req = {"species": "mouse", "perturbation_type": "gene", "perturbation_targets": ["Ahr"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    app = _m2_applicable(req, monkeypatch=monkeypatch, gears=True)
    assert "CaseRunner" not in app


def test_m2_run_gears_case_rejects_non_human_species():

    from praxis_virtualcell.predictors.ml.gears_case import run_gears_case
    raw = {"species": "mouse", "perturbation_object": "gene",
           "target_output": "expression", "perturbation_targets": ["Ahr"]}
    with pytest.raises(_UnsupportedEngine):
        run_gears_case(raw)
