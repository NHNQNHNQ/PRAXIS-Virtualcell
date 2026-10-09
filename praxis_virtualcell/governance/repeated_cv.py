"""Repeated seeded 5-fold leave-perturbation-out CV. Shuffle perturbation order before deterministic modulo
splitting, then summarize bad-perturbation AUROC and selective risk-coverage AUC across seeds as
mean/sd/min/max. Preserve inference-only features and perturbation-level isolation.
"""
from __future__ import annotations

import random as _random

from praxis_virtualcell.governance import abstain_head as ah
from praxis_virtualcell.governance import reliability_model as rm

_KEYS = ("auroc_learned", "auroc_disagreement", "reg_corr", "rc_auc_learned", "rc_auc_disagreement")


def _shuffle(entries, seed):
    idx = list(range(len(entries)))
    _random.Random(seed).shuffle(idx)
    return [entries[i] for i in idx]


def repeated_cv(entries, *, seeds=(0, 1, 2, 3, 4), k=5):
    """Shuffle by each seed, run CV, and return seeds/k/per_seed/summary."""
    rows = []
    for s in seeds:
        sh = _shuffle(entries, s)
        rel = rm.evaluate(sh, k=k)
        ab = ah.evaluate_abstain(sh, k=k)
        rows.append({
            "seed": s,
            "auroc_learned": rel["auroc"]["learned"],
            "auroc_disagreement": rel["auroc"]["disagreement_only"],
            "reg_corr": rel["reg_corr_pred_vs_true"],
            "rc_auc_learned": ab["learned"]["auc"],
            "rc_auc_disagreement": ab["disagreement_only"]["auc"],
        })

    def _summ(key):
        vals = [r[key] for r in rows]
        m = sum(vals) / len(vals)
        sd = (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5
        return {"mean": m, "sd": sd, "min": min(vals), "max": max(vals)}

    return {"seeds": list(seeds), "k": k, "per_seed": rows,
            "summary": {key: _summ(key) for key in _KEYS}}
