"""R2(v0.5):Drug dose-response case —— LINCS 剂量单调性(真跑,治理对照)。

实测:geldanamycin 剂量-recall 单调(Spearman~0.9)→accept;sirolimus 无单调(Spearman<0)→downgrade。
"""
import pytest

from praxis_virtualcell.predictors.embedding.drug_dose import (
    DoseResponseDB, run_drug_dose_case, _DEFAULT_SUBSET,
)
from praxis_virtualcell.agents.case_report import validate_case_report

if not _DEFAULT_SUBSET.is_file():
    pytest.skip(f"dose 子集缺失({_DEFAULT_SUBSET})", allow_module_level=True)


@pytest.fixture(scope="module")
def db():
    return DoseResponseDB()


def test_geldanamycin_monotonic_dose_response(db):
    dr = db.dose_response("geldanamycin")
    assert dr["spearman"] >= 0.6            # 单调剂量-响应(实测 ~0.9)


def test_geldanamycin_case_accept(db):
    report, dec = run_drug_dose_case({
        "case_id": "S_geld_dose", "species": "human", "perturbation_object": "drug",
        "perturbation_targets": ["geldanamycin"], "target_output": "expression",
    }, db=db)
    validate_case_report(report)
    d = report.to_dict()
    assert dec.engine == "embedding"
    assert d["reliability_decision"]["disposition"] == "accept"


def test_sirolimus_case_downgrade(db):
    # sirolimus 无剂量单调(Spearman<0.3)→ 不硬说剂量依赖
    report, _ = run_drug_dose_case({
        "species": "human", "perturbation_object": "drug",
        "perturbation_targets": ["sirolimus"], "target_output": "expression",
    }, db=db)
    assert report.to_dict()["reliability_decision"]["disposition"] in ("downgrade", "caution")


def test_unknown_drug_abstains(db):
    report, _ = run_drug_dose_case({
        "species": "human", "perturbation_object": "drug",
        "perturbation_targets": ["notadrug"], "target_output": "expression",
    }, db=db)
    assert report.to_dict()["reliability_decision"]["disposition"] == "abstain"
