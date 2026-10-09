"""Phase 7:SelfTrainedWrapper —— 自训模型(第一个真实样板 norman_mean_baseline)收编为 ModelWrapper。
本地(无 torch)可测:declare_scope/declare_provenance 契约(type=self_trained + 真锚点 ΔPearson 0.4615)、
estimate_uncertainty 诚实点估计、缺 torch/未声明 ckpt → run_prediction fail-closed(不静默返回假 delta)。
真训 + 真推理(load donor + mean_delta)是 .53 的事 → Task 7.5 gated。"""
import importlib.util

import pytest

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper
from praxis_virtualcell.model_zoo.wrappers.self_trained_wrapper import SelfTrainedWrapper

_HAS_TORCH = importlib.util.find_spec("torch") is not None


def test_is_model_wrapper_subclass():
    assert issubclass(SelfTrainedWrapper, ModelWrapper)


def test_declare_scope_human_genetic_hub():
    scope = SelfTrainedWrapper().declare_scope()
    assert scope["module"] == "genetic_hub"          # 对齐 registry.yaml norman_mean_baseline.module
    assert "human" in scope["species"]
    assert "predict_delta_expression" in scope["task"]
    assert "gene" in scope["perturbation"]


def test_declare_provenance_self_trained_with_honest_baseline_anchor():
    prov = SelfTrainedWrapper().declare_provenance()
    assert prov["model"] == "norman_mean_baseline"
    assert prov["type"] == "self_trained"            # 自训,非 public_model
    # 真锚点:mean_baseline.py 实测 per-cell ΔPearson 0.4615(同表 A 口径,与 base 可比)
    assert prov["metrics"]["delta_pearson"] == pytest.approx(0.4615, abs=1e-4)
    assert prov["metrics"]["cosine"] == pytest.approx(0.9850, abs=1e-4)
    assert prov["metrics"]["n"] == 18874
    # 诚实:naive baseline,低于 trained predictors by design(下界)
    assert prov["is_naive_lower_bound_baseline"] is True
    assert "remote_env" in prov                      # 数据/env/脚本坐标进 provenance(挪出硬编码)


def test_estimate_uncertainty_is_honest_point_estimate():
    """mean baseline 确定性点估计 → available=False + method=point_estimate(不假造 CI)。"""
    unc = SelfTrainedWrapper().estimate_uncertainty({}, None)
    assert unc["available"] is False
    assert unc["method"] == "point_estimate"


@pytest.mark.skipif(_HAS_TORCH, reason="本地无 torch 才测 fail-closed;有 torch 时真推理走 Task 7.5 gated")
def test_run_prediction_fail_closed_without_torch():
    """红线 6:缺 torch → run_prediction 抛(不静默返回假 delta 冒充可用)。"""
    w = SelfTrainedWrapper(ckpt_stem="/nonexistent/mean_delta")  # 有 ckpt 声明才走到 torch import
    with pytest.raises(Exception) as ei:
        w.run_prediction({"targets": ["AHR"]})
    msg = str(ei.value).lower()
    assert "torch" in msg or "no module" in msg or "mean_baseline" in msg


def test_run_prediction_fail_closed_without_ckpt():
    """未声明 ckpt(未训/未落盘)→ run_prediction 抛(fail-closed,不静默)。本地无 torch 也先撞这条。"""
    w = SelfTrainedWrapper(ckpt_stem=None)
    with pytest.raises(Exception) as ei:
        w.run_prediction({"targets": ["AHR"]})
    assert "ckpt" in str(ei.value).lower() or "not trained" in str(ei.value).lower() \
        or "未训" in str(ei.value) or "torch" in str(ei.value).lower()


@pytest.mark.skipif(_HAS_TORCH, reason="本地无 torch 才测 handle fail-closed 归 failed")
def test_handle_degrades_to_failed_without_torch():
    """缺 torch 时经 bus handle → status=failed（继承 PredictorAgent fail-closed），prediction=None。"""
    from praxis_virtualcell.core.bus import MessageBus
    from praxis_virtualcell.core.message import AgentMessage

    bus = MessageBus()
    bus.send(AgentMessage("b0", "SpeciesBrain", "X", "brain_retrieved", {}, "t0"))
    w = SelfTrainedWrapper(ckpt_stem="/nonexistent/mean_delta")
    req = {"species": "human", "input_modality": "scRNA",
           "task_type": "predict_delta_expression", "perturbation_type": "gene",
           "perturbation_targets": ["AHR"]}
    bc = {"species": "human",
          "model_applicability": {"SelfTrainedWrapper": {"supported_species": ["human"],
              "supported_modalities": ["scRNA"], "supported_tasks": ["predict_delta_expression"]}},
          "rules_referenced": ["r1"]}
    w.handle(AgentMessage("m1", "X", "SelfTrainedWrapper", "predict",
                          {"request": req, "brain_context": bc}, "t1"), bus)
    res = bus.latest("predictor_result").payload
    assert res["status"] == "failed"                 # 不是 success、不是静默 accept
    assert res["prediction"] is None


def test_no_llm_import_in_module():
    import praxis_virtualcell.model_zoo.wrappers.self_trained_wrapper as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_orchestration" not in src
