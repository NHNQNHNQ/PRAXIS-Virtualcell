"""Tests for self training spec."""
import pytest

from praxis_virtualcell.model_zoo.training.spec import SelfTrainingSpec


def _norman_mean_spec_kwargs():
    return dict(
        name="norman_mean_baseline",
        training_data="donor norman_2019 (Perturb-seq K562); mean_delta over non-control cells",
        split="by-cell seed split (train seed 0 / test seed 1)",
        baseline="N/A — this model IS the naive lower-bound baseline",
        metrics={"delta_pearson": 0.4615, "cosine": 0.9850, "n": 18874},
        provenance="mean_baseline.py scored in the training fixture environment; checkpoint retrieval gated",
        training_script="praxis_virtualcell.benchmarks.mean_baseline",
        remote_env={"host": "trainer@training.example.invalid", "conda_env": "virtualcell"},
    )


def test_valid_spec_constructs():
    spec = SelfTrainingSpec(**_norman_mean_spec_kwargs())
    assert spec.name == "norman_mean_baseline"
    assert spec.metrics["delta_pearson"] == pytest.approx(0.4615, abs=1e-4)


def test_to_training_card_has_five_registry_keys():
    """Verify to training card has five registry keys."""
    card = SelfTrainingSpec(**_norman_mean_spec_kwargs()).to_training_card()
    for k in ("training_data", "split", "baseline", "metrics", "provenance"):
        assert k in card
    assert card["metrics"]["delta_pearson"] == pytest.approx(0.4615, abs=1e-4)


def test_missing_required_field_fail_closed():
    kw = _norman_mean_spec_kwargs()
    del kw["split"]
    with pytest.raises(TypeError):
        SelfTrainingSpec(**kw)


def test_empty_string_field_fail_closed():
    """Verify empty string field fail closed."""
    kw = _norman_mean_spec_kwargs()
    kw["training_data"] = ""
    with pytest.raises(ValueError) as ei:
        SelfTrainingSpec(**kw)
    assert "training_data" in str(ei.value)


def test_metrics_must_be_dict_fail_closed():
    """Verify metrics must be dict fail closed."""
    kw = _norman_mean_spec_kwargs()
    kw["metrics"] = "0.4615"
    with pytest.raises(ValueError) as ei:
        SelfTrainingSpec(**kw)
    assert "metrics" in str(ei.value)


def test_planned_spec_allows_null_metrics():
    """Verify planned spec allows null metrics."""
    spec = SelfTrainingSpec(
        name="yeast_deletion_fitness",
        training_data="SGD deletion library growth screens (planned — NOT YET AVAILABLE)",
        split="by-gene holdout (planned)",
        baseline="mean-fitness predictor",
        metrics={"pearson": None, "note": "planned, not yet trained — no SGD data"},
        provenance="planned; no weights yet",
        training_script="TBD (needs SGD data)",
        remote_env={},
    )
    assert spec.metrics["pearson"] is None
    assert spec.to_training_card()["metrics"]["note"].startswith("planned")


def test_no_llm_import_in_module():
    import praxis_virtualcell.model_zoo.training.spec as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_orchestration" not in src
