"""Tests for ecoli gem case."""
import pytest

cobra = pytest.importorskip("cobra")

from praxis_virtualcell.agents.case_report import validate_case_report  # noqa: E402
from praxis_virtualcell.predictors.mechanistic.ecoli_gem import EcoliGEM, run_ecoli_growth_case  # noqa: E402


@pytest.fixture(scope="module")
def gem():
    return EcoliGEM()


def test_wt_growth_known_value(gem):
    assert gem.wt_growth == pytest.approx(0.8739, abs=1e-3)   # textbook e_coli_core WT


def test_gltA_essential(gem):
    r = gem.knockout("b0720")
    assert r.in_model and r.essential and r.growth == pytest.approx(0.0, abs=1e-6)


def test_nonessential_gene_grows(gem):
    r = gem.knockout("b0356")
    assert r.in_model and not r.essential and r.ratio > 0.5


def test_gene_not_in_model_flagged(gem):
    r = gem.knockout("ZZZ_notagene")
    assert r.in_model is False and r.growth is None and r.essential is None


def test_full_case_7parts_real_numbers(gem):
    report, dec = run_ecoli_growth_case({
        "case_id": "C4_ecoli_ko_growth", "species": "bacteria", "cell_type": "E. coli",
        "perturbation_object": "gene", "perturbation_targets": ["b0720", "b1136", "b0356"],
        "target_output": "growth", "medium": "glucose_minimal",
    }, gem=gem)
    validate_case_report(report)
    d = report.to_dict()
    assert dec.engine == "gem_fba"
    assert d["models_tools_selected"]["method"].startswith("FBA")
    kos = {k["gene"]: k for k in d["raw_output"]["knockouts"]}
    assert kos["b0720"]["essential"] is True
    assert kos["b1136"]["essential"] is True
    assert d["reliability_decision"]["disposition"] == "accept"
    assert d["baseline_comparison"]["essential_count"] >= 2


def test_case_downgrades_when_gene_missing(gem):
    report, _ = run_ecoli_growth_case({
        "species": "bacteria", "cell_type": "E. coli", "perturbation_object": "gene",
        "perturbation_targets": ["b0720", "ZZZ_notagene"], "target_output": "growth",
    }, gem=gem)

    assert report.to_dict()["reliability_decision"]["disposition"] == "caution"


def test_all_missing_abstains(gem):
    report, _ = run_ecoli_growth_case({
        "species": "bacteria", "cell_type": "E. coli", "perturbation_object": "gene",
        "perturbation_targets": ["ZZZ1", "ZZZ2"], "target_output": "growth",
    }, gem=gem)
    assert report.to_dict()["reliability_decision"]["disposition"] == "abstain"
