"""Tests for drug signature case."""
import pytest

from praxis_virtualcell.agents.case_report import validate_case_report
from praxis_virtualcell.predictors.embedding.drug_signature import (
    _DEFAULT_SUBSET,
    DrugSignatureDB,
    run_drug_response_case,
)

if not _DEFAULT_SUBSET.is_file():
    pytest.skip(f"curated_subset.json unavailable({_DEFAULT_SUBSET})", allow_module_level=True)


@pytest.fixture(scope="module")
def db():
    return DrugSignatureDB()


def test_db_loads_curated_drugs(db):
    assert db.has("geldanamycin") and db.moa("geldanamycin") == "HSP90_inhibitor"
    assert db.has("vorinostat") and db.moa("vorinostat") == "HDAC_inhibitor"
    assert not db.has("aspirin")


def test_same_moa_more_similar_for_hsp90(db):

    same = db.similarity("geldanamycin", "tanespimycin")
    cross = db.similarity("geldanamycin", "vorinostat")
    assert same > cross


def test_geldanamycin_accept_moa_consistent(db):
    report, dec = run_drug_response_case({
        "case_id": "C6_drug", "species": "human", "cell_type": "A549",
        "perturbation_object": "drug", "perturbation_targets": ["geldanamycin"],
        "target_output": "expression",
    }, db=db)
    validate_case_report(report)
    d = report.to_dict()
    assert dec.engine == "embedding"
    assert d["reliability_decision"]["disposition"] == "accept"
    assert d["raw_output"]["per_drug"][0]["moa_enrichment"] > 1.5


def test_vorinostat_downgrade_weak_signal(db):

    report, _ = run_drug_response_case({
        "species": "human", "perturbation_object": "drug",
        "perturbation_targets": ["vorinostat"], "target_output": "expression",
    }, db=db)
    d = report.to_dict()
    assert d["reliability_decision"]["disposition"] == "downgrade"
    assert d["raw_output"]["per_drug"][0]["moa_enrichment"] < 1.5


def test_singleton_drug_downgrade_no_reference(db):

    report, _ = run_drug_response_case({
        "species": "human", "perturbation_object": "drug",
        "perturbation_targets": ["sirolimus"], "target_output": "expression",
    }, db=db)
    assert report.to_dict()["reliability_decision"]["disposition"] == "downgrade"


def test_unknown_drug_abstains(db):
    report, _ = run_drug_response_case({
        "species": "human", "perturbation_object": "drug",
        "perturbation_targets": ["notadrug123"], "target_output": "expression",
    }, db=db)
    assert report.to_dict()["reliability_decision"]["disposition"] == "abstain"


def test_case_has_provenance_and_boundary(db):
    report, _ = run_drug_response_case({
        "species": "human", "perturbation_object": "drug",
        "perturbation_targets": ["geldanamycin"], "target_output": "expression",
    }, db=db)
    pb = report.to_dict()["provenance_boundary"]
    assert "LINCS" in str(pb) and "boundary" in pb
