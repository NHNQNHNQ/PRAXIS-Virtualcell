"""Use brain_context to classify applicable and rejected predictors, record ortholog caution and negative-transfer
reasons, and attach auditable routing provenance. Applicable cross-species targets are projected through
ortholog.map_upper; unmapped targets receive unmapped_ortholog. This agent has routing authority; LLMRouter
provides suggestions only.
"""
from __future__ import annotations

from praxis_virtualcell.agents.request_adapter import request_to_module_input
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import SchemaError, normalize_request
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.predictors.case_dispatch import REAL_ENGINES, gears_available

_LEGACY_CANDIDATES = ("MockLinear", "MockCPA", "MockGEARS")
_DEFAULT_ORIGIN = "human"
_GENE_PERTS = ("gene", "gene_combination")


class ModelApplicabilityAgent(BaseAgent):
    name = "ModelApplicability"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        req = message.payload["request"]
        bc = message.payload["brain_context"]



        try:
            _norm = normalize_request(request_to_module_input(req))
            engine = route(_norm).engine
        except SchemaError:
            _norm, engine = None, None



        if engine in REAL_ENGINES or (
                engine == "donor_predictor" and (_norm or {}).get("species") == "human" and gears_available()):
            bc2 = {**bc, "routing": {"cautions": {}, "rejection_reasons": {},
                                     "rules_hit": [], "real_engine": engine}}
            bus.send(AgentMessage(message.message_id + ":app", self.name,
                "EnsembleCoordinator", "applicability_decided",
                {"request": req, "brain_context": bc2,
                 "applicable": ["CaseRunner"], "rejected_candidates": []},
                message.timestamp, message.message_id))
            return
        appmap = bc.get("model_applicability") or {}
        vocab = set((bc.get("object_vocabulary") or {}).get("genes", []))
        species = req.get("species")
        ptype = req.get("perturbation_type")
        targets = req.get("perturbation_targets", [])
        neg_transfer = ((bc.get("generic") or {}).get("negative_transfer") or {}).get("negative_transfer", [])
        ortholog_map = (((bc.get("species_rules") or {}).get("ortholog_rules") or {})
                        .get("ortholog", {}).get("map_upper", {}))

        applicable, rejected = [], []
        cautions: dict[str, list] = {}            # §7.3 {predictor: [caution flags]}
        rejection_reasons: dict[str, dict] = {}   # §7.5 {predictor: {reason}}
        rules_hit: list[str] = []

        for name in _LEGACY_CANDIDATES:
            rules = appmap.get(name) or {}
            origin = rules.get("native_host", _DEFAULT_ORIGIN)
            nt_rule = next((nt.get("rule") for nt in neg_transfer
                            if nt.get("from_species") == origin and species in (nt.get("to_species") or [])), None)
            species_ok = bool(rules) and species in rules.get("supported_species", [])
            ok = species_ok \
                and req.get("input_modality") in rules.get("supported_modalities", []) \
                and req.get("task_type") in rules.get("supported_tasks", [])
            reason = None
            sp_list = rules.get("supported_perturbations")
            if ok and sp_list is not None and ptype not in sp_list:
                ok, reason = False, "unsupported_perturbation"
            if ok and "gene_not_in_graph_vocabulary" in rules.get("reject_if", []) and ptype in _GENE_PERTS:
                if any(g not in vocab for g in targets):
                    ok, reason = False, "gene_not_in_graph_vocabulary"
                    rules_hit.append("gene_not_in_graph_vocabulary")
            if ok:
                caution = (rules.get("caution") or {}).get(species) or []
                caution = list(caution) if isinstance(caution, list) else [caution]
                if caution:

                    if ortholog_map and ptype in _GENE_PERTS:
                        unmapped = [g for g in targets if g not in ortholog_map]
                        if unmapped:
                            caution = caution + [f"unmapped_ortholog:{unmapped}"]
                    cautions[name] = caution
                    rules_hit.append((rules.get("cross_species") or {}).get("rule", "ortholog_caution"))
                applicable.append(name)
            else:
                if reason is None:
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


class LegacyModelApplicabilityAdapter(ModelApplicabilityAgent):
    """Explicit no-Pack adapter preserving the frozen P0 candidate/dispatch behavior."""
