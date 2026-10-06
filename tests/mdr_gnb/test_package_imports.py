"""G0:断言 mdr_gnb 全部子模块可 import,且关键符号存在。"""
from __future__ import annotations

import importlib

import pytest

# 全部需可导入的子模块(顶层 + 各子包 + 10 物种 + 8 药物类 + mechanistic)
SPECIES = [
    "acinetobacter_baumannii", "klebsiella_pneumoniae", "escherichia_coli",
    "pseudomonas_aeruginosa", "enterobacter_cloacae", "salmonella_enterica",
    "stenotrophomonas_maltophilia", "serratia_marcescens", "proteus_mirabilis",
    "morganella_morganii",
]
DRUG_CLASSES = [
    "beta_lactams", "carbapenems", "polymyxins", "aminoglycosides",
    "fluoroquinolones", "tetracyclines", "antimicrobial_peptides", "combination_therapy",
]

BASE = "praxis_virtualcell.mdr_gnb"

MODULES = [
    BASE,
    f"{BASE}.message",
    f"{BASE}.abstain",
    f"{BASE}.critic",
    f"{BASE}.coordinator",
    f"{BASE}.coordinator.task_parser",
    f"{BASE}.coordinator.mdr_router",
    f"{BASE}.coordinator.report_builder",
    f"{BASE}.agents",
    f"{BASE}.agents.base_species_agent",
    f"{BASE}.drug_agent",
    f"{BASE}.drug_agent.agent",
    f"{BASE}.drug_agent.drug_schema",
    f"{BASE}.drug_agent.peptide_features",
    f"{BASE}.drug_agent.small_molecule_features",
    f"{BASE}.predictors",
    f"{BASE}.predictors.registry",
    f"{BASE}.predictors.features",
    f"{BASE}.predictors.rule_baseline",
    f"{BASE}.predictors.genotype_to_sir",
    f"{BASE}.predictors.mic_regressor",
    f"{BASE}.predictors.peptide_activity_model",
    f"{BASE}.predictors.small_molecule_model",
    f"{BASE}.predictors.membrane_permeability_model",
    f"{BASE}.predictors.mechanistic",
    f"{BASE}.predictors.mechanistic.cell_state",
    f"{BASE}.predictors.mechanistic.gem_fba",
    f"{BASE}.predictors.mechanistic.mechanism_state_model",
    f"{BASE}.predictors.mechanistic.intervention",
    f"{BASE}.predictors.mechanistic.falsifiability",
    f"{BASE}.databases",
    f"{BASE}.databases.bvbrc_loader",
    f"{BASE}.databases.amrfinder_runner",
    f"{BASE}.databases.card_loader",
    f"{BASE}.databases.breakpoint_loader",
    f"{BASE}.databases.dbaasp_loader",
    f"{BASE}.evaluators",
    f"{BASE}.evaluators.funnel",
    f"{BASE}.evaluators.lineage_split",
    f"{BASE}.evaluators.ast_metrics",
    f"{BASE}.evaluators.risk_coverage",
    f"{BASE}.evaluators.leakage_check",
    f"{BASE}.evaluators.combo_gate",
    f"{BASE}.screening",
    f"{BASE}.screening.cross_species",
    f"{BASE}.workflows",
    f"{BASE}.workflows.run_mdr_query",
    f"{BASE}.workflows.run_batch_screen",
]
MODULES += [f"{BASE}.agents.{s}" for s in SPECIES]
MODULES += [f"{BASE}.agents.{s}.agent" for s in SPECIES]
MODULES += [f"{BASE}.drug_agent.{c}" for c in DRUG_CLASSES]


@pytest.mark.parametrize("mod", MODULES)
def test_module_importable(mod: str) -> None:
    """每个子模块必须可 import。"""
    importlib.import_module(mod)


def test_key_symbols_exist() -> None:
    """关键类型/函数符号必须存在(字段名/签名锁定契约)。"""
    from praxis_virtualcell.mdr_gnb.message import MDRGNBMessage
    from praxis_virtualcell.mdr_gnb.drug_agent.drug_schema import (
        DrugTestRequest, DrugTestResult,
    )
    from praxis_virtualcell.mdr_gnb.predictors.mechanistic.cell_state import BacterialCellState
    from praxis_virtualcell.mdr_gnb.evaluators.funnel import FunnelRow
    from praxis_virtualcell.mdr_gnb.evaluators.lineage_split import SplitSpec
    from praxis_virtualcell.mdr_gnb.evaluators.combo_gate import ComboGateResult
    from praxis_virtualcell.mdr_gnb.coordinator import parse_task, route_mdr, build_report
    from praxis_virtualcell.mdr_gnb.predictors import PredictorRegistry, build_feature_matrix
    from praxis_virtualcell.mdr_gnb.workflows import run_mdr_query, run_batch_screen

    # dataclass 字段名锁定校验
    msg = MDRGNBMessage(task_id="t1", species="escherichia_coli")
    assert msg.amr_profile == {} and msg.drug_panel == [] and msg.boundaries == []

    state = BacterialCellState(species="escherichia_coli")
    for f in ("cell_wall_stress", "outer_membrane_permeability", "efflux_activity",
              "beta_lactamase_activity", "ribosome_target_sensitivity",
              "dna_gyrase_sensitivity", "oxidative_stress_response", "biofilm_state"):
        assert hasattr(state, f), f"BacterialCellState 缺字段 {f}"

    # pydantic 默认 requested_outputs 锁定
    req = DrugTestRequest(species="escherichia_coli")
    assert req.requested_outputs == [
        "MIC_range", "SIR", "mechanism", "confidence", "experiment_priority",
    ]
    res = DrugTestResult(drug="ceftriaxone")
    assert res.confidence == "low" and res.abstained is False

    # FunnelRow / SplitSpec / ComboGateResult 字段
    fr = FunnelRow(stage="raw", n_records=0, n_strains=0)
    assert fr.note == ""
    ss = SplitSpec(scheme="lineage_blocked", fold=0)
    assert ss.train_ids == [] and ss.group_key == ""
    cg = ComboGateResult(species="escherichia_coli", drug="ceftriaxone",
                         status="abstain_only", n_strains=0)
    assert cg.vme_model is None

    # 可调用符号存在
    for fn in (parse_task, route_mdr, build_report, build_feature_matrix,
               run_mdr_query, run_batch_screen):
        assert callable(fn)
    assert callable(PredictorRegistry)
