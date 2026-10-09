"""Tests for drug dose case."""
import pytest

from praxis_virtualcell.agents.case_report import validate_case_report
from praxis_virtualcell.predictors.embedding.drug_dose import (
    _DEFAULT_SUBSET,
    DoseResponseDB,
    run_drug_dose_case,
)

if not _DEFAULT_SUBSET.is_file():
    pytest.skip(f"dose subset unavailable({_DEFAULT_SUBSET})", allow_module_level=True)


@pytest.fixture(scope="module")
def db():
    return DoseResponseDB()


def test_geldanamycin_monotonic_dose_response(db):
    dr = db.dose_response("geldanamycin")
    assert dr["spearman"] >= 0.6


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
