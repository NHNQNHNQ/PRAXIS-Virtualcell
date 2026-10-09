import pytest

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.exceptions import RetrieveBeforePredictError
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.predictors.mock_cpa import MockCPAAgent

_PAYLOAD = {"request": {"species": "human", "input_modality": "scRNA",
                        "task_type": "predict_delta_expression", "perturbation_type": "gene",
                        "perturbation_targets": ["AHR"]},
            "brain_context": {"species": "human", "species_supported": True,
                              "model_applicability": {"MockCPA": {"supported_species": ["human"],
                                  "supported_modalities": ["scRNA"], "supported_tasks": ["predict_delta_expression"],
                                  "supported_perturbations": ["gene"]}},
                              "object_vocabulary": {"genes": ["AHR"]}}}


def test_predict_without_brain_retrieved_raises():
    bus = MessageBus()
    a = MockCPAAgent()
    m = AgentMessage("m1", "ModelApplicability", "MockCPA", "predict", _PAYLOAD, "t1")
    with pytest.raises(RetrieveBeforePredictError):
        a.handle(m, bus)


def test_predict_with_brain_retrieved_succeeds():
    bus = MessageBus()
    bus.send(AgentMessage("b1", "SpeciesBrain", "ModelApplicability", "brain_retrieved", {}, "t0"))
    a = MockCPAAgent()
    a.handle(AgentMessage("m1", "ModelApplicability", "MockCPA", "predict", _PAYLOAD, "t1"), bus)
    out = bus.latest("predictor_result")
    assert out.payload["status"] == "success"
    assert out.payload["agent_name"] == "MockCPA"
