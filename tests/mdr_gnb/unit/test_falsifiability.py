"""三支柱可证伪:消融、干预一致性、独立机理监督相关性。"""
import pytest

from praxis_virtualcell.mdr_gnb.predictors.mechanistic.cell_state import (
    BacterialCellState,
)
from praxis_virtualcell.mdr_gnb.predictors.mechanistic.falsifiability import (
    AblationResult,
    correlate_mechanism_supervision,
    run_ablation,
    run_intervention_consistency,
)


def test_ablation_flags_mechanism_helps_when_removal_hurts():
    # 去掉机理层后 VME 明显上升 -> mechanism_helps True
    with_mech = {"vme": 0.05, "major_error": 0.08, "n_strains": 120}
    without_mech = {"vme": 0.15, "major_error": 0.10, "n_strains": 120}
    r = run_ablation(with_mech, without_mech, vme_worsen_threshold=0.03)
    assert isinstance(r, AblationResult)
    assert r.mechanism_helps is True
    assert r.vme_delta == pytest.approx(0.10)
    assert "做功" in r.conclusion


def test_ablation_flags_mechanism_useless_when_no_change():
    with_mech = {"vme": 0.10, "major_error": 0.09, "n_strains": 120}
    without_mech = {"vme": 0.101, "major_error": 0.09, "n_strains": 120}
    r = run_ablation(with_mech, without_mech, vme_worsen_threshold=0.03)
    assert r.mechanism_helps is False
    assert "未做功" in r.conclusion or "不成立" in r.conclusion


def test_intervention_consistency_all_pass_when_directions_correct():
    base = BacterialCellState(species="klebsiella_pneumoniae")
    res = run_intervention_consistency(base, ["ompK36_knockout", "mexAB_overexpression"])
    assert res["all_consistent"] is True
    assert all(item["consistent"] for item in res["checks"])


def test_intervention_consistency_detects_wrong_direction():
    base = BacterialCellState(species="klebsiella_pneumoniae")
    # 注入一个"坏"干预函数,把方向搞反,应被检出
    def bad_apply(state, name):
        return state.copy_with(outer_membrane_permeability=0.9)

    res = run_intervention_consistency(
        base, ["ompK36_knockout"], apply_fn=bad_apply
    )
    assert res["all_consistent"] is False


def test_supervision_returns_unverified_when_no_data():
    r = correlate_mechanism_supervision(
        predicted={"efflux_activity": [0.9, 0.2, 0.8]},
        measured={},  # 无独立功能数据
    )
    assert r["efflux_activity"]["status"] == "unverified"


def test_supervision_reports_correlation_when_data_present():
    r = correlate_mechanism_supervision(
        predicted={"efflux_activity": [0.9, 0.2, 0.8, 0.5]},
        measured={"efflux_activity": [0.85, 0.25, 0.75, 0.55]},
    )
    assert r["efflux_activity"]["status"] == "verified"
    assert r["efflux_activity"]["spearman"] > 0.8
