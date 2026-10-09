"""Tests for self trained wrapper."""
import importlib.util

import pytest

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper
from praxis_virtualcell.model_zoo.wrappers.self_trained_wrapper import SelfTrainedWrapper

_HAS_TORCH = importlib.util.find_spec("torch") is not None


def test_is_model_wrapper_subclass():
    assert issubclass(SelfTrainedWrapper, ModelWrapper)


def test_declare_scope_human_genetic_hub():
    scope = SelfTrainedWrapper().declare_scope()
    assert scope["module"] == "genetic_hub"
    assert "human" in scope["species"]
    assert "predict_delta_expression" in scope["task"]
    assert "gene" in scope["perturbation"]


def test_declare_provenance_self_trained_with_honest_baseline_anchor():
    prov = SelfTrainedWrapper().declare_provenance()
    assert prov["model"] == "norman_mean_baseline"
    assert prov["type"] == "self_trained"

    assert prov["metrics"]["delta_pearson"] == pytest.approx(0.4615, abs=1e-4)
    assert prov["metrics"]["cosine"] == pytest.approx(0.9850, abs=1e-4)
    assert prov["metrics"]["n"] == 18874

    assert prov["is_naive_lower_bound_baseline"] is True
    assert "remote_env" in prov


def test_estimate_uncertainty_is_honest_point_estimate():
    """Verify estimate uncertainty is honest point estimate."""
    unc = SelfTrainedWrapper().estimate_uncertainty({}, None)
    assert unc["available"] is False
    assert unc["method"] == "point_estimate"


@pytest.mark.skipif(_HAS_TORCH, reason="Requires a torch-free environment; real inference is dependency gated.")
def test_run_prediction_fail_closed_without_torch():
    """Verify run prediction fail closed without torch."""
    w = SelfTrainedWrapper(ckpt_stem="/nonexistent/mean_delta")
    with pytest.raises(Exception) as ei:
        w.run_prediction({"targets": ["AHR"]})
    msg = str(ei.value).lower()
    assert "torch" in msg or "no module" in msg or "mean_baseline" in msg


def test_run_prediction_fail_closed_without_ckpt():
    """Verify run prediction fail closed without ckpt."""
    w = SelfTrainedWrapper(ckpt_stem=None)
    with pytest.raises(Exception) as ei:
        w.run_prediction({"targets": ["AHR"]})
    assert "ckpt" in str(ei.value).lower() or "not trained" in str(ei.value).lower() \
        or "untrained" in str(ei.value).lower() or "torch" in str(ei.value).lower()


@pytest.mark.skipif(_HAS_TORCH, reason="This test checks that missing torch produces a failed result")
def test_handle_degrades_to_failed_without_torch():
    """Verify handle degrades to failed without torch."""
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
    assert res["status"] == "failed"
    assert res["prediction"] is None


def test_no_llm_import_in_module():
    import praxis_virtualcell.model_zoo.wrappers.self_trained_wrapper as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_orchestration" not in src
