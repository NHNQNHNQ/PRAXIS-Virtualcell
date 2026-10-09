"""Determine reliability and abstention from hard rules, disagreement, core failures, and cell type. Hard
abstention takes precedence; nonabstaining downgrade signals lower reliability separately. Optional learned
scoring replaces only soft disagreement decisions. Missing artifacts or incompatible schemas fall back to rules;
expose decisions and provenance.
"""
from __future__ import annotations

from dataclasses import asdict

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage, ReliabilityDecision

_HARD_ABSTAIN = {"no_perturbation_specified", "core_predictor_failed",
                 "species_not_supported", "all_predictors_rejected", "no_successful_predictor"}

_DOWN = {"high": "medium", "medium": "low", "low": "low"}


class ReliabilityAgent(BaseAgent):
    name = "Reliability"

    def __init__(self, *, mode: str = "rule", art_dir=None) -> None:

        self.mode = mode
        self._art_dir = art_dir

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        p = message.payload
        used = p.get("models_used", [])
        bc = p.get("brain_context", {})
        req = p.get("request", {})
        results = p.get("results", [])
        generic = bc.get("generic", {})
        abstain_rules = generic.get("default_abstain_rules", {}).get("abstain_if", [])
        reasons: list[str] = []
        failed: list[str] = []
        abstain = False

        targets = [t for t in (req.get("perturbation_targets") or []) if str(t).strip()]
        if not targets:
            abstain = True
            reasons.append("no_perturbation_specified")

        core_set = set((generic.get("core_predictors") or {}).get("core", []))
        core_failed = [r.get("agent_name") for r in results
                       if r.get("status") == "failed" and r.get("agent_name") in core_set]
        if core_failed and "core_predictor_failed" in abstain_rules:
            abstain = True
            reasons.append("core_predictor_failed")
            failed.extend(core_failed)

        if not used:
            abstain = True
            if not bc.get("species_supported", True) and "species_not_supported" in abstain_rules:
                reasons.append("species_not_supported")
            reasons.append("all_predictors_rejected" if "all_predictors_rejected" in abstain_rules
                           else "no_successful_predictor")

        dis = p.get("disagreement")
        score = dis.get("score") if dis else None
        threshold = generic.get("default_abstain_rules", {}).get("disagreement_threshold", 0.5)
        disagreement_high = score is not None and score > threshold


        hard_abstain = abstain and any(r in _HARD_ABSTAIN for r in reasons)
        learned_prov = None
        learned_active = False
        learned_decision = None
        adapter_output = p.get("adapter_output") or {}
        learned_adapter_supported = not adapter_output or (
            adapter_output.get("task") == "predict_delta_expression"
            and adapter_output.get("output") == "delta_expression"
        )
        if self.mode != "rule" and learned_adapter_supported:
            learned_prov = self._learned(p, dis)
            if not learned_prov.get("fallback"):
                learned_active = True
                learned_decision = learned_prov["abstain_decision"]
        elif self.mode != "rule":
            learned_prov = {
                "fallback": True,
                "reason": "unsupported_adapter_output",
            }


        if disagreement_high and "model_disagreement_too_high" in abstain_rules and not learned_active:
            abstain = True
            reasons.append("model_disagreement_too_high")
            if "model_disagreement" not in failed:
                failed.append("model_disagreement")

        if learned_active and not hard_abstain and learned_decision == "abstain":
            abstain = True
            reasons.append("learned_abstain_low_reliability")


        if abstain:
            reliability = "low"
        elif len(used) >= 2 and p.get("ensemble"):
            reliability = "high"
        elif used:
            reliability = "medium"
        else:
            reliability = "low"


        if not abstain:
            if learned_active:
                if learned_decision == "downgrade":
                    reliability = _DOWN[reliability]
                    reasons.append("downgrade:learned_low_reliability")
            elif disagreement_high:
                reliability = "medium" if reliability == "high" else "low"
                reasons.append("downgrade:model_disagreement_too_high")
                if "model_disagreement" not in failed:
                    failed.append("model_disagreement")

        req_ct = req.get("cell_type")
        if req_ct and used and not abstain:
            appmap = bc.get("model_applicability") or {}
            declaring = [n for n in used if appmap.get(n, {}).get("supported_cell_types") is not None]
            unsupported = [n for n in declaring if req_ct not in appmap[n]["supported_cell_types"]]
            if declaring and len(unsupported) == len(declaring):
                reasons.append("downgrade:cell_type_not_supported")
                reliability = _DOWN[reliability] if reliability != "low" else "low"

        md = {**dis, "threshold": threshold, "triggered": disagreement_high} if dis else None
        rd = ReliabilityDecision(reliability=reliability, abstain=abstain,
                                 reasons=reasons, failed_checks=failed, model_disagreement=md)
        out = {**p, "reliability_decision": asdict(rd)}
        if learned_prov is not None:
            out["learned_reliability"] = {"reliability_mode": self.mode, **learned_prov}
        bus.send(AgentMessage(message.message_id + ":rel", self.name, "Critic",
            "reliability_decided", out, message.timestamp, message.message_id))

    def _learned(self, p: dict, dis: dict | None) -> dict:
        """Extract inference-available features and call learned_reliability.score; missing inputs or errors fall
        back to rules.
        """
        from praxis_virtualcell.governance import learned_reliability as L
        feats = {
            "disagreement_score": (dis or {}).get("score"),
            "disagreement_n_zero_pairs": (dis or {}).get("n_zero_vector_pairs"),
            "seen_in_train": p.get("seen_in_train"),
        }
        kw = {"art_dir": self._art_dir} if self._art_dir else {}
        try:
            return L.score(feats, **kw)
        except Exception as e:
            return {"fallback": True, "reason": f"exception:{type(e).__name__}"}
