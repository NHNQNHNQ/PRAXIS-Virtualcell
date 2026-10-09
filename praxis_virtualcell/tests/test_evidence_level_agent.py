"""Tests for evidence level agent."""
from praxis_virtualcell.agents.evidence_level_agent import EvidenceLevelAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _report(**kw):
    base = {"abstain": False, "reliability": "high", "prediction": {"delta": [0.3]},
            "models_used": ["MockLinear"], "abstain_reasons": [], "downgrade_reasons": [],
            "model_disagreement": {"score": 0.2, "triggered": False}, "caution_flags": {},
            "learned_reliability": None, "request": {"species": "human"},
            "seen_in_train": True, "provenance": {}}
    base.update(kw)
    return base


def _run(report):
    bus = MessageBus()
    EvidenceLevelAgent().handle(AgentMessage(
        message_id="c1", sender="Report", receiver="EvidenceLevelAgent",
        message_type="evidence_level_request", payload={"report": report},
        timestamp="t1"), bus)
    return bus.latest("evidence_level_ready")


def test_emits_evidence_level_ready():
    msg = _run(_report())
    assert msg is not None
    assert msg.message_type == "evidence_level_ready"
    assert msg.receiver == "ActiveLearningAgent"
    assert msg.payload["evidence_level"]["level"] == "E2"


def test_agent_does_not_mutate_report():
    r = _report()
    snap = dict(r)
    _run(r)
    assert r == snap


def test_downgrade_report_maps_e4_or_e5():
    msg = _run(_report(reliability="medium",
                       downgrade_reasons=["downgrade:model_disagreement_too_high"]))
    assert msg.payload["evidence_level"]["level"] in ("E4", "E5")


def test_abstain_report_maps_e0_or_e1():
    msg = _run(_report(abstain=True, prediction=None, models_used=[],
                       abstain_reasons=["species_not_supported"]))
    assert msg.payload["evidence_level"]["level"] == "E0"


def test_no_llm_import_in_module():
    import praxis_virtualcell.agents.evidence_level_agent as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_client" not in src
    assert "llm_orchestration" not in src
