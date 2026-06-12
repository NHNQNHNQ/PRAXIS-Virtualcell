"""Task 5(W4b):真 MLBackedPredictorAgent 接 core PredictorAgent —— bus 通讯 + 门 + success/rejected。仅远端。"""
import os

import pytest

pytestmark = pytest.mark.remote


@pytest.fixture(scope="module")
def agent_and_target():
    from praxis_virtualcell.predictors.ml.agent_adapter import make_ml_agent
    from praxis_virtualcell.predictors.ml.donor_bridge import build_predictor_from_ckpt, load_norman

    model, _ = build_predictor_from_ckpt(os.path.join(os.environ["W4B_CKPT_DIR"], "latent_additive"))
    ds = load_norman(split="test", max_perts=3, max_cells=4)
    agent = make_ml_agent(model, norman_ds=ds, name="MLLatent")
    item = next(ds[i] for i in range(len(ds)) if ds[i].kind != "control")
    return agent, item.perturbation.split("+")[0]


def _bus_with_brain():
    from praxis_virtualcell.core.bus import MessageBus
    from praxis_virtualcell.core.message import AgentMessage

    bus = MessageBus()
    bus.send(AgentMessage("b1", "SpeciesBrain", "X", "brain_retrieved", {}, "t0"))
    return bus


def _payload(target, species="human"):
    return {"request": {"species": species, "input_modality": "scRNA",
                        "task_type": "predict_delta_expression", "perturbation_type": "gene",
                        "perturbation_targets": [target]},
            "brain_context": {"species": species, "species_supported": species == "human",
                              "model_applicability": {"MLLatent": {"supported_species": ["human"],
                                  "supported_modalities": ["scRNA"],
                                  "supported_tasks": ["predict_delta_expression"]}},
                              "rules_referenced": []}}


def test_ml_agent_success(agent_and_target):
    from praxis_virtualcell.core.message import AgentMessage

    agent, target = agent_and_target
    bus = _bus_with_brain()
    agent.handle(AgentMessage("m1", "ModelApplicability", "MLLatent", "predict", _payload(target), "t1"), bus)
    out = bus.latest("predictor_result").payload
    assert out["status"] == "success", out
    assert out["prediction"] is not None and out["agent_name"] == "MLLatent"


def test_ml_agent_retrieve_before_predict(agent_and_target):
    from praxis_virtualcell.core.bus import MessageBus
    from praxis_virtualcell.core.exceptions import RetrieveBeforePredictError
    from praxis_virtualcell.core.message import AgentMessage

    agent, target = agent_and_target
    bus = MessageBus()  # 无 brain_retrieved → 门拦截
    with pytest.raises(RetrieveBeforePredictError):
        agent.handle(AgentMessage("m1", "X", "MLLatent", "predict", _payload(target), "t1"), bus)


def test_ml_agent_rejected_unsupported_species(agent_and_target):
    from praxis_virtualcell.core.message import AgentMessage

    agent, target = agent_and_target
    bus = _bus_with_brain()
    agent.handle(AgentMessage("m1", "X", "MLLatent", "predict", _payload(target, species="bacteria"), "t1"), bus)
    out = bus.latest("predictor_result").payload
    assert out["status"] == "rejected", out
    assert out["rejection_reason"] == "unsupported_species"
