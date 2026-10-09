"""Phase 2:ModelWrapper 契约。测 declare_scope 结构、estimate_uncertainty 契约(含 None 优雅降级)、
超出 scope 的输入 → rejected(不硬预测)。用一个最小 DummyWrapper 具化 abstract。"""
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper


class _DummyWrapper(ModelWrapper):
    """最小具化:scope=human/genetic_hub/expression;run_prediction 回定值。"""
    name = "DummyWrapper"

    def declare_scope(self) -> dict:
        return {
            "species": ["human"],
            "module": "genetic_hub",
            "task": ["expression"],
            "perturbation": ["gene"],
        }

    def run_prediction(self, model_input: dict) -> dict:
        return {"prediction": {"delta": 0.5}, "uncertainty": {"std": 0.1}}


class _NoUncertaintyWrapper(_DummyWrapper):
    name = "NoUncWrapper"

    def run_prediction(self, model_input: dict) -> dict:
        return {"prediction": {"delta": 0.2}}  # 无 uncertainty


def _bus_with_brain():
    bus = MessageBus()
    bus.record_trace(AgentMessage(
        message_id="m0", sender="SpeciesBrain", receiver="X",
        message_type="brain_retrieved", payload={}, timestamp="t0"))
    return bus


def _brain_ctx():
    # 让 assess_applicability 放行 human/gene/expression
    return {
        "species": "human",
        "model_applicability": {
            "DummyWrapper": {
                "supported_species": ["human"],
                "supported_modalities": ["scRNA"],
                "supported_tasks": ["expression"],
            }
        },
        "rules_referenced": ["r1"],
    }


def _request(**over):
    base = {
        "species": "human", "input_modality": "scRNA", "task_type": "expression",
        "perturbation_type": "gene", "perturbation_targets": ["AHR"],
    }
    base.update(over)
    return base


def test_declare_scope_structure():
    scope = _DummyWrapper().declare_scope()
    assert set(scope) >= {"species", "module", "task"}
    assert scope["module"] == "genetic_hub"
    assert "human" in scope["species"]


def test_estimate_uncertainty_from_prediction():
    w = _DummyWrapper()
    out = w.run_prediction({})
    unc = w.estimate_uncertainty({}, out["prediction"])
    assert unc["available"] is True
    assert unc["uncertainty"] == {"std": 0.1} or "std" in unc.get("uncertainty", {})


def test_estimate_uncertainty_handles_missing_gracefully():
    """铁律:run_prediction 无 uncertainty → 不崩溃,available=False(诚实:说没有,不假造)。"""
    w = _NoUncertaintyWrapper()
    out = w.run_prediction({})
    unc = w.estimate_uncertainty({}, out.get("prediction"))
    assert unc["available"] is False


def test_in_scope_request_succeeds():
    w = _DummyWrapper()
    bus = _bus_with_brain()
    w.handle(AgentMessage(
        message_id="m1", sender="X", receiver="DummyWrapper", message_type="predict",
        payload={"request": _request(), "brain_context": _brain_ctx()}, timestamp="t1"), bus)
    res = bus.latest("predictor_result")
    assert res.payload["status"] == "success"


def test_out_of_scope_request_is_rejected_not_hard_predicted():
    """超出 scope(mouse)→ rejected,不硬预测(fail-closed)。"""
    w = _DummyWrapper()
    bus = _bus_with_brain()
    ctx = _brain_ctx()  # applicability 仍只列 human
    w.handle(AgentMessage(
        message_id="m2", sender="X", receiver="DummyWrapper", message_type="predict",
        payload={"request": _request(species="mouse"), "brain_context": ctx}, timestamp="t2"), bus)
    res = bus.latest("predictor_result")
    assert res.payload["status"] == "rejected"
    assert res.payload["prediction"] is None
