"""Tests for gears wrapper."""
import importlib.util

import pytest

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper
from praxis_virtualcell.model_zoo.wrappers.gears_wrapper import GearsWrapper

_HAS_TORCH = importlib.util.find_spec("torch") is not None


def test_is_model_wrapper_subclass():
    assert issubclass(GearsWrapper, ModelWrapper)


def test_declare_scope_human_genetic_hub():
    scope = GearsWrapper().declare_scope()
    assert scope["module"] == "genetic_hub"
    assert "human" in scope["species"]
    assert "perturbation_response" in scope["task"]
    assert "gene" in scope["perturbation"]


def test_declare_provenance_has_gears_anchor_and_honest_flags():
    prov = GearsWrapper().declare_provenance()
    assert prov["model"] == "gears"

    assert prov["metrics"]["pearson_de"] == pytest.approx(0.8392, abs=1e-4)

    assert prov["not_comparable_to_donor_base"] is True
    assert prov["metrics"]["comparable_delta_pearson"] is None
    assert "remote_env" in prov


def test_estimate_uncertainty_is_honest_point_estimate():
    """Verify estimate uncertainty is honest point estimate."""
    unc = GearsWrapper().estimate_uncertainty({}, None)
    assert unc["available"] is False
    assert unc["method"] == "point_estimate"


@pytest.mark.skipif(_HAS_TORCH, reason="Requires a torch-free environment; real inference is dependency gated.")
def test_run_prediction_fail_closed_without_torch():
    """Verify run prediction fail closed without torch."""
    with pytest.raises(Exception) as ei:
        GearsWrapper().run_prediction({"targets": ["AHR"]})
    msg = str(ei.value).lower()
    assert "torch" in msg or "gears" in msg or "no module" in msg


@pytest.mark.skipif(_HAS_TORCH, reason="This test checks that missing torch produces a failed result")
def test_handle_degrades_to_failed_without_torch():
    """Verify handle degrades to failed without torch."""
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
    assert res["status"] == "failed"
    assert res["prediction"] is None


def test_no_llm_import_in_module():
    import praxis_virtualcell.model_zoo.wrappers.gears_wrapper as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_orchestration" not in src
