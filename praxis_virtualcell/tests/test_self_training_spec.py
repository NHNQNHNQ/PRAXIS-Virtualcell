"""Phase 7:SelfTrainingSpec —— 自训模型的声明式训练契约(training_data/split/baseline/metrics/
provenance + 远端脚本坐标)。fail-closed:缺必填 / metrics 非 dict / 空字段 → ValueError。
to_training_card() 产 registry.yaml training_card 五键 dict(单一真相源)。"""
import pytest

from praxis_virtualcell.model_zoo.training.spec import SelfTrainingSpec


def _norman_mean_spec_kwargs():
    return dict(
        name="norman_mean_baseline",
        training_data="donor norman_2019 (Perturb-seq K562); mean_delta over non-control cells",
        split="by-cell seed split (train seed 0 / test seed 1)",
        baseline="N/A — this model IS the naive lower-bound baseline",
        metrics={"delta_pearson": 0.4615, "cosine": 0.9850, "n": 18874},
        provenance="mean_baseline.py scored on .53 virtualcell env; ckpt fetch gated",
        training_script="praxis_virtualcell.benchmarks.mean_baseline",
        remote_env={"host": "zkyd@10.102.106.53", "conda_env": "virtualcell"},
    )


def test_valid_spec_constructs():
    spec = SelfTrainingSpec(**_norman_mean_spec_kwargs())
    assert spec.name == "norman_mean_baseline"
    assert spec.metrics["delta_pearson"] == pytest.approx(0.4615, abs=1e-4)


def test_to_training_card_has_five_registry_keys():
    """to_training_card 产 registry.yaml training_card 必需五键(与 registry._validate required_card 一致)。"""
    card = SelfTrainingSpec(**_norman_mean_spec_kwargs()).to_training_card()
    for k in ("training_data", "split", "baseline", "metrics", "provenance"):
        assert k in card
    assert card["metrics"]["delta_pearson"] == pytest.approx(0.4615, abs=1e-4)


def test_missing_required_field_fail_closed():
    kw = _norman_mean_spec_kwargs()
    del kw["split"]
    with pytest.raises(TypeError):                   # 缺必填位置/关键字参数 → 构造失败
        SelfTrainingSpec(**kw)


def test_empty_string_field_fail_closed():
    """空字符串字段(training_data="")→ ValueError(不静默接受空契约)。"""
    kw = _norman_mean_spec_kwargs()
    kw["training_data"] = ""
    with pytest.raises(ValueError) as ei:
        SelfTrainingSpec(**kw)
    assert "training_data" in str(ei.value)


def test_metrics_must_be_dict_fail_closed():
    """metrics 非 dict(如 str)→ ValueError(fail-closed)。"""
    kw = _norman_mean_spec_kwargs()
    kw["metrics"] = "0.4615"
    with pytest.raises(ValueError) as ei:
        SelfTrainingSpec(**kw)
    assert "metrics" in str(ei.value)


def test_planned_spec_allows_null_metrics():
    """planned 自训(如 yeast,未训)允许 metrics 值为 null,但 metrics 仍须是 dict + 有 note。
    诚实:planned 不假造数字,但契约结构完整(fail-closed 只拦结构坏,不拦'诚实未训')。"""
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
