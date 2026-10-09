"""Tests for model broker agent."""
from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _ask(model_name):
    return AgentMessage(
        message_id="q1", sender="Client", receiver="ModelBrokerAgent",
        message_type="model_request", payload={"model_name": model_name}, timestamp="t1")


def test_available_model_returns_wrapper():
    """Verify available model returns wrapper."""
    bus = MessageBus()
    ModelBrokerAgent().handle(_ask("ecoli_gem"), bus)
    res = bus.latest("model_broker_result")
    assert res is not None
    p = res.payload
    assert p["model_name"] == "ecoli_gem"
    assert p["available"] is True
    assert p["wrapper"] == "praxis_virtualcell.model_zoo.wrappers.gem_wrapper.GemWrapper"


def test_planned_model_is_fail_closed():
    """Verify planned model is fail closed."""
    bus = MessageBus()
    ModelBrokerAgent().handle(_ask("gears"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert p["status"] == "planned"
    assert p["reason"]


def test_unknown_model_is_fail_closed():
    bus = MessageBus()
    ModelBrokerAgent().handle(_ask("no_such_model"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert "unknown" in p["reason"]


def test_bus_message_structure():
    bus = MessageBus()
    ModelBrokerAgent().handle(_ask("ecoli_gem"), bus)
    res = bus.latest("model_broker_result")
    assert res.sender == "ModelBrokerAgent"
    assert res.message_type == "model_broker_result"
    assert set(res.payload) >= {"model_name", "available", "status", "wrapper", "reason"}


def test_missing_dependency_degrades_explicitly(monkeypatch):
    """Verify missing dependency degrades explicitly."""
    import praxis_virtualcell.agents.model_broker_agent as mba

    monkeypatch.setattr(mba, "_dep_available", lambda dep: dep != "cobra")
    bus = MessageBus()
    mba.ModelBrokerAgent().handle(_ask("ecoli_gem"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert "cobra" in p["reason"]
