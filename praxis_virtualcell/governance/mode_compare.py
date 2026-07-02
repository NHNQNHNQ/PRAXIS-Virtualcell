"""M2.1 Step6:rule_only vs learned_with_rule_fallback 运行时对照(论文硬证据)。

用 151 ledger 复算(每条真 disagreement + 真 dp),证明默认 learned 模式**真的改变软风险决策**且**不破坏硬规则**:
- rule_only 软决策:disagreement > 阈值(0.5)才 flag(abstain/downgrade)——ledger 多 <0.5,故几乎不动。
- learned:冻结 reliability artifact 预测 dp → abstain/downgrade/accept(由训练分位阈值)。
- 真 label:bad = dp 底 bad_quantile(默认 25%)。
指标:wrong_accept↓ / unnecessary_abstain↓ / risk_coverage↑ / retained_utility↑ / hard_rule_override(=0)/ provenance_complete。

诚实:ledger 全为 human/in-vocab 软判定样本(无硬规则触发),故 hard_rule_override=0 by construction;硬规则不被
learned 覆盖另有单测(test_hard_abstain_not_overridden_by_learned)。pert-level(≠per-cell);disagreement 单 control。
"""
from __future__ import annotations

from praxis_virtualcell.governance import learned_reliability as L
from praxis_virtualcell.governance import ledger_features as lf

# score() 实际输出字段(reliability_mode 由 agent 层加、report 层 e2e 另测)
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
        flagged = []  # True = abstain/downgrade(flag 软风险)
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
        wa = sum(1 for b, f in zip(bad, flagged) if b and not f) / n_bad
        ua = sum(1 for b, f in zip(bad, flagged) if (not b) and f) / n_good
        rc = sum(1 for b, f in zip(bad, flagged) if b and f) / n_bad
        ru = sum(1 for b, f in zip(bad, flagged) if (not b) and not f) / n_good
        out[mode] = {"wrong_accept": wa, "unnecessary_abstain": ua,
                     "risk_coverage": rc, "retained_utility": ru,
                     "n_flagged": sum(flagged)}
    return {"n": len(entries), "n_bad": n_bad, "n_good": n_good, "bad_threshold": bad_thr,
            "hard_rule_override": 0, "provenance_complete": prov_ok, "modes": out}
