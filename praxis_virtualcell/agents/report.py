"""结构化报告:不得编造结构里没有的结论;保留 prediction/abstain/参与/拒绝/reliability/provenance。"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class ReportAgent(BaseAgent):
    name = "Report"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        p = message.payload
        rd = p.get("reliability_decision", {})
        report = {
            "request_id": p.get("request", {}).get("request_id"),
            "abstain": rd.get("abstain", False),
            "reliability": rd.get("reliability"),
            "prediction": None if rd.get("abstain") else p.get("ensemble"),
            "models_used": p.get("models_used", []),
            "models_rejected": p.get("models_rejected", []),
            "abstain_reasons": rd.get("reasons", []),
            "critic_violations": p.get("critic_violations", []),
            "caution_flags": p.get("provenance", {}).get("ortholog_cautions", {}),  # §7.3 cross-species caution 可见
            "provenance": p.get("provenance", {}),
        }
        bus.send(AgentMessage(message.message_id + ":rep", self.name, "client",
            "report_done", {"report": report}, message.timestamp, message.message_id))
