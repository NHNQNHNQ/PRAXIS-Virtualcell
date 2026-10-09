"""M2.1 投稿前补强 B3:多 seed 重复 5-fold CV(纯 Python,Mac 可跑)。

回应「单一确定性 5-fold」局限:打乱扰动顺序后做 leave-perturbation-out CV(`leave_perturbation_out_folds`
按索引取模分 fold,故打乱顺序 = 不同 fold 划分),跑多个 seed,报 learned / disagreement 的 bad-pert AUROC
与 abstain risk-coverage AUC 跨 seed 的 mean/sd/min/max。仍无泄漏(只用 INFERENCE_FEATURES)、pert-level。
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
    """对每个 seed 打乱顺序 → CV → 收集指标;返回 {seeds, k, per_seed, summary}。"""
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
