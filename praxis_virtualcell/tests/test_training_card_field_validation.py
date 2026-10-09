"""Phase 7:registry training_card 内部字段类型校验(fail-closed 加固)。
现有校验只校五键存在;本 task 加:metrics 须 dict、split/baseline/training_data/provenance 非空。
坏 card(metrics 非 dict / 空 split)→ ValueError,不静默接受。合法(含 planned null metrics)→ 过。"""
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
    """metrics 是 str(非 dict)→ ValueError(fail-closed 加固)。"""
    card = (
        "    training_card:\n"
        "      training_data: SGD deletion library\n"
        "      split: by-gene holdout\n"
        "      baseline: mean-fitness\n"
        "      metrics: oops-not-a-dict\n"           # 坏:str 非 dict
        "      provenance: planned\n"
    )
    with pytest.raises(ValueError) as ei:
        ModelZooRegistry(registry_path=_write(tmp_path, card))
    assert "metrics" in str(ei.value)


def test_empty_split_rejected(tmp_path):
    """split 空字符串 → ValueError(不静默接受空契约字段)。"""
    card = (
        "    training_card:\n"
        "      training_data: SGD deletion library\n"
        "      split: ''\n"                          # 坏:空
        "      baseline: mean-fitness\n"
        "      metrics: {pearson: null}\n"
        "      provenance: planned\n"
    )
    with pytest.raises(ValueError) as ei:
        ModelZooRegistry(registry_path=_write(tmp_path, card))
    assert "split" in str(ei.value)


def test_planned_null_metrics_still_valid(tmp_path):
    """planned 自训 metrics 值可 null(诚实未训),只要 metrics 是 dict + 其余字段非空 → 过。
    关键:fail-closed 只拦'结构坏',不拦'诚实标注未训'(否则逼假造数字)。"""
    card = (
        "    training_card:\n"
        "      training_data: SGD deletion library (planned)\n"
        "      split: by-gene holdout (planned)\n"
        "      baseline: mean-fitness\n"
        "      metrics: {pearson: null, note: planned}\n"   # dict + null 值 OK
        "      provenance: planned; no weights yet\n"
    )
    reg = ModelZooRegistry(registry_path=_write(tmp_path, card))
    assert reg.get("yst")["training_card"]["metrics"]["pearson"] is None


def test_full_valid_card_still_loads(tmp_path):
    """回归:合法全 card(与 test_self_trained_card 同款)仍过(不误伤现有)。"""
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
