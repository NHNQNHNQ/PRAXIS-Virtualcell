"""Tests for yeast gem case."""
import pytest

pytest.importorskip("cobra")

from praxis_virtualcell.agents.case_report import validate_case_report
from praxis_virtualcell.predictors.mechanistic.yeast_gem import (
    _DEFAULT_YEAST_SBML,
    YeastGEM,
    run_yeast_growth_case,
)

if not _DEFAULT_YEAST_SBML.is_file():
    pytest.skip(f"iMM904 SBML unavailable({_DEFAULT_YEAST_SBML})", allow_module_level=True)


@pytest.fixture(scope="module")
def gem():
    return YeastGEM()


def test_wt_growth_known_value(gem):
    assert gem.wt_growth == pytest.approx(0.2879, abs=1e-3)


def test_erg1_essential(gem):
    r = gem.knockout("YGR175C")
    assert r.in_model and r.essential and r.growth == pytest.approx(0.0, abs=1e-6)


def test_nonessential_gene_grows(gem):
    r = gem.knockout("YOR375C")
    assert r.in_model and not r.essential and r.ratio > 0.9


def test_gene_not_in_model_flagged(gem):
    r = gem.knockout("ZZZ_notagene")
    assert r.in_model is False and r.growth is None


def test_full_case_7parts_real_numbers(gem):
    report, dec = run_yeast_growth_case({
        "case_id": "C5_yeast_deletion_growth", "species": "yeast", "cell_type": "S. cerevisiae",
        "perturbation_object": "gene", "perturbation_targets": ["YGR175C", "YOR375C"],
        "target_output": "growth", "medium": "glucose_minimal",
    }, gem=gem)
    validate_case_report(report)
    d = report.to_dict()
    assert dec.engine == "gem_fba"
    assert "iMM904" in d["models_tools_selected"]["tool"]
    kos = {k["gene"]: k for k in d["raw_output"]["knockouts"]}
    assert kos["YGR175C"]["essential"] is True
    assert d["reliability_decision"]["disposition"] == "accept"


def test_case_abstains_when_all_missing(gem):
    report, _ = run_yeast_growth_case({
        "species": "yeast", "cell_type": "S. cerevisiae", "perturbation_object": "gene",
        "perturbation_targets": ["ZZZ1", "ZZZ2"], "target_output": "growth",
    }, gem=gem)
    assert report.to_dict()["reliability_decision"]["disposition"] == "abstain"
