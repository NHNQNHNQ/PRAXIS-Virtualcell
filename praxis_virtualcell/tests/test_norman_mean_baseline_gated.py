"""Phase 7:norman_mean_baseline —— 第一个真实自训模型样板(mean-perturbation naive baseline)。
离线可测:registry 条目 schema(self_trained + training_card 真值 + assets sha 占位)、broker
对它 fail-closed(status=planned/sha 占位)。真训(compute_mean_delta 落盘)+ 真评(score_mean_baseline
复算 ΔPearson 0.4615)是 .53 的事 → @pytest.mark.remote gated(本地无 torch skip,skip 基线 27→29)。"""
import importlib.util

import pytest

from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry

_HAS_TORCH = importlib.util.find_spec("torch") is not None


def _ask(name):
    return AgentMessage("q1", "Client", "ModelBrokerAgent", "model_request", {"model_name": name}, "t1")


# ---- 离线:registry 条目 + broker fail-closed（计入 passed）----

def test_registry_has_norman_mean_baseline_self_trained():
    reg = ModelZooRegistry()                          # 默认 model_zoo/registry.yaml
    e = reg.get("norman_mean_baseline")
    assert e["type"] == "self_trained"
    assert e["species"] == ["human"]
    assert e["module"] == "genetic_hub"
    assert e["task"] == "predict_delta_expression"
    assert e["wrapper"].endswith("self_trained_wrapper.SelfTrainedWrapper")


def test_registry_training_card_has_real_anchor():
    """training_card metrics 是真值 ΔPearson 0.4615(mean_baseline.py 实测),不是 null 占位。"""
    card = ModelZooRegistry().get("norman_mean_baseline")["training_card"]
    assert card["metrics"]["delta_pearson"] == pytest.approx(0.4615, abs=1e-4)
    assert card["metrics"]["n"] == 18874
    assert "norman" in card["training_data"].lower()


def test_broker_norman_mean_baseline_fail_closed():
    """status=planned(ckpt 未落 + sha 占位)→ broker fail-closed(红线 6:自训未产品化不静默 accept)。"""
    bus = MessageBus()
    ModelBrokerAgent().handle(_ask("norman_mean_baseline"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert p["wrapper"].endswith("self_trained_wrapper.SelfTrainedWrapper")  # 路径仍可见


def test_yeast_deletion_fitness_still_planned_no_data():
    """种子 yeast 仍 planned + 诚实标无 SGD 数据(不假造已训)。"""
    e = ModelZooRegistry().get("yeast_deletion_fitness")
    assert e["status"] == "planned"
    prov = str(e["training_card"]["provenance"]).lower()
    assert "planned" in prov or "no weights" in prov


def test_norman_mean_baseline_source_self_trained_fail_closed():
    """norman_mean_baseline status=planned + source=self_trained:* → broker fail-closed(多关兜底)。"""
    bus = MessageBus()
    ModelBrokerAgent().handle(_ask("norman_mean_baseline"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert p["reason"]


# ---- gated:真训 + 真评（.53 跑,本地无 torch skip,计入 skipped）----

pytestmark_remote = pytest.mark.remote


@pytest.mark.remote
def test_real_train_mean_delta_and_score():
    """真训 + 真评(.53 virtualcell env):compute_mean_delta 训练集算 mean_delta → 落盘 →
    score_mean_baseline 在 donor norman test split 复算 per-cell ΔPearson,pin 0.4615(±容差)。
    缺 torch(Mac)→ conftest 自动 skip。绝不 mock donor 数据凑绿(红线 5)。"""
    import torch  # noqa: F401 — 缺 torch → remote marker 已 skip,到不了这

    from praxis_virtualcell.benchmarks.mean_baseline import score_mean_baseline

    res = score_mean_baseline(test_seed=1, train_seed=0)
    # mean_baseline.py docstring 实测锚点:ΔPearson 0.4615 / cosine 0.9850 / n 18874
    assert res["delta_pearson"] == pytest.approx(0.4615, abs=5e-3)   # 宽容度:donor 数据/seed 微扰
    assert res["n"] > 10000


@pytest.mark.remote
def test_real_selftrained_wrapper_run_prediction():
    """真推理(.53):SelfTrainedWrapper(ckpt=落盘 mean_delta)+ 注入 donor control ctx →
    run_prediction 返回 mean_baseline delta(n_genes=2000)。缺 torch → skip。"""
    import torch

    from praxis_virtualcell.model_zoo.wrappers.self_trained_wrapper import SelfTrainedWrapper

    # 执行者在 .53 补:落盘 mean_delta ckpt 路径 + donor norman control tensor 注入 _context。
    ckpt = __import__("os").environ.get("P7_MEAN_DELTA_CKPT")
    if not ckpt:
        pytest.skip("需 P7_MEAN_DELTA_CKPT env(.53 落盘 mean_delta 路径)")
    w = SelfTrainedWrapper(ckpt_stem=ckpt)
    ctx = torch.zeros(2000)                            # 执行者换成真 donor control(zeros 仅占位验形状)
    out = w.run_prediction({"targets": ["AHR"], "_context": ctx})
    assert out["prediction"]["n_genes"] == 2000
    assert out["prediction"]["is_naive_lower_bound_baseline"] is True
    assert out["uncertainty"]["available"] is False   # 点估计诚实
