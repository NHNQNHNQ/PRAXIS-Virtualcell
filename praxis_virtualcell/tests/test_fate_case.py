"""Tests for fate case."""
import pytest

from praxis_virtualcell.agents.case_report import validate_case_report
from praxis_virtualcell.predictors.state.fate import _DEFAULT_SUBSET, FateDB, run_fate_case

if not _DEFAULT_SUBSET.is_file():
    pytest.skip(f"paul15 fate subset unavailable({_DEFAULT_SUBSET})", allow_module_level=True)


@pytest.fixture(scope="module")
def db():
    return FateDB()


def test_fate_separates_lineages(db):
    res = db.fate_separation()
    assert res["erythroid_mean"] > res["myeloid_mean"]
    assert res["cohens_d"] > 2.0


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
    }, db=db, ery_panel=["FAKE1", "FAKE2"])
    assert report.to_dict()["reliability_decision"]["disposition"] == "downgrade"


def test_lineage_composition(db):
    per = report_lineages(db)
    assert "erythroid" in per and "myeloid" in per


def report_lineages(db):
    return {c["lineage"] for c in db._d["cells"]}
