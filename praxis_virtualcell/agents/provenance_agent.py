"""Assemble an auditable chain of trace summaries, rule references, used/rejected models, and critic observations."""
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
        adapter_outputs = {
            r.get("agent_name"): (r.get("provenance") or {}).get("adapter_output")
            for r in p.get("results", [])
            if (r.get("provenance") or {}).get("adapter_output") is not None
        }
        provenance = {
            "n_messages": len(bus.trace),
            "rules_referenced": bc.get("rules_referenced", []),
            "rules_hit": routing.get("rules_hit", []),
            "ortholog_cautions": routing.get("cautions", {}),          # §7.3 {predictor: [caution flags]}
            "rejection_reasons": routing.get("rejection_reasons", {}),  # §7.5 {predictor: {reason}}
            "models_used": p.get("models_used", []),
            "models_rejected": p.get("models_rejected", []),
            "models_failed": p.get("models_failed", []),
            "critic_violations": p.get("critic_violations", []),

            "model_cautions": p.get("model_cautions", {}),


            "per_call_hashes": {r.get("agent_name"): (r.get("provenance") or {}).get("per_call")
                                for r in p.get("results", [])
                                if (r.get("provenance") or {}).get("per_call")},
        }
        if adapter_outputs:
            provenance["adapter_outputs"] = adapter_outputs
        if p.get("adapter_output") is not None:
            provenance["adapter_output"] = p["adapter_output"]
        bus.send(AgentMessage(message.message_id + ":prov", self.name, "Report",
            "provenance_done", {**p, "provenance": provenance}, message.timestamp,
            message.message_id))
