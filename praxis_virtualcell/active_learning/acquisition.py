"""Deterministic information-gain-inspired priority heuristic, not Bayesian expected information gain. Higher
disagreement, OOD, weaker evidence, and weaker module support increase priority. Missing signals contribute 0;
no clock, randomness, or LLM is used.
"""
from __future__ import annotations

_W_DISAGREEMENT = 1.0
_W_DIS_TRIGGERED = 0.5
_W_OOD = {"ood": 1.0, "unknown": 0.6, "in_domain": 0.0}

_W_EVIDENCE = {"E0": 0.2, "E1": 0.3, "E2": 0.0, "E3": 0.4, "E4": 0.8, "E5": 1.0}
_W_MODULE_WEAK = 0.5


def information_gain(signals: dict) -> float:
    """Weight optional signals deterministically; missing values contribute 0. Signals: disagreement_score (float),
    disagreement_triggered (bool), ood_signal (str), evidence_level (E0..E5), and module_weak (bool).
    """
    dis = signals.get("disagreement_score")
    dis = float(dis) if isinstance(dis, (int, float)) else 0.0
    g = _W_DISAGREEMENT * max(0.0, min(1.0, dis))
    if signals.get("disagreement_triggered"):
        g += _W_DIS_TRIGGERED
    g += _W_OOD.get(str(signals.get("ood_signal", "")), 0.0)
    g += _W_EVIDENCE.get(str(signals.get("evidence_level", "")), 0.0)
    if signals.get("module_weak"):
        g += _W_MODULE_WEAK
    return round(g, 6)
