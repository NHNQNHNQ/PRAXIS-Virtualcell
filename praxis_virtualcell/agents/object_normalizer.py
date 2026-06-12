"""第一版:gene symbol 去空格 + 大写(真 ortholog/别名归一化留后续)。"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class BioObjectNormalizerAgent(BaseAgent):
    name = "BioObjectNormalizer"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        req = dict(message.payload["request"])
        if req.get("perturbation_type") in ("gene", "gene_combination"):
            req["perturbation_targets"] = [str(g).strip().upper()
                                           for g in req.get("perturbation_targets", [])]
        bus.send(AgentMessage(message.message_id + ":norm", self.name,
            "SpeciesBrain", "object_normalized", {"request": req}, message.timestamp,
            message.message_id))
