from praxis_virtualcell.agents.species_brain import SpeciesBrainAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import RuntimeConfig
from praxis_virtualcell.core.message import AgentMessage


def _req():
    return {"species": "human", "perturbation_targets": ["AHR"], "task_type": "predict_delta_expression",
            "input_modality": "scRNA", "perturbation_type": "gene"}


def test_brain_retrieved_for_human():
    bus = MessageBus()
    a = SpeciesBrainAgent(RuntimeConfig())
    a.handle(AgentMessage("m1", "X", "SpeciesBrain", "retrieve",
                          {"request": _req()}, "t1"), bus)
    out = bus.latest("brain_retrieved")
    assert out is not None
    bc = out.payload["brain_context"]
    assert bc["species"] == "human"
    assert "model_applicability" in bc and "object_vocabulary" in bc
    assert "AHR" in bc["object_vocabulary"]["genes"]


def test_unknown_species_still_retrieves_generic_with_flag():
    bus = MessageBus()
    a = SpeciesBrainAgent(RuntimeConfig())
    req = dict(_req(), species="martian")
    a.handle(AgentMessage("m1", "X", "SpeciesBrain", "retrieve",
                          {"request": req}, "t1"), bus)
    bc = bus.latest("brain_retrieved").payload["brain_context"]
    assert bc["species_supported"] is False
