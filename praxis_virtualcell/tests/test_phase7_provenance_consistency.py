"""Tests for provenance consistency."""
import pytest

from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
from praxis_virtualcell.model_zoo.training.spec import SelfTrainingSpec
from praxis_virtualcell.model_zoo.wrappers.self_trained_wrapper import SelfTrainedWrapper


def test_registry_wrapper_metric_anchor_aligned():
    """Verify registry wrapper metric anchor aligned."""
    reg_metrics = ModelZooRegistry().get("norman_mean_baseline")["training_card"]["metrics"]
    wrap_metrics = SelfTrainedWrapper().declare_provenance()["metrics"]
    assert reg_metrics["delta_pearson"] == pytest.approx(wrap_metrics["delta_pearson"], abs=1e-6)
    assert reg_metrics["n"] == wrap_metrics["n"]


def test_registry_wrapper_module_species_aligned():
    """Verify registry wrapper module species aligned."""
    e = ModelZooRegistry().get("norman_mean_baseline")
    scope = SelfTrainedWrapper().declare_scope()
    assert e["module"] == scope["module"]
    assert e["species"] == scope["species"]
    assert e["task"] in scope["task"]                 # registry task(str)∈ wrapper task(list)


def test_spec_to_card_matches_registry():
    """Verify spec to card matches registry."""
    reg_card = ModelZooRegistry().get("norman_mean_baseline")["training_card"]
    spec = SelfTrainingSpec(
        name="norman_mean_baseline",
        training_data=reg_card["training_data"], split=reg_card["split"],
        baseline=reg_card["baseline"], metrics=reg_card["metrics"], provenance=reg_card["provenance"],
        training_script="praxis_virtualcell.benchmarks.mean_baseline",
    )
    card = spec.to_training_card()
    assert card["metrics"]["delta_pearson"] == pytest.approx(reg_card["metrics"]["delta_pearson"], abs=1e-6)
    for k in ("training_data", "split", "baseline", "provenance"):
        assert card[k] == reg_card[k]


def test_wrapper_provenance_honest_flags():
    """Verify wrapper provenance honest flags."""
    prov = SelfTrainedWrapper().declare_provenance()
    assert prov["is_naive_lower_bound_baseline"] is True
    assert prov["distributable"] is False


def test_self_trained_wrapper_no_llm_import():
    import praxis_virtualcell.model_zoo.wrappers.self_trained_wrapper as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_orchestration" not in src


def test_training_spec_module_no_llm_import():
    import praxis_virtualcell.model_zoo.training.spec as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_orchestration" not in src
