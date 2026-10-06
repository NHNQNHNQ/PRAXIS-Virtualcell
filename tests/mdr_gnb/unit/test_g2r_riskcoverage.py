"""G2R v2 risk-coverage 曲线结构不变量。"""
import numpy as np

from praxis_virtualcell.mdr_gnb.workflows.run_g2r_riskcoverage import risk_coverage_curve, _pooled


def test_full_coverage_equals_base():
    y = np.array([1, 0, 1, 0, 1])
    pred = np.array([1, 0, 0, 1, 1])
    conf = np.array([0.4, 0.3, 0.1, 0.2, 0.5])
    pts = risk_coverage_curve(y, pred, conf, n_points=10)
    assert pts[0]["coverage"] == 1.0
    v0, m0 = _pooled(y, pred)
    assert pts[0]["vme"] == round(v0, 4) and pts[0]["me"] == round(m0, 4)


def test_coverage_monotonic_decreasing():
    y = np.array([1, 0] * 20); pred = np.array([1, 0] * 20)
    conf = np.linspace(0, 1, 40)
    pts = risk_coverage_curve(y, pred, conf, n_points=10)
    covs = [p["coverage"] for p in pts]
    assert covs == sorted(covs, reverse=True)      # 覆盖率单调不增


def test_high_conf_kept_first_lowers_error():
    # 低置信样本恰是错的 → 弃权后 covered 子集 VME 应下降
    y = np.array([1, 1, 1, 1])          # 全真 R
    pred = np.array([1, 1, 1, 0])       # 最后一个漏判(VME)
    conf = np.array([0.9, 0.8, 0.7, 0.05])  # 漏判那个置信最低
    pts = risk_coverage_curve(y, pred, conf, n_points=4)
    assert pts[0]["vme"] == 0.25        # 满覆盖 1/4 漏
    assert pts[-1]["vme"] == 0.0        # 弃掉低置信 → 无漏


def test_per_st_vme_covered_excludes_abstained():
    import numpy as np
    from praxis_virtualcell.mdr_gnb.workflows.run_g2r_riskcoverage import _per_st_vme_covered
    st = np.array(["A", "A", "B", "B"])
    y = np.array([1, 1, 1, 1])          # 全真 R
    pred = np.array([0, 1, 0, 1])       # A 漏1/2,B 漏1/2
    covered_all = np.array([True, True, True, True])
    # 满覆盖:A VME=0.5,B VME=0.5 → 均值 0.5
    assert abs(_per_st_vme_covered(st, y, pred, covered_all) - 0.5) < 1e-9
    # 弃掉 A 的漏判那条 → A VME=0,B VME=0.5 → 均值 0.25
    covered = np.array([False, True, True, True])
    assert abs(_per_st_vme_covered(st, y, pred, covered) - 0.25) < 1e-9
