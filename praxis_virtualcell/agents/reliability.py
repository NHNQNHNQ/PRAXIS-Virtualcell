"""据 abstain rules + 模型分歧裁 reliability/abstain。"""
from __future__ import annotations

from dataclasses import asdict

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage, ReliabilityDecision


class ReliabilityAgent(BaseAgent):
    name = "Reliability"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        p = message.payload
        used = p.get("models_used", [])
        reasons: list[str] = []
        failed: list[str] = []
        abstain_rules = (p.get("brain_context", {}).get("generic", {})
                         .get("default_abstain_rules", {}).get("abstain_if", []))
        abstain = False
        if not used:
            abstain = True
            if "all_predictors_rejected" in abstain_rules:
                reasons.append("all_predictors_rejected")
            else:
                reasons.append("no_successful_predictor")
        disagreement = None
        if len(used) >= 2 and p.get("ensemble"):
            reliability = "high"
        elif used:
            reliability = "medium"
        else:
            reliability = "low"
        rd = ReliabilityDecision(reliability=reliability, abstain=abstain,
                                 reasons=reasons, failed_checks=failed,
                                 model_disagreement=disagreement)
        bus.send(AgentMessage(message.message_id + ":rel", self.name, "Critic",
            "reliability_decided", {**p, "reliability_decision": asdict(rd)},
            message.timestamp, message.message_id))
