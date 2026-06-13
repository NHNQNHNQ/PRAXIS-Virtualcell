"""结构化报告:不得编造结构里没有的结论;保留 prediction/abstain/参与/拒绝/reliability/provenance。
abstain_reasons 只装真 abstain 原因;非 abstain 的可靠性降级(downgrade: 前缀)单列 downgrade_reasons,
避免 'abstain_reasons 非空 ⇒ 已弃权' 的下游误读(§8.4 报告诚实性)。"""
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
            "provenance": p.get("provenance", {}),
        }
        bus.send(AgentMessage(message.message_id + ":rep", self.name, "client",
            "report_done", {"report": report}, message.timestamp, message.message_id))
