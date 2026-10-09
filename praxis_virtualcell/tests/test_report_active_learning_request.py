"""P0 regression tests for request context crossing the report/AL seam."""

from praxis_virtualcell.active_learning.active_learning_agent import ActiveLearningAgent
from praxis_virtualcell.agents.report import ReportAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _report_message() -> AgentMessage:
    return AgentMessage(
        message_id="m1",
        sender="ProvenanceAgent",
        receiver="Report",
        message_type="render",
        payload={
            "request": {
                "request_id": "r1",
                "species": "human",
                "perturbation_targets": ["AHR"],
            },
            "reliability_decision": {
                "abstain": False,
                "reliability": "high",
                "reasons": [],
            },
            "ensemble": {"delta": [0.3]},
            "provenance": {},
        },
        timestamp="t1",
    )


def test_report_preserves_request_context_for_downstream_agents():
    bus = MessageBus()
    ReportAgent().handle(_report_message(), bus)

    report = bus.latest("report_done").payload["report"]

    assert report["request"] == {
        "request_id": "r1",
        "species": "human",
        "perturbation_targets": ["AHR"],
    }


def test_active_learning_candidate_uses_report_request_context():
    bus = MessageBus()
    ReportAgent().handle(_report_message(), bus)
    report = bus.latest("report_done").payload["report"]
    report["provenance"]["module_plan"] = {
        "entries": [{"module": "genetic_hub", "species_support": "strong"}]
    }

    ActiveLearningAgent().handle(
        AgentMessage(
            message_id="m2",
            sender="EvidenceLevelAgent",
            receiver="ActiveLearningAgent",
            message_type="learning_queue_request",
            payload={"report": report, "evidence_level": {"level": "E3"}},
            timestamp="t1",
        ),
        bus,
    )

    candidates = [
        item["candidate"]
        for item in bus.latest("learning_queue_ready").payload["learning_queue"]["items"]
    ]
    assert candidates == ["genetic_hub@human:AHR"]
