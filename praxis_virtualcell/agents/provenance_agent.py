"""组装可追溯证据链:trace 摘要 + 规则引用 + 模型参与/拒绝 + critic。"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class ProvenanceAgent(BaseAgent):
    name = "ProvenanceAgent"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        p = message.payload
        provenance = {
            "n_messages": len(bus.trace),
            "rules_referenced": p.get("brain_context", {}).get("rules_referenced", [])
                                or p.get("brain_context", {}).get("generic", {}).get("negative_transfer", []),
            "models_used": p.get("models_used", []),
            "models_rejected": p.get("models_rejected", []),
            "critic_violations": p.get("critic_violations", []),
        }
        bus.send(AgentMessage(message.message_id + ":prov", self.name, "Report",
            "provenance_done", {**p, "provenance": provenance}, message.timestamp,
            message.message_id))
