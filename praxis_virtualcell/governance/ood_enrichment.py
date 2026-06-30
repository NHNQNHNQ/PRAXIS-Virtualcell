"""M2.1 投稿前补强 L2:OOD enrichment / OOD-only risk-coverage(纯 Python,Mac 可跑)。

回答"learned abstain 是否偏好弃权 OOD(未见)扰动",并区分 learned 是否只是 OOD 标签的代理。
- OOD 标签来自 ledger `seen_in_train`(推理期 OOD flag,**特征非 label**;82/151 未见,与 v0.2 表 C split 一致)。
- 复用 `bootstrap_ci._prepare`(固定 OOF 预测 + frozen learned/rule 软风险 flag)、`abstain_head` risk-coverage。
- odds ratio 用 Haldane–Anscombe(+0.5)校正,避免除零。

诚实:learned 模型显式含 `seen_in_train` 特征,故 enrichment 部分由该特征驱动;但 learned bad-pert AUROC 0.907
> ood-only 0.788(reliability_model),且 OOD-only 子集内仍有 risk-coverage 选择性 ⇒ learned **超越** OOD 标签本身。
pert-level(≠per-cell);runtime `seen_in_train` 多 None(此分析在 ledger 上 flag 齐全)。
"""
from __future__ import annotations

from praxis_virtualcell.governance import abstain_head as ah
from praxis_virtualcell.governance import bootstrap_ci as bc
from praxis_virtualcell.governance import reliability_model as rm

_NAN = float("nan")


def _isnan(x):
    return x != x


def _get(e, k):
    """兼容 dict 与 LedgerEntry(dataclass)。"""
    return e.get(k) if isinstance(e, dict) else getattr(e, k, None)


def ood_labels(entries):
    """True = OOD(unseen);False = seen;None = unknown。seen_in_train: True/1=seen → 非OOD。"""
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
    """OOD enrichment + OOD-only/seen-only risk-coverage。返回全部诊断标量。"""
    oof, y, dis, rule_flag, learned_flag = bc._prepare(entries)
    ood = ood_labels(entries)
    valid = [i for i in range(len(entries)) if ood[i] is not None]
    n = len(valid)
    n_ood = sum(1 for i in valid if ood[i])
    n_seen = n - n_ood
    base = n_ood / n if n else _NAN

    # 2x2 列联表(learned flagged=abstain/downgrade vs retained) × (OOD vs seen)
    a = sum(1 for i in valid if learned_flag[i] and ood[i])          # flagged & OOD
    b = sum(1 for i in valid if learned_flag[i] and not ood[i])      # flagged & seen
    c = sum(1 for i in valid if (not learned_flag[i]) and ood[i])    # retained & OOD
    d = sum(1 for i in valid if (not learned_flag[i]) and not ood[i])  # retained & seen
    odds_ratio = ((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5))   # Haldane–Anscombe

    # 子集 risk-coverage(learned 排序 = oof 预测 dp 高=保留)
    ood_idx = [i for i in valid if ood[i]]
    seen_idx = [i for i in valid if not ood[i]]
    rc_ood = ah.rc_auc(ah.risk_coverage([oof[i] for i in ood_idx], [y[i] for i in ood_idx]))
    rc_seen = ah.rc_auc(ah.risk_coverage([oof[i] for i in seen_idx], [y[i] for i in seen_idx]))

    rel = rm.evaluate(entries)  # 支撑"learned 不只是 OOD 标签":learned AUROC > ood-only AUROC

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
