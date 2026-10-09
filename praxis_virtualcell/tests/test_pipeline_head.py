from praxis_virtualcell.agents.input_interpreter import InputInterpreterAgent
from praxis_virtualcell.agents.model_applicability import ModelApplicabilityAgent
from praxis_virtualcell.agents.object_normalizer import BioObjectNormalizerAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_REQ = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
        "perturbation_targets": ["ahr"], "input_modality": "scRNA",
        "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def test_input_interpreter_parses():
    bus = MessageBus()
    InputInterpreterAgent().handle(AgentMessage("m", "client", "InputInterpreter",
        "parse_request", {"request_dict": _REQ}, "t1"), bus)
    assert bus.latest("request_parsed").payload["request"]["species"] == "human"


def test_normalizer_uppercases_genes():
    bus = MessageBus()
    BioObjectNormalizerAgent().handle(AgentMessage("m", "X", "BioObjectNormalizer",
        "normalize", {"request": _REQ}, "t1"), bus)
    req = bus.latest("object_normalized").payload["request"]
    assert req["perturbation_targets"] == ["AHR"]


def test_model_applicability_splits_applicable_rejected():
    bus = MessageBus()
    bc = {"species": "human", "species_supported": True,
          "model_applicability": {
              "MockCPA": {"supported_species": ["human"], "supported_modalities": ["scRNA"],
                          "supported_tasks": ["predict_delta_expression"], "supported_perturbations": ["gene"]},
              "MockGEARS": {"supported_species": ["human"], "supported_modalities": ["scRNA"],
                            "supported_tasks": ["predict_delta_expression"], "supported_perturbations": ["gene"],
                            "reject_if": ["gene_not_in_graph_vocabulary"]}},
          "object_vocabulary": {"genes": ["AHR"]}}
    ModelApplicabilityAgent().handle(AgentMessage("m", "SpeciesBrain", "ModelApplicability",
        "decide", {"request": dict(_REQ, perturbation_targets=["AHR"]), "brain_context": bc}, "t1"), bus)
    out = bus.latest("applicability_decided").payload
    assert "MockCPA" in out["applicable"] and "MockGEARS" in out["applicable"]
