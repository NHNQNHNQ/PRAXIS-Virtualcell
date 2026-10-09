"""Tests for active learning agent."""
from praxis_virtualcell.active_learning.active_learning_agent import ActiveLearningAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _module_plan(entries=None):
    entries = entries or [
        {"module": "genetic_hub", "role": "primary", "species_support": "strong",
         "verdict": "accept", "data_gated": False},
        {"module": "stress_processor", "role": "secondary", "species_support": "weak",
         "verdict": "caution", "data_gated": True},
    ]
    return {"species": "human", "primary": "genetic_hub",
            "secondary": ["stress_processor"], "overall_verdict": "caution", "entries": entries}


def _report(**kw):
    base = {"abstain": False, "reliability": "high", "prediction": {"delta": [0.3]},
            "models_used": ["MockLinear"], "abstain_reasons": [], "downgrade_reasons": [],
            "model_disagreement": {"score": 0.3, "triggered": False}, "caution_flags": {},
            "learned_reliability": None, "request": {"species": "human",
                                                     "perturbation_targets": ["AHR"]},
            "seen_in_train": True,
            "provenance": {"module_plan": _module_plan()}}
    base.update(kw)
    return base


def _run(report, evidence_level=None):
    bus = MessageBus()
    ActiveLearningAgent().handle(AgentMessage(
        message_id="c1", sender="EvidenceLevelAgent", receiver="ActiveLearningAgent",
        message_type="learning_queue_request",
        payload={"report": report, "evidence_level": evidence_level or {"level": "E3"}},
        timestamp="t1"), bus)
    return bus.latest("learning_queue_ready")


def test_emits_learning_queue_ready():
    msg = _run(_report())
    assert msg is not None
    assert msg.message_type == "learning_queue_ready"
    assert msg.receiver == "client"
    q = msg.payload["learning_queue"]
    assert "items" in q and "notes" in q


def test_weak_gated_module_ranks_higher():
    """Verify weak gated module ranks higher."""
    msg = _run(_report())
    items = msg.payload["learning_queue"]["items"]
    mods = [it["module"] for it in items]
    assert "stress_processor" in mods and "genetic_hub" in mods
    assert mods.index("stress_processor") < mods.index("genetic_hub")


def test_does_not_mutate_report():
    """Verify does not mutate report."""
    r = _report()
    snap = {"abstain": r["abstain"], "reliability": r["reliability"],
            "prediction": dict(r["prediction"]), "provenance_keys": set(r["provenance"])}
    _run(r)
    assert r["abstain"] == snap["abstain"]
    assert r["reliability"] == snap["reliability"]
    assert r["prediction"] == snap["prediction"]
    assert set(r["provenance"]) == snap["provenance_keys"]


def test_abstain_report_no_fabricated_accept():
    """Verify abstain report no fabricated accept."""
    r = _report(abstain=True, prediction=None, models_used=[],
                abstain_reasons=["model_disagreement_too_high"])
    msg = _run(r, evidence_level={"level": "E1"})
    assert r["abstain"] is True
    q = msg.payload["learning_queue"]
    assert isinstance(q["items"], list)


def test_no_module_plan_empty_queue_with_note():
    """Verify no module plan empty queue with note."""
    r = _report(provenance={})
    msg = _run(r)
    q = msg.payload["learning_queue"]
    assert q["items"] == []
    assert q["notes"]


def test_high_disagreement_drives_gain():
    """Verify high disagreement drives gain."""
    msg = _run(_report(model_disagreement={"score": 0.95, "triggered": True},
                       reliability="medium",
                       downgrade_reasons=["downgrade:model_disagreement_too_high"]),
               evidence_level={"level": "E4"})
    items = msg.payload["learning_queue"]["items"]
    assert items
    drivers = [d for it in items for d in it["drivers"]]
    assert any("disagreement" in d for d in drivers)


def test_no_llm_import_in_module():
    import praxis_virtualcell.active_learning.active_learning_agent as m
    src = open(m.__file__, encoding="utf-8").read()
    assert "agents_llm" not in src and "llm_client" not in src
    assert "llm_orchestration" not in src
