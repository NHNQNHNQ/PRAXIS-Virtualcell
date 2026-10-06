"""AST 评估指标测试:EA、分类误差 VME/ME、折点附近掩码、AUROC、ST 分组聚合。"""
import numpy as np

from praxis_virtualcell.mdr_gnb.evaluators.ast_metrics import (
    essential_agreement,
    categorical_errors,
    auroc_auprc,
    near_breakpoint_mask,
    compute_ast_metrics,
)


def test_essential_agreement():
    true = np.array([2.0, 3.0, 5.0])
    pred = np.array([2.4, 4.5, 5.0])
    ea = essential_agreement(true, pred)
    assert abs(ea["ea_pm1"] - (2 / 3)) < 1e-9  # 第2个差1.5 超±1
    assert ea["ea_pm2"] == 1.0


def test_categorical_errors():
    y_true = np.array([1, 1, 0, 0])   # R,R,S,S
    y_pred = np.array([0, 1, 1, 0])   # 第1个 VME(真R判S),第3个 ME(真S判R)
    err = categorical_errors(y_true, y_pred)
    assert abs(err["vme"] - 0.5) < 1e-9   # 1/2 真R被判S
    assert abs(err["me"] - 0.5) < 1e-9    # 1/2 真S被判R


def test_near_breakpoint_subset():
    mic_log2 = np.array([-3.0, 1.5, 2.5, 6.0])
    m = near_breakpoint_mask(mic_log2, r_min_log2=2.0, window=1.0)  # [1,3] 区间
    assert m.tolist() == [False, True, True, False]


def test_auroc_perfect():
    y = np.array([0, 0, 1, 1])
    s = np.array([0.1, 0.2, 0.8, 0.9])
    m = auroc_auprc(y, s)
    assert abs(m["auroc"] - 1.0) < 1e-9


def test_compute_ast_metrics_st_unit():
    # ST 为显著性单位:全局 VME 与 per-ST 平均 VME 分开
    y_true = np.array([1, 1, 1, 0])
    y_pred = np.array([0, 1, 1, 1])
    groups = np.array(["A", "A", "B", "B"])
    m = compute_ast_metrics(y_true, y_pred, groups)
    assert abs(m["vme"] - (1 / 3)) < 1e-9        # 全局:真R{0,1,2},判S仅idx0 → 1/3
    assert abs(m["vme_by_st"] - 0.25) < 1e-9     # A:0.5, B:0 → 平均0.25
    assert m["n_st"] == 2
