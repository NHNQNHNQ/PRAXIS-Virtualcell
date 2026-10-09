"""Tests for gem wrapper."""
import pytest

cobra = pytest.importorskip("cobra")

from praxis_virtualcell.model_zoo.wrappers.gem_wrapper import GemWrapper  # noqa: E402


@pytest.fixture(scope="module")
def wrapper():
    return GemWrapper()


def test_declare_scope_growth_bacteria_yeast(wrapper):
    scope = wrapper.declare_scope()
    assert scope["module"] == "cytoplasmic_metabolism"
    assert "bacteria" in scope["species"]
    assert "growth" in scope["task"]


def test_run_prediction_real_ko_essential(wrapper):

    out = wrapper.run_prediction({"targets": ["b0720"]})
    kos = {k["gene"]: k for k in out["prediction"]["knockouts"]}
    assert kos["b0720"]["in_model"] is True
    assert kos["b0720"]["essential"] is True


def test_gene_not_in_gem_not_fabricated(wrapper):

    out = wrapper.run_prediction({"targets": ["ZZZ_notagene"]})
    ko = out["prediction"]["knockouts"][0]
    assert ko["in_model"] is False
    assert ko["growth"] is None


def test_uncertainty_contract(wrapper):
    out = wrapper.run_prediction({"targets": ["b0720"]})
    unc = wrapper.estimate_uncertainty({"targets": ["b0720"]}, out["prediction"])

    assert "available" in unc
