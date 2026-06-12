from praxis_virtualcell.agents.ensemble import EnsembleCoordinatorAgent
from praxis_virtualcell.agents.reliability import ReliabilityAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _result(name, status):
    return {"agent_name": name, "status": status, "prediction": ({"delta": [0.5]} if status == "success" else None),
            "uncertainty": {"sigma": 0.2}, "applicability_score": 1.0 if status == "success" else 0.0,
            "evidence": [], "rejection_reason": None if status == "success" else "x", "provenance": {}}


def test_ensemble_only_aggregates_success():
    bus = MessageBus()
    payload = {"request": {}, "brain_context": {"generic": {"default_abstain_rules": {}}},
               "results": [_result("MockCPA", "success"), _result("MockGEARS", "rejected")]}
    EnsembleCoordinatorAgent().handle(AgentMessage("m", "X", "EnsembleCoordinator", "ensemble", payload, "t1"), bus)
    out = bus.latest("ensemble_done").payload
    assert out["models_used"] == ["MockCPA"]
    assert out["models_rejected"] == ["MockGEARS"]


def test_reliability_abstains_when_all_rejected():
    bus = MessageBus()
    payload = {"request": {}, "brain_context": {"generic": {"default_abstain_rules": {"abstain_if": ["all_predictors_rejected"]}}},
               "results": [_result("MockCPA", "rejected"), _result("MockGEARS", "rejected")],
               "models_used": [], "models_rejected": ["MockCPA", "MockGEARS"], "ensemble": None}
    ReliabilityAgent().handle(AgentMessage("m", "X", "Reliability", "assess", payload, "t1"), bus)
    rd = bus.latest("reliability_decided").payload["reliability_decision"]
    assert rd["abstain"] is True and "all_predictors_rejected" in rd["reasons"]
