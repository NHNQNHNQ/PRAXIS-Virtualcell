from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.predictors.mock_gears import MockGEARSAgent


def _bus_with_brain():
    bus = MessageBus()
    bus.send(AgentMessage("b1", "SpeciesBrain", "X", "brain_retrieved", {}, "t0"))
    return bus


def _payload(gene):
    return {"request": {"species": "human", "input_modality": "scRNA",
                        "task_type": "predict_delta_expression", "perturbation_type": "gene",
                        "perturbation_targets": [gene]},
            "brain_context": {"species": "human", "species_supported": True,
                              "model_applicability": {"MockGEARS": {"supported_species": ["human"],
                                  "supported_modalities": ["scRNA"], "supported_tasks": ["predict_delta_expression"],
                                  "supported_perturbations": ["gene"], "reject_if": ["gene_not_in_graph_vocabulary"]}},
                              "object_vocabulary": {"genes": ["AHR", "TP53"]}}}


def test_gears_rejects_unknown_gene():
    bus = _bus_with_brain()
    MockGEARSAgent().handle(AgentMessage("m1", "X", "MockGEARS", "predict", _payload("ZZZ9"), "t1"), bus)
    out = bus.latest("predictor_result").payload
    assert out["status"] == "rejected"
    assert "gene_not_in_graph_vocabulary" in out["rejection_reason"]


def test_gears_accepts_known_gene():
    bus = _bus_with_brain()
    MockGEARSAgent().handle(AgentMessage("m1", "X", "MockGEARS", "predict", _payload("AHR"), "t1"), bus)
    assert bus.latest("predictor_result").payload["status"] == "success"
