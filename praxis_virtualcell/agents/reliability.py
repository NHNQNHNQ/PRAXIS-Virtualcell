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
        bc = p.get("brain_context", {})
        req = p.get("request", {})
        abstain_rules = (bc.get("generic", {}).get("default_abstain_rules", {}).get("abstain_if", []))
        reasons: list[str] = []
        failed: list[str] = []
        abstain = False
        # 退化输入:无有效扰动目标 → abstain(不该静默出预测)
        targets = [t for t in (req.get("perturbation_targets") or []) if str(t).strip()]
        if not targets:
            abstain = True
            reasons.append("no_perturbation_specified")
        if not used:
            abstain = True
            # 物种未知 vs 物种已知但模型不适配:前者额外标 species_not_supported(若 abstain rule 允许)
            if not bc.get("species_supported", True) and "species_not_supported" in abstain_rules:
                reasons.append("species_not_supported")
            reasons.append("all_predictors_rejected" if "all_predictors_rejected" in abstain_rules
                           else "no_successful_predictor")
        disagreement = None
        if abstain:
            reliability = "low"
        elif len(used) >= 2 and p.get("ensemble"):
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
