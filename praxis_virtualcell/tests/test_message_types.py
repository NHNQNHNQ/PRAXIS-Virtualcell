from dataclasses import asdict

from praxis_virtualcell.core.message import (
    AgentMessage, PredictorResultMessage, ReliabilityDecision,
)


def test_agent_message_roundtrip():
    m = AgentMessage(message_id="m1", sender="A", receiver="B",
                     message_type="ping", payload={"x": 1}, timestamp="t0001")
    d = asdict(m)
    assert d["sender"] == "A" and d["parent_message_id"] is None


def test_predictor_result_status_fields():
    r = PredictorResultMessage(agent_name="MockCPA", status="rejected",
                               prediction=None, uncertainty=None,
                               applicability_score=0.0, evidence=["unsupported"],
                               rejection_reason="species", provenance={})
    assert r.status == "rejected" and r.prediction is None


def test_reliability_decision_defaults():
    d = ReliabilityDecision(reliability="low", abstain=True,
                            reasons=["all_rejected"], failed_checks=[],
                            model_disagreement=None)
    assert d.abstain is True
