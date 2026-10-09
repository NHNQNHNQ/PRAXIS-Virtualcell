"""Tests for emt case."""
import pytest

from praxis_virtualcell.agents.case_report import validate_case_report
from praxis_virtualcell.predictors.state.emt import _DEFAULT_SUBSET, EmtDB, run_emt_case

if not _DEFAULT_SUBSET.is_file():
    pytest.skip(f"mcfarland EMT subset unavailable({_DEFAULT_SUBSET})", allow_module_level=True)


@pytest.fixture(scope="module")
def db():
    return EmtDB()


def test_emt_separates_sarcoma_from_epithelial(db):
    res = db.emt_separation()
    assert res["mesenchymal_mean"] > res["epithelial_mean"]
    assert res["cohens_d"] > 1.0


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
    assert "characterizes EMT state" in str(report.to_dict()["provenance_boundary"])
