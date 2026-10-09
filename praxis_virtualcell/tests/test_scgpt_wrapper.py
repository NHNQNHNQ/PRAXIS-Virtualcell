"""Phase 6:ScgptWrapper —— 把 .53 上真跑的 scGPT(frozen backbone + head)收编为 ModelWrapper。
本地(无 torch)可测:scope/provenance 契约、诚实点估计 uncertainty、缺 torch → run_prediction
fail-closed(不静默返回假 delta)。真推理(load 196MB ckpt + MLPredictorAgent)是 .53 → Task 6.5 gated。
scGPT 接口已同构 donor(finding_w4c_scgpt:predict_tensor==donor predict),故真推理复用
build_predictor_from_ckpt + MLPredictorAgent,不重写 ML 内核。"""
import importlib.util

import pytest

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper
from praxis_virtualcell.model_zoo.wrappers.scgpt_wrapper import ScgptWrapper

_HAS_TORCH = importlib.util.find_spec("torch") is not None


def test_is_model_wrapper_subclass():
    assert issubclass(ScgptWrapper, ModelWrapper)


def test_declare_scope_human_genetic_hub():
    scope = ScgptWrapper().declare_scope()
    assert scope["module"] == "genetic_hub"
    assert "human" in scope["species"]
    assert "predict_delta_expression" in scope["task"]


def test_declare_provenance_has_scgpt_anchor_and_honest_flags():
    prov = ScgptWrapper().declare_provenance()
    assert prov["model"] == "scgpt"
    # 锚点:scGPT ΔPearson 0.4407(donor norman test split,同表 A 口径可比)
    assert prov["metrics"]["delta_pearson"] == pytest.approx(0.4407, abs=1e-4)
    assert prov["metrics"]["cosine"] == pytest.approx(0.9808, abs=1e-4)
    assert prov["metrics"]["n"] == 7290
    # 诚实:frozen backbone 偏低,SOTA 需 fine-tune(backlog)
    assert prov["frozen_backbone_underperforms"] is True
    # ckpt 坐标进 provenance(挪出硬编码)
    assert "pretrained_backbone" in prov["remote_env"]["ckpt"]


def test_declare_provenance_comparable_to_donor_base():
    """scGPT ΔPearson 与 donor base 同口径可比(与 GEARS 不同)。"""
    prov = ScgptWrapper().declare_provenance()
    assert prov.get("not_comparable_to_donor_base", False) is False


def test_estimate_uncertainty_is_honest_point_estimate():
    unc = ScgptWrapper().estimate_uncertainty({}, None)
    assert unc["available"] is False
    assert unc["method"] == "point_estimate"


@pytest.mark.skipif(_HAS_TORCH, reason="本地无 torch 才测 fail-closed;有 torch 时真推理走 Task 6.5 gated")
def test_run_prediction_fail_closed_without_torch():
    """红线 6:缺 torch → run_prediction 抛(不静默返回假 delta 冒充可用)。"""
    with pytest.raises(Exception) as ei:
        ScgptWrapper().run_prediction({"targets": ["AHR"]})
    msg = str(ei.value).lower()
    assert "torch" in msg or "scgpt" in msg or "no module" in msg or "ckpt" in msg


@pytest.mark.skipif(_HAS_TORCH, reason="本地无 torch 才测 handle fail-closed 归 failed")
def test_handle_degrades_to_failed_without_torch():
    from praxis_virtualcell.core.bus import MessageBus
    from praxis_virtualcell.core.message import AgentMessage

    bus = MessageBus()
    bus.send(AgentMessage("b0", "SpeciesBrain", "X", "brain_retrieved", {}, "t0"))
    w = ScgptWrapper()
    req = {"species": "human", "input_modality": "scRNA",
           "task_type": "predict_delta_expression", "perturbation_type": "gene",
           "perturbation_targets": ["AHR"]}
    bc = {"species": "human",
          "model_applicability": {"ScgptWrapper": {"supported_species": ["human"],
              "supported_modalities": ["scRNA"], "supported_tasks": ["predict_delta_expression"]}},
          "rules_referenced": ["r1"]}
    w.handle(AgentMessage("m1", "X", "ScgptWrapper", "predict",
                          {"request": req, "brain_context": bc}, "t1"), bus)
    res = bus.latest("predictor_result").payload
    assert res["status"] == "failed"
    assert res["prediction"] is None


def test_no_llm_import_in_module():
    import praxis_virtualcell.model_zoo.wrappers.scgpt_wrapper as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_orchestration" not in src
