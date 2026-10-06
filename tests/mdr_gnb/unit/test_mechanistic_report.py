"""机理报告:落盘 markdown,含三支柱结论与最终 gate 判定(允许/降级)。"""
from pathlib import Path

from praxis_virtualcell.mdr_gnb.predictors.mechanistic.cell_state import (
    BacterialCellState,
)
from praxis_virtualcell.mdr_gnb.predictors.mechanistic.falsifiability import (
    run_ablation,
    run_intervention_consistency,
)
from praxis_virtualcell.mdr_gnb.predictors.mechanistic.report import (
    build_mechanistic_report,
    mechanism_gate_decision,
)


def test_gate_allows_when_helps_and_consistent():
    abl = run_ablation(
        {"vme": 0.05, "major_error": 0.08, "n_strains": 100},
        {"vme": 0.15, "major_error": 0.10, "n_strains": 100},
    )
    cons = run_intervention_consistency(
        BacterialCellState(species="klebsiella_pneumoniae"), ["ompK36_knockout"]
    )
    decision = mechanism_gate_decision(abl, cons)
    assert decision["allow_mechanism_explanation"] is True


def test_gate_degrades_when_ablation_shows_no_work():
    abl = run_ablation(
        {"vme": 0.10, "major_error": 0.09, "n_strains": 100},
        {"vme": 0.10, "major_error": 0.09, "n_strains": 100},
    )
    cons = run_intervention_consistency(
        BacterialCellState(species="klebsiella_pneumoniae"), ["ompK36_knockout"]
    )
    decision = mechanism_gate_decision(abl, cons)
    assert decision["allow_mechanism_explanation"] is False
    assert "降级" in decision["action"]


def test_report_writes_file_with_all_sections(tmp_path):
    abl = run_ablation(
        {"vme": 0.05, "major_error": 0.08, "n_strains": 100},
        {"vme": 0.15, "major_error": 0.10, "n_strains": 100},
    )
    cons = run_intervention_consistency(
        BacterialCellState(species="escherichia_coli"),
        ["ompK36_knockout", "gyrA_qrdr_mutation"],
    )
    sup = {"efflux_activity": {"status": "unverified", "note": "无数据"}}
    out = build_mechanistic_report(
        species="escherichia_coli",
        drug="ceftriaxone",
        ablation=abl,
        consistency=cons,
        supervision=sup,
        out_dir=tmp_path,
    )
    p = Path(out)
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "消融" in text and "干预一致性" in text and "独立机理监督" in text
    assert "免责声明" in text  # D2:科研筛选工具声明
    assert "escherichia_coli" in text and "ceftriaxone" in text
