"""Perturbation-level selective prediction using learned reliability OOF estimates. Compare learned,
disagreement-only, OOD-only, random, and oracle rankings through risk-coverage curves and AUC. This ledger-based
perturbation analysis is distinct from per-cell evaluation; only inference-available features are used.
"""
from __future__ import annotations

from praxis_virtualcell.governance import reliability_model as rm

_NAN = float("nan")
COVERAGES = (1.0, 0.9, 0.8, 0.7, 0.6, 0.5)


def _isnan(x):
    return x != x


def risk_coverage(reliability_score, true_dp, coverages=COVERAGES):
    """Larger reliability_score favors retention; return (coverage, retained mean true dp) pairs."""
    pairs = [(s, d) for s, d in zip(reliability_score, true_dp) if not (_isnan(s) or _isnan(d))]  # noqa: B905
    pairs.sort(key=lambda x: -x[0])
    n = len(pairs)
    out = []
    for c in coverages:
        k = max(1, int(round(c * n)))
        kept = [d for _, d in pairs[:k]]
        out.append((c, sum(kept) / len(kept)))
    return out


def rc_auc(curve):
    """Normalized trapezoidal area under the coverage curve; larger values indicate more effective selective
    retention.
    """
    pts = sorted(curve)
    if len(pts) < 2:
        return pts[0][1] if pts else _NAN
    area = sum((pts[i][0] - pts[i - 1][0]) * (pts[i][1] + pts[i - 1][1]) / 2
               for i in range(1, len(pts)))
    span = pts[-1][0] - pts[0][0]
    return area / span if span else pts[0][1]


def evaluate_abstain(entries, *, k=5, coverages=COVERAGES):
    """Compute risk-coverage curves and AUC for ranking signals; learned scores use leakage-safe OOF predictions."""
    oof, y = rm.cv_reliability(entries, k=k)
    X, _ = rm._matrix(entries)
    dis = [r[0] for r in X]                            # disagreement_score
    seen = [r[1] for r in X]                           # seen_in_train(1=seen)
    import random as _r
    rnd = _r.Random(0)
    signals = {
        "learned": oof,
        "disagreement_only": [(-d if not _isnan(d) else _NAN) for d in dis],
        "ood_only": [(0.5 if _isnan(s) else s) for s in seen],
        "random": [rnd.random() for _ in y],
        "oracle": y,
    }
    res = {}
    for name, sc in signals.items():
        curve = risk_coverage(sc, y, coverages)
        res[name] = {"curve": [(round(c, 2), round(v, 4)) for c, v in curve],
                     "auc": rc_auc(curve)}
    return res
