"""R1(v0.5):Stem/progenitor 分化 fate case —— paul15 髓系祖细胞(真跑,填 State/fate 例 3A)。

分析:红系(Gata1/Klf1/Hbb-b1…)vs 髓系(Elane/Mpo/Prtn3…)lineage fate 评分 → 分离红系/髓系群。
断言实测:fate 评分强分离两谱系(Cohen's d ≈ 4)→ accept。治理:marker 覆盖不足→downgrade。
注:paul15 是**原生小鼠 scRNA**,marker 分析非 human→mouse predictor 迁移 → ortholog caution 不适用。
"""
import pytest

from praxis_virtualcell.agents.case_report import validate_case_report
from praxis_virtualcell.predictors.state.fate import _DEFAULT_SUBSET, FateDB, run_fate_case

if not _DEFAULT_SUBSET.is_file():
    pytest.skip(f"paul15 fate 子集缺失({_DEFAULT_SUBSET})", allow_module_level=True)


@pytest.fixture(scope="module")
def db():
    return FateDB()


def test_fate_separates_lineages(db):
    res = db.fate_separation()
    assert res["erythroid_mean"] > res["myeloid_mean"]     # 红系 fate 评分 > 髓系
    assert res["cohens_d"] > 2.0                            # 强分离(实测 ~4.25)


def test_full_case_accept_fate(db):
    report, dec = run_fate_case({
        "case_id": "S_paul15_fate", "species": "mouse", "cell_type": "myeloid progenitor",
        "perturbation_object": "gene", "perturbation_targets": ["Gata1"],
        "target_output": "state",
    }, db=db)
    validate_case_report(report)
    d = report.to_dict()
    assert dec.engine == "state_scoring"
    assert d["reliability_decision"]["disposition"] == "accept"
    assert d["raw_output"]["cohens_d"] > 2.0


def test_low_coverage_downgrades(db):
    report, _ = run_fate_case({
        "species": "mouse", "cell_type": "progenitor", "perturbation_object": "gene",
        "perturbation_targets": ["Gata1"], "target_output": "state",
    }, db=db, ery_panel=["FAKE1", "FAKE2"])          # 覆盖不足
    assert report.to_dict()["reliability_decision"]["disposition"] == "downgrade"


def test_lineage_composition(db):
    per = report_lineages(db)
    assert "erythroid" in per and "myeloid" in per


def report_lineages(db):
    return {c["lineage"] for c in db._d["cells"]}
