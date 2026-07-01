"""W5.2(v0.4,Phase II):Human 免疫激活 cell-state case —— Kang 2018 IFN-β PBMC(真跑,非 mock)。

填补 State/fate 空白应用。分析:IFN-β 刺激 → ISG(干扰素刺激基因)激活评分 → ctrl vs stim state 迁移
(Cohen's d)。数据:Enrichr/pertpy Kang 2018 的 committed 子集(data/cellstate/kang_isg_subset.json,
2232 cells × 33 基因,原始 counts)。治理:marker 覆盖不足 → downgrade;迁移不显著 → downgrade/caution。
断言实测:IFN-β → ISG 强激活(d≈2.5)→ accept。
"""
import pytest

from praxis_virtualcell.predictors.state.cell_state import (
    CellStateDB, run_cellstate_case, _DEFAULT_SUBSET,
)
from praxis_virtualcell.agents.case_report import validate_case_report
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.agents.route_table import route

if not _DEFAULT_SUBSET.is_file():
    pytest.skip(f"kang 子集缺失({_DEFAULT_SUBSET})", allow_module_level=True)


@pytest.fixture(scope="module")
def db():
    return CellStateDB()


def test_route_state_to_state_scoring():
    d = route(normalize_request({"species": "human", "perturbation_object": "ligand",
                                 "perturbation_targets": ["IFNB1"], "target_output": "state"}))
    assert d.engine == "state_scoring"


def test_ifn_activates_isg_strong_effect(db):
    res = db.state_shift()
    assert res["stim_mean"] > res["ctrl_mean"]        # 刺激后 ISG 上调
    assert res["cohens_d"] > 1.5                       # 强效应(实测 ~2.5)


def test_full_case_accept_state_transition(db):
    report, dec = run_cellstate_case({
        "case_id": "S_ifn_activation", "species": "human", "cell_type": "PBMC",
        "perturbation_object": "ligand", "perturbation_targets": ["IFNB1"],
        "target_output": "state",
    }, db=db)
    validate_case_report(report)
    d = report.to_dict()
    assert dec.engine == "state_scoring"
    assert d["reliability_decision"]["disposition"] == "accept"
    assert d["raw_output"]["cohens_d"] > 1.5
    assert d["raw_output"]["marker_coverage"] == pytest.approx(1.0)


def test_low_marker_coverage_downgrades(db):
    # marker 覆盖不足(panel 多不在数据)→ 不硬说,downgrade
    report, _ = run_cellstate_case({
        "species": "human", "cell_type": "PBMC", "perturbation_object": "ligand",
        "perturbation_targets": ["IFNB1"], "target_output": "state",
    }, db=db, isg_panel=["FAKE1", "FAKE2", "STAT1"])   # 仅 1/3 覆盖
    assert report.to_dict()["reliability_decision"]["disposition"] == "downgrade"


def test_per_celltype_breakdown_present(db):
    report, _ = run_cellstate_case({
        "species": "human", "cell_type": "PBMC", "perturbation_object": "ligand",
        "perturbation_targets": ["IFNB1"], "target_output": "state",
    }, db=db)
    per = report.to_dict()["raw_output"]["per_cell_type"]
    assert len(per) >= 5 and all("cohens_d" in r for r in per)
