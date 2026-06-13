"""据 brain_context 把候选 predictor 分成 applicable / rejected_candidates；
并计算 cross-species ortholog caution(§7.3)/ negative-transfer 命中(§7.5)/ 各 predictor 拒因,
写入 brain_context.routing(随 payload 透传到 Provenance/Report,使路由依据在 trace 可审计)。
最终路由权威在此(LLMRouter 只能建议,W3)。"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_CANDIDATES = ("MockLinear", "MockCPA", "MockGEARS")
# Mock* 三个 predictor 均训练于 human(母种);cross-species 迁移/负迁移据此判定。
_PREDICTOR_ORIGIN = "human"


class ModelApplicabilityAgent(BaseAgent):
    name = "ModelApplicability"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        req = message.payload["request"]
        bc = message.payload["brain_context"]
        appmap = bc.get("model_applicability") or {}
        vocab = set((bc.get("object_vocabulary") or {}).get("genes", []))
        species = req.get("species")
        neg_transfer = ((bc.get("generic") or {}).get("negative_transfer") or {}).get("negative_transfer", [])
        # 母种(human)→ 本物种 是否命中负迁移 → 具体 rule 名(供 §7.5 trace 审计)
        nt_rule = next((nt.get("rule") for nt in neg_transfer
                        if nt.get("from_species") == _PREDICTOR_ORIGIN
                        and species in (nt.get("to_species") or [])), None)

        applicable, rejected = [], []
        cautions: dict[str, list] = {}            # {name: [caution flags]}  §7.3
        rejection_reasons: dict[str, dict] = {}   # {name: {reason}}          §7.5
        rules_hit: list[str] = []                 # 本次命中的具体规则名

        for name in _CANDIDATES:
            rules = appmap.get(name)
            species_ok = bool(rules) and species in rules.get("supported_species", [])
            ok = species_ok \
                and req.get("input_modality") in rules.get("supported_modalities", []) \
                and req.get("task_type") in rules.get("supported_tasks", [])
            reason = None
            if ok and "gene_not_in_graph_vocabulary" in rules.get("reject_if", []):
                if any(g not in vocab for g in req.get("perturbation_targets", [])):
                    ok = False
                    reason = "gene_not_in_graph_vocabulary"
                    rules_hit.append("gene_not_in_graph_vocabulary")
            if ok:
                # cross-species ortholog caution:applicable 但带 caution(LIST)§7.3
                caution = (rules.get("caution") or {}).get(species) or []
                if caution:
                    cautions[name] = list(caution)
                    rules_hit.append((rules.get("cross_species") or {}).get("rule", "ortholog_caution"))
                applicable.append(name)
            else:
                if reason is None:  # 物种级拒绝:负迁移命中则记具体 rule,否则 unsupported_species
                    if nt_rule:
                        reason = nt_rule
                        rules_hit.append(nt_rule)
                    else:
                        reason = "unsupported_species" if not species_ok else "not_applicable"
                rejection_reasons[name] = {"reason": reason}
                rejected.append(name)

        bc2 = {**bc, "routing": {"cautions": cautions,
                                 "rejection_reasons": rejection_reasons,
                                 "rules_hit": sorted(set(rules_hit))}}
        bus.send(AgentMessage(message.message_id + ":app", self.name,
            "EnsembleCoordinator", "applicability_decided",
            {"request": req, "brain_context": bc2, "applicable": applicable,
             "rejected_candidates": rejected}, message.timestamp, message.message_id))
