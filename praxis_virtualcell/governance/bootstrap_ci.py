"""Perturbation-level percentile bootstrap of fixed OOF predictions and frozen decisions from the 151-row ledger.
Resample 151 perturbations with replacement and recompute metrics for 95% CIs. This measures metric stability
under perturbation sampling, not model-retraining uncertainty. Preserve the same bad_quantile, rule_threshold,
and frozen learned decision definitions as mode_compare.
"""
from __future__ import annotations

import random as _random

from praxis_virtualcell.governance import abstain_head as ah
from praxis_virtualcell.governance import learned_reliability as L
from praxis_virtualcell.governance import ledger_features as lf
from praxis_virtualcell.governance import reliability_model as rm

_NAN = float("nan")


def _isnan(x):
    return x != x


def _pct(vals, q):
    """Linearly interpolated percentile of a nonempty value list."""
    s = sorted(vals)
    if not s:
        return _NAN
    i = q * (len(s) - 1)
    lo = int(i)
    hi = min(lo + 1, len(s) - 1)
    frac = i - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def _quantile(vals, q):
    s = sorted(v for v in vals if not _isnan(v))
    if not s:
        return _NAN
    return s[max(0, min(len(s) - 1, int(q * (len(s) - 1))))]


def _prepare(entries):
    """Precompute fixed per-perturbation OOF dp, true dp, disagreement, and rule/learned soft-risk flags."""
    oof, y = rm.cv_reliability(entries)
    X, _ = rm._matrix(entries)
    dis = [r[0] for r in X]                          # disagreement_score(nan-filled)
    rows = lf.extract_features(entries)
    rule_flag, learned_flag = [], []
    for r in rows:
        d = r.get("disagreement_score")
        rf = d is not None and d > 0.5
        rule_flag.append(rf)
        lr = L.score(r)
        if lr.get("fallback"):
            learned_flag.append(rf)                 # fallback → rule
        else:
            learned_flag.append(lr["abstain_decision"] in ("abstain", "downgrade"))
    return oof, y, dis, rule_flag, learned_flag


def _metrics(idx, oof, y, dis, rule_flag, learned_flag, *, bad_quantile=0.25, rule_threshold=0.5):
    """Recompute metrics on a potentially repeated index list; return None when n_bad or n_good is 0 so that
    iteration can be skipped.
    """
    ys = [y[i] for i in idx]
    thr = _quantile(ys, bad_quantile)
    bad = [(not _isnan(y[i]) and y[i] <= thr) for i in idx]
    n_bad = sum(bad)
    n_good = len(idx) - n_bad
    if n_bad == 0 or n_good == 0:
        return None

    bad01 = [1 if b else 0 for b in bad]

    learned_auc_score = [(-oof[i] if not _isnan(oof[i]) else 0.0) for i in idx]
    dis_auc_score = [dis[i] for i in idx]
    auroc_learned = rm._auroc(learned_auc_score, bad01)
    auroc_dis = rm._auroc(dis_auc_score, bad01)

    yi = [y[i] for i in idx]
    rc_learned = ah.rc_auc(ah.risk_coverage([oof[i] for i in idx], yi))
    rc_dis = ah.rc_auc(ah.risk_coverage([(-dis[i] if not _isnan(dis[i]) else _NAN) for i in idx], yi))

    wa_rule = sum(1 for j in range(len(idx)) if bad[j] and not rule_flag[idx[j]]) / n_bad
    wa_learned = sum(1 for j in range(len(idx)) if bad[j] and not learned_flag[idx[j]]) / n_bad
    rc_rule = sum(1 for j in range(len(idx)) if bad[j] and rule_flag[idx[j]]) / n_bad
    rc_learned_mc = sum(1 for j in range(len(idx)) if bad[j] and learned_flag[idx[j]]) / n_bad
    ru_learned = sum(1 for j in range(len(idx)) if not bad[j] and not learned_flag[idx[j]]) / n_good
    ua_learned = sum(1 for j in range(len(idx)) if not bad[j] and learned_flag[idx[j]]) / n_good

    return {
        "auroc_learned": auroc_learned,
        "auroc_disagreement": auroc_dis,
        "rc_auc_learned": rc_learned,
        "rc_auc_disagreement": rc_dis,
        "mc_wrong_accept_rule": wa_rule,
        "mc_wrong_accept_learned": wa_learned,
        "mc_risk_coverage_rule": rc_rule,
        "mc_risk_coverage_learned": rc_learned_mc,
        "mc_retained_utility_learned": ru_learned,
        "mc_unnecessary_abstain_learned": ua_learned,
    }


def _augment_diffs(m):
    """Add learned-minus-baseline differences with signs oriented so positive means learned is better."""
    out = dict(m)
    out["auroc_diff_learned_minus_disagreement"] = m["auroc_learned"] - m["auroc_disagreement"]
    out["rc_auc_diff_learned_minus_disagreement"] = m["rc_auc_learned"] - m["rc_auc_disagreement"]
    out["mc_wrong_accept_reduction"] = m["mc_wrong_accept_rule"] - m["mc_wrong_accept_learned"]
    out["mc_risk_coverage_gain"] = m["mc_risk_coverage_learned"] - m["mc_risk_coverage_rule"]
    return out


def run(entries, *, b=2000, seed=0, bad_quantile=0.25, rule_threshold=0.5):
    """Return perturbation-level bootstrap metadata and metrics. point uses the full sample; ci_lo/ci_hi are
    bootstrap 2.5%/97.5% percentiles.
    """
    oof, y, dis, rule_flag, learned_flag = _prepare(entries)
    n = len(entries)
    full = list(range(n))
    args = (oof, y, dis, rule_flag, learned_flag)
    kw = {"bad_quantile": bad_quantile, "rule_threshold": rule_threshold}

    point = _augment_diffs(_metrics(full, *args, **kw))
    dists = {k: [] for k in point}
    rng = _random.Random(seed)
    n_valid = 0
    for _ in range(b):
        idx = [rng.randrange(n) for _ in range(n)]
        mm = _metrics(idx, *args, **kw)
        if mm is None:
            continue
        mm = _augment_diffs(mm)
        for k, v in mm.items():
            dists[k].append(v)
        n_valid += 1

    metrics = {}
    for k, pv in point.items():
        d = dists[k]
        metrics[k] = {
            "point": pv,
            "median": _pct(d, 0.5),
            "ci_lo": _pct(d, 0.025),
            "ci_hi": _pct(d, 0.975),
            "n_boot": len(d),
        }
    return {
        "n": n,
        "n_bootstrap": b,
        "n_valid": n_valid,
        "seed": seed,
        "bad_quantile": bad_quantile,
        "method": ("perturbation-level bootstrap over fixed OOF predictions (R2/R3, generalization) and "
                   "frozen decisions (R7, in-sample replay); metric sampling stability only, no CV retraining"),
        "metrics": metrics,
    }
