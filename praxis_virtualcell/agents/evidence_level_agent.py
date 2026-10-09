"""Read report in evidence_level_request, map existing governance signals, and emit evidence_level_ready for
ActiveLearningAgent. This thin deterministic mapping does not mutate report or its verdict and uses no LLM.
"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.governance.evidence_level import map_evidence_level


class EvidenceLevelAgent(BaseAgent):
    name = "EvidenceLevelAgent"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        report = message.payload.get("report", {}) or {}
        ev = map_evidence_level(report)
        bus.send(AgentMessage(
            message_id=message.message_id + ":evlvl",
            sender=self.name, receiver="ActiveLearningAgent",
            message_type="evidence_level_ready",
            payload={"evidence_level": ev},
            timestamp=message.timestamp, parent_message_id=message.message_id))
