"""Build a structured report without inventing conclusions. Preserve prediction/abstention, participation,
rejection, reliability, and provenance. abstain_reasons contains actual abstention reasons; nonabstaining
downgrades are recorded separately in downgrade_reasons.
"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class ReportAgent(BaseAgent):
    name = "Report"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        p = message.payload
        rd = p.get("reliability_decision", {})
        reasons = rd.get("reasons", [])
        report = {
            "request": p.get("request", {}),
            "request_id": p.get("request", {}).get("request_id"),
            "abstain": rd.get("abstain", False),
            "reliability": rd.get("reliability"),
            "prediction": None if rd.get("abstain") else p.get("ensemble"),
            "models_used": p.get("models_used", []),
            "models_rejected": p.get("models_rejected", []),
            "models_failed": p.get("models_failed", []),
            "abstain_reasons": [r for r in reasons if not r.startswith("downgrade:")],
            "downgrade_reasons": [r for r in reasons if r.startswith("downgrade:")],
            "failed_checks": rd.get("failed_checks", []),
            "model_disagreement": rd.get("model_disagreement"),
            "critic_violations": p.get("critic_violations", []),
            "caution_flags": p.get("provenance", {}).get("ortholog_cautions", {}),
            "learned_reliability": p.get("learned_reliability"),
            "provenance": p.get("provenance", {}),
        }
        if p.get("adapter_output") is not None:
            report["adapter_output"] = None if rd.get("abstain") else p["adapter_output"]
        bus.send(AgentMessage(message.message_id + ":rep", self.name, "client",
            "report_done", {"report": report}, message.timestamp, message.message_id))
