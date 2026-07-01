"""R4(v0.5):Cancer EMT state 刻画 case —— mcfarland_2020(真跑,填 State/fate 例 3C)。

断言实测:EMT 评分分离肉瘤(间质)vs 上皮癌(Cohen's d ~1.7)→ accept。治理:marker 覆盖不足→downgrade。
"""
import pytest

from praxis_virtualcell.predictors.state.emt import EmtDB, run_emt_case, _DEFAULT_SUBSET
from praxis_virtualcell.agents.case_report import validate_case_report

if not _DEFAULT_SUBSET.is_file():
    pytest.skip(f"mcfarland EMT 子集缺失({_DEFAULT_SUBSET})", allow_module_level=True)


@pytest.fixture(scope="module")
def db():
    return EmtDB()


def test_emt_separates_sarcoma_from_epithelial(db):
    res = db.emt_separation()
    assert res["mesenchymal_mean"] > res["epithelial_mean"]    # 肉瘤 EMT 评分 > 上皮癌
    assert res["cohens_d"] > 1.0                               # 强分离(实测 ~1.7)


def test_full_case_accept(db):
    report, dec = run_emt_case({
        "case_id": "S_emt", "species": "human", "cell_type": "cancer",
        "perturbation_object": "gene", "perturbation_targets": ["ZEB1"],
        "target_output": "state",
    }, db=db)
    validate_case_report(report)
    d = report.to_dict()
    assert dec.engine == "state_scoring"
    assert d["reliability_decision"]["disposition"] == "accept"
    assert d["raw_output"]["cohens_d"] > 1.0


def test_low_coverage_downgrades(db):
    report, _ = run_emt_case({
        "species": "human", "cell_type": "cancer", "perturbation_object": "gene",
        "perturbation_targets": ["ZEB1"], "target_output": "state",
    }, db=db, mes_panel=["FAKE1", "FAKE2"])
    assert report.to_dict()["reliability_decision"]["disposition"] == "downgrade"


def test_boundary_notes_state_characterization(db):
    report, _ = run_emt_case({
        "species": "human", "cell_type": "cancer", "perturbation_object": "gene",
        "perturbation_targets": ["ZEB1"], "target_output": "state",
    }, db=db)
    assert "状态刻画" in str(report.to_dict()["provenance_boundary"])
