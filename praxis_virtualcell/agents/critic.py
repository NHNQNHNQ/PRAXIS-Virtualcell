"""Deterministically audit retrieve-before-predict, ensemble completeness, abstention, provenance, uncertainty,
species consistency, and prediction consistency. Record violations without changing predictions. This agent
audits reliability_decided before Report; LLMCriticAgent separately reviews narrative semantics when credentials
are configured.
"""
from __future__ import annotations

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class CriticAgent(BaseAgent):
    name = "Critic"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        p = message.payload
        bc = p.get("brain_context", {}) or {}
        req = p.get("request", {}) or {}
        rd = p.get("reliability_decision", {}) or {}
        abstain = bool(rd.get("abstain"))
        results = p.get("results", []) or []
        used = set(p.get("models_used", []))
        ensemble = p.get("ensemble")
        appmap = bc.get("model_applicability") or {}
        species = req.get("species")
        notes: list[str] = []
        violations: list[str] = []
        types = [m.message_type for m in bus.trace]
        # 1. retrieve-before-predict
        if "predictor_result" in types:
            if "brain_retrieved" not in types or types.index("brain_retrieved") > types.index("predictor_result"):
                violations.append("predict_before_retrieve")

        rejected = {r["agent_name"] for r in results if r["status"] != "success"}
        if used & rejected:
            violations.append(f"rejected_model_in_ensemble:{sorted(used & rejected)}")

        if not used and not abstain:
            violations.append("claims_prediction_without_predictor")

        if not abstain and not (bc.get("rules_referenced") or []):
            violations.append("missing_provenance")

        no_sigma = sorted(r["agent_name"] for r in results if r.get("status") == "success"
                          and (r.get("provenance") or {}).get("adapter_output") is None
                          and (r.get("uncertainty") is None or "sigma" not in (r.get("uncertainty") or {})))
        if no_sigma:
            violations.append(f"missing_uncertainty:{no_sigma}")

        if species is not None:
            bad = sorted(n for n in used if n in appmap
                         and species not in (appmap[n].get("supported_species") or []))
            if bad:
                violations.append(f"unsupported_species_in_ensemble:{bad}")

        if abstain and ensemble is not None:
            violations.append("abstain_inconsistent_with_prediction")
        notes.append(f"checked retrieve-first, ensemble integrity, abstain honesty, provenance, "
                     f"uncertainty reporting, species consistency, abstain/prediction consistency; violations={violations}")  # noqa: E501
        bus.send(AgentMessage(message.message_id + ":crit", self.name, "ProvenanceAgent",
            "critic_done", {**p, "critic_notes": notes, "critic_violations": violations},
            message.timestamp, message.message_id))
