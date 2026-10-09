"""Tests for predictor mock marker."""
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.predictors.base import PredictorAgent
from praxis_virtualcell.predictors.mock_gears import MockGEARSAgent


def _bus_with_brain():
    bus = MessageBus()
    bus.send(AgentMessage("b1", "SpeciesBrain", "X", "brain_retrieved", {}, "t0"))
    return bus


def _payload(model_name):
    return {"request": {"species": "human", "input_modality": "scRNA",
                        "task_type": "predict_delta_expression", "perturbation_type": "gene",
                        "perturbation_targets": ["AHR"]},
            "brain_context": {"species": "human", "species_supported": True,
                              "model_applicability": {model_name: {"supported_species": ["human"],
                                  "supported_modalities": ["scRNA"],
                                  "supported_tasks": ["predict_delta_expression"],
                                  "supported_perturbations": ["gene"],
                                  "reject_if": ["gene_not_in_graph_vocabulary"]}},
                              "object_vocabulary": {"genes": ["AHR"]}}}


class _RealPredictor(PredictorAgent):
    """Test fixture: _RealPredictor."""
    name = "RealPredictor"

    def run_prediction(self, model_input: dict) -> dict:
        return {"prediction": {"delta": [0.1]}, "uncertainty": {"sigma": 0.3}}


def test_real_predictor_not_flagged_mock():
    """Verify real predictor not flagged mock."""
    bus = _bus_with_brain()
    _RealPredictor().handle(
        AgentMessage("m1", "X", "RealPredictor", "predict", _payload("RealPredictor"), "t1"), bus)
    out = bus.latest("predictor_result").payload
    assert out["status"] == "success"
    assert out["evidence"] == []
    assert "mock" not in out["provenance"]


def test_mock_predictor_self_declares_mock():
    """Verify mock predictor self declares mock."""
    bus = _bus_with_brain()
    MockGEARSAgent().handle(
        AgentMessage("m1", "X", "MockGEARS", "predict", _payload("MockGEARS"), "t1"), bus)
    out = bus.latest("predictor_result").payload
    assert out["status"] == "success"
    assert "mock" in out["evidence"]
    assert out["provenance"]["mock"] is True
