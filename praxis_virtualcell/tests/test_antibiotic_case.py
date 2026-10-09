"""Tests for antibiotic case."""
import pytest

pytest.importorskip("cobra")

from praxis_virtualcell.agents.case_report import validate_case_report
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.predictors.mechanistic.antibiotic import (
    _IML1515,
    _gem,
    run_antibiotic_case,
)

if not _IML1515.is_file():
    pytest.skip(f"iML1515 unavailable({_IML1515})", allow_module_level=True)


@pytest.fixture(scope="module")
def gem():
    return _gem()


def test_route_bacteria_drug_growth_to_gem():
    d = route(normalize_request({"species": "bacteria", "perturbation_object": "drug",
                                 "perturbation_targets": ["trimethoprim"], "target_output": "growth"}))
    assert d.engine == "gem_fba"


def test_trimethoprim_growth_arrest(gem):
    report, dec = run_antibiotic_case({
        "case_id": "S_tmp", "species": "bacteria", "cell_type": "E. coli",
        "perturbation_object": "drug", "perturbation_targets": ["trimethoprim"],
        "target_output": "growth",
    }, gem=gem)
    validate_case_report(report)
    d = report.to_dict()
    assert dec.engine == "gem_fba"
    r = d["raw_output"]["antibiotics"][0]
    assert r["target_rxn"] == "DHFR" and r["growth_arrest"] is True
    assert d["reliability_decision"]["disposition"] == "accept"


def test_sulfamethoxazole_growth_arrest(gem):
    report, _ = run_antibiotic_case({
        "species": "bacteria", "cell_type": "E. coli", "perturbation_object": "drug",
        "perturbation_targets": ["sulfamethoxazole"], "target_output": "growth",
    }, gem=gem)
    r = report.to_dict()["raw_output"]["antibiotics"][0]
    assert r["target_rxn"] == "DHPS2" and r["growth_arrest"] is True


def test_non_metabolic_target_abstains(gem):

    report, _ = run_antibiotic_case({
        "species": "bacteria", "cell_type": "E. coli", "perturbation_object": "drug",
        "perturbation_targets": ["ciprofloxacin"], "target_output": "growth",
    }, gem=gem)
    d = report.to_dict()
    assert d["reliability_decision"]["disposition"] == "abstain"
    assert "non_metabolic_target" in str(d["reliability_decision"]["caution_flags"])


def test_unknown_antibiotic_abstains(gem):
    report, _ = run_antibiotic_case({
        "species": "bacteria", "cell_type": "E. coli", "perturbation_object": "drug",
        "perturbation_targets": ["notanantibiotic"], "target_output": "growth",
    }, gem=gem)
    assert report.to_dict()["reliability_decision"]["disposition"] == "abstain"
