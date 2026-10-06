"""风险-覆盖分析测试:AURC、校准集选阈值、VME-coverage。"""
import numpy as np

from praxis_virtualcell.mdr_gnb.evaluators.risk_coverage import (
    risk_coverage_curve,
    aurc,
    select_threshold_on_calibration,
    vme_at_coverage,
)


def test_aurc_confidence_ordering():
    y_true = np.array([1, 1, 0, 0, 1, 0])
    y_pred = np.array([1, 1, 0, 0, 0, 1])   # 后两个错
    conf = np.array([0.9, 0.8, 0.7, 0.6, 0.3, 0.2])  # 错样本置信低
    cov, risk = risk_coverage_curve(y_true, y_pred, conf)
    assert cov[0] < cov[-1]
    assert aurc(cov, risk) < 0.3


def test_threshold_selected_on_calibration_only():
    y_cal = np.array([1, 1, 0, 0])
    p_cal = np.array([1, 1, 0, 1])
    c_cal = np.array([0.9, 0.8, 0.7, 0.4])
    thr = select_threshold_on_calibration(y_cal, p_cal, c_cal, target_risk=0.0)
    assert thr > 0.4   # 弃权掉置信 0.4 的错样本


def test_vme_at_coverage():
    y = np.array([1, 1, 1, 0])
    pred = np.array([0, 1, 1, 0])
    conf = np.array([0.2, 0.9, 0.8, 0.7])
    v = vme_at_coverage(y, pred, conf, coverage=0.75)  # 保留置信最高 3 个
    assert v == 0.0
