"""EvidenceLevelAgent(插点 C,进 message bus):薄包装 governance.evidence_level.map_evidence_level。

收 evidence_level_request({report})→ map_evidence_level(report) → emit evidence_level_ready
(交 ActiveLearningAgent)。铁律:只读 report、只出 evidence_level dict(挂 provenance),
不改 report 任何键、不回写 verdict(决策 B:治理层之上的薄映射)。零 LLM。
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
