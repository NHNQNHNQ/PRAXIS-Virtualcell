"""Tests for training card field validation."""
import pytest

from praxis_virtualcell.model_zoo.registry import ModelZooRegistry


def _write(tmp_path, card_block: str) -> str:
    p = tmp_path / "reg.yaml"
    p.write_text(
        "models:\n"
        "  yst:\n"
        "    name: yst\n    type: self_trained\n    species: [yeast]\n"
        "    module: genetic_hub\n    task: deletion_fitness\n    source: 'self_trained:yst'\n"
        "    license: internal\n    status: planned\n    wrapper: x.Y\n    version: v0\n"
        "    requires: [torch]\n    reliability_policy: ml_disagreement\n"
        + card_block,
        encoding="utf-8")
    return str(p)


def test_metrics_non_dict_rejected(tmp_path):
    """Verify metrics non dict rejected."""
    card = (
        "    training_card:\n"
        "      training_data: SGD deletion library\n"
        "      split: by-gene holdout\n"
        "      baseline: mean-fitness\n"
        "      metrics: oops-not-a-dict\n"
        "      provenance: planned\n"
    )
    with pytest.raises(ValueError) as ei:
        ModelZooRegistry(registry_path=_write(tmp_path, card))
    assert "metrics" in str(ei.value)


def test_empty_split_rejected(tmp_path):
    """Verify empty split rejected."""
    card = (
        "    training_card:\n"
        "      training_data: SGD deletion library\n"
        "      split: ''\n"
        "      baseline: mean-fitness\n"
        "      metrics: {pearson: null}\n"
        "      provenance: planned\n"
    )
    with pytest.raises(ValueError) as ei:
        ModelZooRegistry(registry_path=_write(tmp_path, card))
    assert "split" in str(ei.value)


def test_planned_null_metrics_still_valid(tmp_path):
    """Verify planned null metrics still valid."""
    card = (
        "    training_card:\n"
        "      training_data: SGD deletion library (planned)\n"
        "      split: by-gene holdout (planned)\n"
        "      baseline: mean-fitness\n"
        "      metrics: {pearson: null, note: planned}\n"
        "      provenance: planned; no weights yet\n"
    )
    reg = ModelZooRegistry(registry_path=_write(tmp_path, card))
    assert reg.get("yst")["training_card"]["metrics"]["pearson"] is None


def test_full_valid_card_still_loads(tmp_path):
    """Verify full valid card still loads."""
    card = (
        "    training_card:\n"
        "      training_data: donor norman_2019\n"
        "      split: by-cell seed split\n"
        "      baseline: naive lower bound\n"
        "      metrics: {delta_pearson: 0.4615, n: 18874}\n"
        "      provenance: scored on .53\n"
    )
    reg = ModelZooRegistry(registry_path=_write(tmp_path, card))
    assert reg.get("yst")["training_card"]["metrics"]["delta_pearson"] == 0.4615
