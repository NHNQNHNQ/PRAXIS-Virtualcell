"""Compare rule_only with learned_with_rule_fallback on the 151-row ledger. Rules flag disagreement>0.5; learned
frozen scores use training-quantile thresholds. Bad labels are the bottom bad_quantile (default 25%). Report
wrong_accept, unnecessary_abstain, risk_coverage, retained_utility, hard_rule_override, and provenance
completeness. Human/in-vocabulary soft-risk rows imply hard_rule_override=0 by construction; hard-rule
preservation is separately tested.
"""  # noqa: E501
from __future__ import annotations

from praxis_virtualcell.governance import learned_reliability as L
from praxis_virtualcell.governance import ledger_features as lf

_PROV_FIELDS = ("reliability_score", "abstain_score", "abstain_decision", "features_used",
                "model_version", "feature_schema_version", "artifact_sha256", "fallback")


def _quantile(vals, q):
    s = sorted(v for v in vals if v is not None and v == v)
    return s[max(0, min(len(s) - 1, int(q * (len(s) - 1))))]


def compare(entries, *, bad_quantile=0.25, rule_threshold=0.5):
    rows = lf.extract_features(entries)
    y = [lf.reliability_target(e) for e in entries]
    bad_thr = _quantile(y, bad_quantile)
    bad = [(v is not None and v <= bad_thr) for v in y]
    n_bad = sum(bad)
    n_good = sum(1 for b in bad if not b)

    out = {}
    prov_ok = True
    for mode in ("rule_only", "learned_with_rule_fallback"):
        flagged = []
        for r in rows:
            dis = r.get("disagreement_score")
            if mode == "rule_only":
                flag = dis is not None and dis > rule_threshold
            else:
                lr = L.score(r)
                if lr.get("fallback"):
                    flag = dis is not None and dis > rule_threshold  # fallback → rule
                else:
                    flag = lr["abstain_decision"] in ("abstain", "downgrade")
                    if not all(k in lr for k in _PROV_FIELDS):
                        prov_ok = False
            flagged.append(flag)
        wa = sum(1 for b, f in zip(bad, flagged) if b and not f) / n_bad  # noqa: B905
        ua = sum(1 for b, f in zip(bad, flagged) if (not b) and f) / n_good  # noqa: B905
        rc = sum(1 for b, f in zip(bad, flagged) if b and f) / n_bad  # noqa: B905
        ru = sum(1 for b, f in zip(bad, flagged) if (not b) and not f) / n_good  # noqa: B905
        out[mode] = {"wrong_accept": wa, "unnecessary_abstain": ua,
                     "risk_coverage": rc, "retained_utility": ru,
                     "n_flagged": sum(flagged)}
    return {"n": len(entries), "n_bad": n_bad, "n_good": n_good, "bad_threshold": bad_thr,
            "hard_rule_override": 0, "provenance_complete": prov_ok, "modes": out}
