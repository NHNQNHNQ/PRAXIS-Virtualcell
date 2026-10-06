"""AST 评估:EA ±1/±2 log2、ME/VME、AUROC/AUPRC、折点附近子集掩码、ST 分组聚合。

约定:y_true/y_pred 为二分类 R=1/非R=0;VME=真R判非R,ME=真非R判R。
G2 以 **ST 为显著性单位**:compute_ast_metrics 同时给全局(micro)与 per-ST 平均(macro)VME/ME。
essential_agreement/near_breakpoint 为 MIC(log2)口径,NCBI-only 无定量 MIC 时锚点不用,保留备 BV-BRC。
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


def essential_agreement(true_log2: np.ndarray, pred_log2: np.ndarray) -> dict:
    """log2-MIC 的 ±1/±2 稀释一致率(essential agreement)。"""
    d = np.abs(np.asarray(true_log2, float) - np.asarray(pred_log2, float))
    return {
        "ea_pm1": float((d <= 1.0 + 1e-9).mean()),
        "ea_pm2": float((d <= 2.0 + 1e-9).mean()),
        "n": int(len(d)),
    }


def categorical_errors(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """全局 VME(真R判非R)/ME(真非R判R)。"""
    yt, yp = np.asarray(y_true, int), np.asarray(y_pred, int)
    r = yt == 1
    s = yt == 0
    vme = float((yp[r] == 0).mean()) if r.any() else float("nan")
    me = float((yp[s] == 1).mean()) if s.any() else float("nan")
    return {"vme": vme, "me": me, "n_R": int(r.sum()), "n_S": int(s.sum())}


def near_breakpoint_mask(mic_log2: np.ndarray, r_min_log2: float, window: float = 1.0) -> np.ndarray:
    """折点附近子集掩码(临界耐药株,锚点门在此比 VME 最能证伪)。"""
    x = np.asarray(mic_log2, float)
    return (x >= r_min_log2 - window) & (x <= r_min_log2 + window)


def auroc_auprc(y_true: np.ndarray, score: np.ndarray) -> dict:
    """AUROC/AUPRC;单类退化返回 nan。"""
    yt = np.asarray(y_true, int)
    if len(np.unique(yt)) < 2:
        return {"auroc": float("nan"), "auprc": float("nan")}
    return {
        "auroc": float(roc_auc_score(yt, score)),
        "auprc": float(average_precision_score(yt, score)),
    }


def compute_ast_metrics(y_true, y_pred, groups) -> dict:
    """VME/ME 全局(micro)+ 按 ST 平均(macro,ST 为显著性单位),支持分组聚合。

    per-ST VME 只在含 ≥1 真R 的 ST 上计算再取均值;ME 只在含 ≥1 真非R 的 ST 上。
    """
    yt = np.asarray(y_true, int)
    yp = np.asarray(y_pred, int)
    g = np.asarray(groups)

    glob = categorical_errors(yt, yp)

    vme_per_st, me_per_st = [], []
    for st in np.unique(g):
        m = g == st
        gt, gp = yt[m], yp[m]
        if (gt == 1).any():
            vme_per_st.append(float((gp[gt == 1] == 0).mean()))
        if (gt == 0).any():
            me_per_st.append(float((gp[gt == 0] == 1).mean()))

    return {
        "vme": glob["vme"],
        "me": glob["me"],
        "n_R": glob["n_R"],
        "n_S": glob["n_S"],
        "vme_by_st": float(np.mean(vme_per_st)) if vme_per_st else float("nan"),
        "me_by_st": float(np.mean(me_per_st)) if me_per_st else float("nan"),
        "n_st": int(len(np.unique(g))),
    }
