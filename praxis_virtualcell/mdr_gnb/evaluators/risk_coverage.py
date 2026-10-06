"""风险-覆盖分析:AURC + VME-coverage。

弃权阈值只允许在独立校准集选(select_threshold_on_calibration),禁止在 test 上调阈(防泄漏)。
coverage = 保留(不弃权)比例,risk = 保留集内错误率。VME-coverage 供 G2 操作点对齐用。
"""
from __future__ import annotations

import numpy as np


def _sorted_by_conf(conf):
    return np.argsort(-np.asarray(conf, float))   # 置信降序


def risk_coverage_curve(y_true, y_pred, conf):
    """按置信降序逐步纳入样本,返回 (coverage, risk) 曲线。"""
    order = _sorted_by_conf(conf)
    yt = np.asarray(y_true, int)[order]
    yp = np.asarray(y_pred, int)[order]
    wrong = (yt != yp).astype(float)
    n = len(yt)
    cov, risk = [], []
    cum_wrong = 0.0
    for k in range(1, n + 1):
        cum_wrong += wrong[k - 1]
        cov.append(k / n)
        risk.append(cum_wrong / k)
    return np.array(cov), np.array(risk)


def aurc(cov: np.ndarray, risk: np.ndarray) -> float:
    """risk-coverage 曲线下面积(越低越好)。"""
    return float(np.trapezoid(risk, cov))


def select_threshold_on_calibration(y_cal, y_pred_cal, conf_cal, target_risk: float = 0.0) -> float:
    """在校准集上选能满足保留集风险 ≤ target_risk 的最低置信阈值(覆盖最大)。"""
    order = _sorted_by_conf(conf_cal)
    yt = np.asarray(y_cal, int)[order]
    yp = np.asarray(y_pred_cal, int)[order]
    conf = np.asarray(conf_cal, float)[order]
    wrong = (yt != yp).astype(float)
    best_thr = float("inf")
    cum = 0.0
    for k in range(1, len(yt) + 1):
        cum += wrong[k - 1]
        if cum / k <= target_risk + 1e-12:
            best_thr = conf[k - 1]
    return best_thr


def vme_at_coverage(y_true, y_pred, conf, coverage: float) -> float:
    """保留置信最高的 coverage 比例样本后,其上的 VME(真R判非R)。"""
    order = _sorted_by_conf(conf)
    keep = max(1, int(round(coverage * len(order))))
    idx = order[:keep]
    yt = np.asarray(y_true, int)[idx]
    yp = np.asarray(y_pred, int)[idx]
    r = yt == 1
    return float((yp[r] == 0).mean()) if r.any() else float("nan")
