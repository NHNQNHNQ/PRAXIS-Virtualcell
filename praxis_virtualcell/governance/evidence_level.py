"""Conservative E0–E5 mapping above governance using existing reliability, OOD, disagreement, and learned signals.
Do not mutate verdicts or promote abstain/downgrade into E2/E3 acceptance. Missing seen_in_train yields
caution/species proxies or unknown rather than assuming in-domain support.
"""
from __future__ import annotations

from praxis_virtualcell.agents.reliability import _HARD_ABSTAIN

_HARD_REJECT = _HARD_ABSTAIN

_OOD_CAUTION_KEYS = ("ortholog", "cross_species", "cross-species", "projected")


def derive_ood_signal(report: dict) -> str:
    """Derive in_domain/ood/unknown: seen_in_train=True/False takes priority; absent values use caution/species
    signals and otherwise remain unknown.
    """
    seen = report.get("seen_in_train")
    if seen in (True, 1):
        return "in_domain"
    if seen in (False, 0):
        return "ood"

    return "unknown"


def _has_ood_caution(report: dict) -> bool:
    flags = report.get("caution_flags") or {}
    blob = " ".join(str(v).lower() for v in flags.values())
    if any(k in blob for k in _OOD_CAUTION_KEYS):
        return True
    species = str((report.get("request") or {}).get("species", "")).lower()
    return bool(species) and species != "human"


def map_evidence_level(report: dict) -> dict:
    """Map existing report signals conservatively to a new E0–E5 dictionary without mutating report or verdict."""
    abstain = bool(report.get("abstain"))
    reliability = report.get("reliability")
    downgrade = list(report.get("downgrade_reasons") or [])
    abstain_reasons = list(report.get("abstain_reasons") or [])
    dis = report.get("model_disagreement") or {}
    dis_triggered = bool(dis.get("triggered"))
    learned = report.get("learned_reliability") or {}
    learned_fallback = bool(learned.get("fallback"))
    ood = derive_ood_signal(report)
    rationale: list[str] = []


    if abstain:
        if any(r in _HARD_REJECT for r in abstain_reasons):
            rationale.append("hard_reject_abstain")
            level = "E0"
        else:
            rationale.append("abstain")
            level = "E1"
        return {"level": level, "rationale": rationale, "ood_signal": ood,
                "aligned_with_disposition": True}


    if dis_triggered:
        rationale.append("disagreement_triggered")
    if learned_fallback:
        rationale.append("learned_fallback")
    if downgrade:
        rationale.append("downgrade")

    if dis_triggered or learned_fallback or reliability == "low":

        rationale.append("high_uncertainty")
        level = "E5"
    elif downgrade:
        level = "E4"
    else:

        if ood == "in_domain" and not _has_ood_caution(report) and reliability == "high":
            rationale.append("in_domain_high_reliability")
            level = "E2"
        else:
            rationale.append("accept_with_caution_or_unknown_ood")
            level = "E3"
    return {"level": level, "rationale": rationale, "ood_signal": ood,
            "aligned_with_disposition": True}
