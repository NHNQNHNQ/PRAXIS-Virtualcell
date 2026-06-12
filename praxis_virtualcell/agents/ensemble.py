"""只汇总 success 结果(rejected/failed 不进 ensemble)。Coordinator 仅通讯+汇总。"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class EnsembleCoordinatorAgent(BaseAgent):
    name = "EnsembleCoordinator"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        results = message.payload["results"]
        ok = [r for r in results if r["status"] == "success"]
        used = [r["agent_name"] for r in ok]
        rejected = [r["agent_name"] for r in results if r["status"] != "success"]
        ensemble = None
        if ok:
            vecs = [r["prediction"]["delta"] for r in ok if r.get("prediction")]
            n = max((len(v) for v in vecs), default=0)
            ensemble = {"delta": [sum(v[i] for v in vecs) / len(vecs) for i in range(n)]} if n else None
        bus.send(AgentMessage(message.message_id + ":ens", self.name, "Reliability",
            "ensemble_done", {**message.payload, "models_used": used,
            "models_rejected": rejected, "ensemble": ensemble}, message.timestamp,
            message.message_id))
