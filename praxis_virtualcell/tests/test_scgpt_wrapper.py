"""Tests for scgpt wrapper."""
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

    assert prov["metrics"]["delta_pearson"] == pytest.approx(0.4407, abs=1e-4)
    assert prov["metrics"]["cosine"] == pytest.approx(0.9808, abs=1e-4)
    assert prov["metrics"]["n"] == 7290

    assert prov["frozen_backbone_underperforms"] is True

    assert "pretrained_backbone" in prov["remote_env"]["ckpt"]


def test_declare_provenance_comparable_to_donor_base():
    """Verify declare provenance comparable to donor base."""
    prov = ScgptWrapper().declare_provenance()
    assert prov.get("not_comparable_to_donor_base", False) is False


def test_estimate_uncertainty_is_honest_point_estimate():
    unc = ScgptWrapper().estimate_uncertainty({}, None)
    assert unc["available"] is False
    assert unc["method"] == "point_estimate"


@pytest.mark.skipif(_HAS_TORCH, reason="Requires a torch-free environment; real inference is dependency gated.")
def test_run_prediction_fail_closed_without_torch():
    """Verify run prediction fail closed without torch."""
    with pytest.raises(Exception) as ei:
        ScgptWrapper().run_prediction({"targets": ["AHR"]})
    msg = str(ei.value).lower()
    assert "torch" in msg or "scgpt" in msg or "no module" in msg or "ckpt" in msg


@pytest.mark.skipif(_HAS_TORCH, reason="This test checks that missing torch produces a failed result")
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
