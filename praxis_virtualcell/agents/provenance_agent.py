"""组装可追溯证据链:trace 摘要 + 规则引用 + 模型参与/拒绝 + critic。"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class ProvenanceAgent(BaseAgent):
    name = "ProvenanceAgent"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        p = message.payload
        bc = p.get("brain_context", {})
        routing = bc.get("routing", {})
        provenance = {
            "n_messages": len(bus.trace),
            "rules_referenced": bc.get("rules_referenced", []),
            "rules_hit": routing.get("rules_hit", []),                  # §7.5 本次命中的具体规则名
            "ortholog_cautions": routing.get("cautions", {}),          # §7.3 {predictor: [caution flags]}
            "rejection_reasons": routing.get("rejection_reasons", {}),  # §7.5 {predictor: {reason}}
            "models_used": p.get("models_used", []),
            "models_rejected": p.get("models_rejected", []),
            "models_failed": p.get("models_failed", []),
            "critic_violations": p.get("critic_violations", []),
            # B1:机制 predictor 的 disposition caution(如 targets_not_in_gem)如实透出
            "model_cautions": p.get("model_cautions", {}),
            # C2:per-call hash 汇总(每个 result 的 per_call → {agent_name: per_call})。
            # 只汇总,不裁决;供 Gate A 校验 models_used 完整性。
            "per_call_hashes": {r.get("agent_name"): (r.get("provenance") or {}).get("per_call")
                                for r in p.get("results", [])
                                if (r.get("provenance") or {}).get("per_call")},
        }
        bus.send(AgentMessage(message.message_id + ":prov", self.name, "Report",
            "provenance_done", {**p, "provenance": provenance}, message.timestamp,
            message.message_id))
