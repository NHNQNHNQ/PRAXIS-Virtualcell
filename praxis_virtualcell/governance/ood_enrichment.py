"""Perturbation-level OOD enrichment and OOD-only/seen-only risk-coverage analysis. seen_in_train is an inference
feature; 82/151 ledger perturbations are unseen. Reuse fixed OOF scores and frozen soft-risk flags; apply
Haldane–Anscombe +0.5 correction to odds ratios. The learned model includes this OOD feature, so enrichment is
partly feature-driven; historical AUROC 0.907 vs OOD-only 0.788 is ledger-specific. Runtime missing values
remain unknown.
"""
from __future__ import annotations

from praxis_virtualcell.governance import abstain_head as ah
from praxis_virtualcell.governance import bootstrap_ci as bc
from praxis_virtualcell.governance import reliability_model as rm

_NAN = float("nan")


def _isnan(x):
    return x != x


def _get(e, k):
    """Read either a dictionary or LedgerEntry dataclass."""
    return e.get(k) if isinstance(e, dict) else getattr(e, k, None)


def ood_labels(entries):
    """Return True for unseen/OOD, False for seen, and None for unknown; seen_in_train=True/1 means in-domain."""
    out = []
    for e in entries:
        s = _get(e, "seen_in_train")
        if s in (True, 1):
            out.append(False)
        elif s in (False, 0):
            out.append(True)
        else:
            out.append(None)
    return out


def _frac_ood(valid, flag, ood, want):
    sel = [i for i in valid if flag[i] == want]
    if not sel:
        return None
    return sum(1 for i in sel if ood[i]) / len(sel)


def _mean_dp(idx, y):
    vals = [y[i] for i in idx if not _isnan(y[i])]
    return sum(vals) / len(vals) if vals else _NAN


def evaluate_ood(entries):
    """Compute OOD enrichment and OOD-only/seen-only risk-coverage diagnostics."""
    oof, y, dis, rule_flag, learned_flag = bc._prepare(entries)
    ood = ood_labels(entries)
    valid = [i for i in range(len(entries)) if ood[i] is not None]
    n = len(valid)
    n_ood = sum(1 for i in valid if ood[i])
    n_seen = n - n_ood
    base = n_ood / n if n else _NAN


    a = sum(1 for i in valid if learned_flag[i] and ood[i])          # flagged & OOD
    b = sum(1 for i in valid if learned_flag[i] and not ood[i])      # flagged & seen
    c = sum(1 for i in valid if (not learned_flag[i]) and ood[i])    # retained & OOD
    d = sum(1 for i in valid if (not learned_flag[i]) and not ood[i])  # retained & seen
    odds_ratio = ((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5))   # Haldane–Anscombe


    ood_idx = [i for i in valid if ood[i]]
    seen_idx = [i for i in valid if not ood[i]]
    rc_ood = ah.rc_auc(ah.risk_coverage([oof[i] for i in ood_idx], [y[i] for i in ood_idx]))
    rc_seen = ah.rc_auc(ah.risk_coverage([oof[i] for i in seen_idx], [y[i] for i in seen_idx]))

    rel = rm.evaluate(entries)

    return {
        "n": n,
        "n_ood": n_ood,
        "n_seen": n_seen,
        "base_rate_ood": base,
        "mean_dp_ood": _mean_dp(ood_idx, y),
        "mean_dp_seen": _mean_dp(seen_idx, y),
        "n_learned_flagged": a + b,
        "n_rule_flagged": sum(1 for i in valid if rule_flag[i]),
        "learned_flagged_ood_frac": _frac_ood(valid, learned_flag, ood, True),
        "learned_retained_ood_frac": _frac_ood(valid, learned_flag, ood, False),
        "rule_flagged_ood_frac": _frac_ood(valid, rule_flag, ood, True),
        "odds_ratio_learned": odds_ratio,
        "contingency": {"flagged_ood": a, "flagged_seen": b, "retained_ood": c, "retained_seen": d},
        "rc_auc_ood_only": rc_ood,
        "rc_auc_seen_only": rc_seen,
        "reliability_auroc_learned": rel["auroc"]["learned"],
        "reliability_auroc_ood_only": rel["auroc"]["ood_only"],
    }
