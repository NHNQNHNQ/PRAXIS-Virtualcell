"""M2.1 Step3:Learned Abstain head —— 用 reliability 预测做选择性预测(risk-coverage)。

把 v0.2 表 C 的"按 disagreement 弃权"升级为"按 **learned reliability** 弃权":按可靠性分数排序,
弃权预测最差的扰动 → 保留集 dp 随 coverage 的曲线 + AUC。对照 learned / disagreement-only(v0.2)/
OOD-only / random / oracle(真 dp 上界)。纯 Python,Mac;无泄漏(learned 用 OOF 预测,坑1);pert-level（坑2)。

诚实:这是 **pert-level** risk-coverage(基于 ledger per-pert dp),≠ v0.2 的 per-cell 表 C,互补不替代。
"""
from __future__ import annotations

from praxis_virtualcell.governance import reliability_model as rm

_NAN = float("nan")
COVERAGES = (1.0, 0.9, 0.8, 0.7, 0.6, 0.5)


def _isnan(x):
    return x != x


def risk_coverage(reliability_score, true_dp, coverages=COVERAGES):
    """reliability_score 越大=越该保留;返回 [(coverage, 保留集平均真 dp)]。"""
    pairs = [(s, d) for s, d in zip(reliability_score, true_dp) if not (_isnan(s) or _isnan(d))]
    pairs.sort(key=lambda x: -x[0])             # 最可靠的排前
    n = len(pairs)
    out = []
    for c in coverages:
        k = max(1, int(round(c * n)))
        kept = [d for _, d in pairs[:k]]
        out.append((c, sum(kept) / len(kept)))
    return out


def rc_auc(curve):
    """risk-coverage 曲线下面积(按 coverage 梯形积分,归一化)。越大=选择性弃权越有效。"""
    pts = sorted(curve)
    if len(pts) < 2:
        return pts[0][1] if pts else _NAN
    area = sum((pts[i][0] - pts[i - 1][0]) * (pts[i][1] + pts[i - 1][1]) / 2
               for i in range(1, len(pts)))
    span = pts[-1][0] - pts[0][0]
    return area / span if span else pts[0][1]


def evaluate_abstain(entries, *, k=5, coverages=COVERAGES):
    """各排序信号的 risk-coverage 曲线 + AUC。learned 用 reliability OOF 预测(无泄漏)。"""
    oof, y = rm.cv_reliability(entries, k=k)          # learned OOF 预测 dp
    X, _ = rm._matrix(entries)
    dis = [r[0] for r in X]                            # disagreement_score
    seen = [r[1] for r in X]                           # seen_in_train(1=seen)
    import random as _r
    rnd = _r.Random(0)
    signals = {
        "learned": oof,                               # 预测 dp 高=保留
        "disagreement_only": [(-d if not _isnan(d) else _NAN) for d in dis],  # 分歧高=弃权
        "ood_only": [(0.5 if _isnan(s) else s) for s in seen],                # seen=保留
        "random": [rnd.random() for _ in y],
        "oracle": y,                                  # 真 dp = 上界
    }
    res = {}
    for name, sc in signals.items():
        curve = risk_coverage(sc, y, coverages)
        res[name] = {"curve": [(round(c, 2), round(v, 4)) for c, v in curve],
                     "auc": rc_auc(curve)}
    return res
