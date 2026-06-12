"""据 brain_context 把候选 predictor 分成 applicable / rejected_candidates。
最终路由权威在此(LLMRouter 只能建议,W3)。"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_CANDIDATES = ("MockLinear", "MockCPA", "MockGEARS")


class ModelApplicabilityAgent(BaseAgent):
    name = "ModelApplicability"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        req = message.payload["request"]
        bc = message.payload["brain_context"]
        appmap = bc.get("model_applicability") or {}
        vocab = set((bc.get("object_vocabulary") or {}).get("genes", []))
        applicable, rejected = [], []
        for name in _CANDIDATES:
            rules = appmap.get(name)
            ok = bool(rules) \
                and req.get("species") in rules.get("supported_species", []) \
                and req.get("input_modality") in rules.get("supported_modalities", []) \
                and req.get("task_type") in rules.get("supported_tasks", [])
            if ok and "gene_not_in_graph_vocabulary" in rules.get("reject_if", []):
                if any(g not in vocab for g in req.get("perturbation_targets", [])):
                    ok = False
            (applicable if ok else rejected).append(name)
        bus.send(AgentMessage(message.message_id + ":app", self.name,
            "EnsembleCoordinator", "applicability_decided",
            {"request": req, "brain_context": bc, "applicable": applicable,
             "rejected_candidates": rejected}, message.timestamp, message.message_id))
