"""G3 冒烟:两个锚点组合跑完整机理三支柱并落报告,gate 判定可读。"""
from pathlib import Path

from praxis_virtualcell.mdr_gnb.predictors.mechanistic.run_g3_gate import run_g3_gate


def test_g3_gate_produces_reports_and_decisions(tmp_path):
    results = run_g3_gate(out_dir=tmp_path)
    assert set(results) == {
        "escherichia_coli__ceftriaxone",
        "klebsiella_pneumoniae__meropenem",
    }
    for key, res in results.items():
        assert Path(res["report_path"]).exists()
        assert "allow_mechanism_explanation" in res["decision"]
        # 干预一致性在正确算子下必须全过(否则机理层实现有 bug)
        assert res["consistency"]["all_consistent"] is True
