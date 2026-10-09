"""Phase 6:GearsWrapper —— 把 .53 上真跑的 GEARS 收编为 ModelWrapper 插件。
本地(无 torch)可测:declare_scope/declare_provenance 契约、estimate_uncertainty 诚实点估计、
缺 torch → run_prediction fail-closed(不静默返回 mock 0.4 冒充真 GEARS)。
真推理(load ckpt + GEARS predict)是 .53 的事 → Task 6.5 gated。"""
import importlib.util

import pytest

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper
from praxis_virtualcell.model_zoo.wrappers.gears_wrapper import GearsWrapper

_HAS_TORCH = importlib.util.find_spec("torch") is not None


def test_is_model_wrapper_subclass():
    assert issubclass(GearsWrapper, ModelWrapper)


def test_declare_scope_human_genetic_hub():
    scope = GearsWrapper().declare_scope()
    assert scope["module"] == "genetic_hub"          # 对齐 registry.yaml gears.module
    assert "human" in scope["species"]
    assert "perturbation_response" in scope["task"]
    assert "gene" in scope["perturbation"]


def test_declare_provenance_has_gears_anchor_and_honest_flags():
    prov = GearsWrapper().declare_provenance()
    assert prov["model"] == "gears"
    # 锚点:GEARS native pearson_de 0.8392(finding_w4c_gears)
    assert prov["metrics"]["pearson_de"] == pytest.approx(0.8392, abs=1e-4)
    # 诚实:与 donor base 不可比 + 同表 ΔPearson 未做(backlog)
    assert prov["not_comparable_to_donor_base"] is True
    assert prov["metrics"]["comparable_delta_pearson"] is None
    assert "remote_env" in prov                      # 远端坐标进 provenance(挪出硬编码)


def test_estimate_uncertainty_is_honest_point_estimate():
    """GEARS 无标定不确定性 → available=False + method=point_estimate(不假造 CI)。"""
    unc = GearsWrapper().estimate_uncertainty({}, None)
    assert unc["available"] is False
    assert unc["method"] == "point_estimate"


@pytest.mark.skipif(_HAS_TORCH, reason="本地无 torch 才测 fail-closed;有 torch 时真推理走 Task 6.5 gated")
def test_run_prediction_fail_closed_without_torch():
    """红线 6:缺 torch → run_prediction 抛(不静默返回 mock 0.4 冒充可用)。"""
    with pytest.raises(Exception) as ei:
        GearsWrapper().run_prediction({"targets": ["AHR"]})
    msg = str(ei.value).lower()
    assert "torch" in msg or "gears" in msg or "no module" in msg


@pytest.mark.skipif(_HAS_TORCH, reason="本地无 torch 才测 handle fail-closed 归 failed")
def test_handle_degrades_to_failed_without_torch():
    """缺 torch 时经 bus handle → status=failed（继承 PredictorAgent fail-closed），prediction=None。"""
    from praxis_virtualcell.core.bus import MessageBus
    from praxis_virtualcell.core.message import AgentMessage

    bus = MessageBus()
    bus.send(AgentMessage("b0", "SpeciesBrain", "X", "brain_retrieved", {}, "t0"))
    w = GearsWrapper()
    req = {"species": "human", "input_modality": "scRNA",
           "task_type": "perturbation_response", "perturbation_type": "gene",
           "perturbation_targets": ["AHR"]}
    bc = {"species": "human",
          "model_applicability": {"GearsWrapper": {"supported_species": ["human"],
              "supported_modalities": ["scRNA"], "supported_tasks": ["perturbation_response"]}},
          "rules_referenced": ["r1"]}
    w.handle(AgentMessage("m1", "X", "GearsWrapper", "predict",
                          {"request": req, "brain_context": bc}, "t1"), bus)
    res = bus.latest("predictor_result").payload
    assert res["status"] == "failed"                 # 不是 success、不是静默 accept
    assert res["prediction"] is None


def test_no_llm_import_in_module():
    import praxis_virtualcell.model_zoo.wrappers.gears_wrapper as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_orchestration" not in src
