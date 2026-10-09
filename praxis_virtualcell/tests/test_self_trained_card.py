"""Phase 2:self_trained 模型必须有 training_card(training_data/split/baseline/metrics/provenance)。
铁律:无 provenance 的自训模型不入库(fail-closed)。测:合法通过;缺 card → ValueError;缺字段 → ValueError。"""
import pytest

from praxis_virtualcell.model_zoo.registry import ModelZooRegistry


def _write(tmp_path, card_block: str) -> str:
    p = tmp_path / "reg.yaml"
    p.write_text(
        "models:\n"
        "  yst:\n"
        "    name: yst\n"
        "    type: self_trained\n"
        "    species: [yeast]\n"
        "    module: genetic_hub\n"
        "    task: deletion_fitness\n"
        "    source: 'self_trained:yst'\n"
        "    license: internal\n"
        "    status: planned\n"
        "    wrapper: x.Y\n"
        "    version: v0\n"
        "    requires: [torch]\n"
        "    reliability_policy: ml_disagreement\n"
        + card_block,
        encoding="utf-8")
    return str(p)


def test_self_trained_with_full_card_loads(tmp_path):
    card = (
        "    training_card:\n"
        "      training_data: SGD deletion library\n"
        "      split: by-gene holdout\n"
        "      baseline: mean-fitness\n"
        "      metrics: {pearson: null}\n"
        "      provenance: planned\n"
    )
    reg = ModelZooRegistry(registry_path=_write(tmp_path, card))
    assert reg.get("yst")["training_card"]["split"] == "by-gene holdout"


def test_self_trained_without_card_is_rejected(tmp_path):
    with pytest.raises(ValueError) as ei:
        ModelZooRegistry(registry_path=_write(tmp_path, ""))
    assert "training_card" in str(ei.value)


def test_self_trained_card_missing_field_is_rejected(tmp_path):
    card = (
        "    training_card:\n"
        "      training_data: SGD deletion library\n"
        "      split: by-gene holdout\n"
        # 缺 baseline / metrics / provenance
    )
    with pytest.raises(ValueError) as ei:
        ModelZooRegistry(registry_path=_write(tmp_path, card))
    assert "training_card" in str(ei.value)


def test_public_model_needs_no_card(tmp_path):
    """public_model 不要求 training_card(只 self_trained 要求)。"""
    p = tmp_path / "reg.yaml"
    p.write_text(
        "models:\n"
        "  pub:\n"
        "    name: pub\n"
        "    type: public_model\n"
        "    species: [bacteria]\n"
        "    module: cytoplasmic_metabolism\n"
        "    task: growth\n"
        "    source: cobra_bundled_textbook\n"
        "    license: MIT\n"
        "    status: available\n"
        "    wrapper: x.Y\n"
        "    version: v1\n"
        "    requires: [cobra]\n"
        "    reliability_policy: gem_growth\n",
        encoding="utf-8")
    reg = ModelZooRegistry(registry_path=str(p))
    assert reg.get("pub")["type"] == "public_model"
