"""ST 为单位显著性检验 + 预注册效应量 CI 测试。"""
import numpy as np

from praxis_virtualcell.mdr_gnb.evaluators.significance import (
    st_level_vme,
    paired_permutation_test,
    bootstrap_effect_ci,
    load_preregistration,
)


def test_st_level_vme_aggregates():
    st = np.array(["A", "A", "B", "B"])
    y_true = np.array([1, 1, 1, 1])
    y_model = np.array([1, 1, 0, 1])   # B 内真R有2个,1个判S → VME=0.5
    per_st = st_level_vme(st, y_true, y_model)
    assert per_st["A"] == 0.0
    assert per_st["B"] == 0.5


def test_permutation_detects_improvement():
    sts = np.array([f"ST{i}" for i in range(20)])
    rule = np.full(20, 0.30)
    model = np.full(20, 0.10)          # 每个 ST model 都更好
    res = paired_permutation_test(model, rule, sts, n_perm=2000, seed=0)
    assert res["p_value"] < 0.05
    assert res["mean_diff"] < 0        # model - rule 为负(VME 更低)


def test_permutation_no_improvement_high_p():
    # model 比 rule 更差(VME 更高)→ 单侧"model 更优"检验不显著
    model = np.full(20, 0.40)
    rule = np.full(20, 0.10)
    res = paired_permutation_test(model, rule, None, n_perm=2000, seed=0)
    assert res["mean_diff"] > 0
    assert res["p_value"] > 0.05


def test_bootstrap_ci():
    diff = np.array([-0.2, -0.15, -0.1, -0.25, -0.18])
    lo, hi = bootstrap_effect_ci(diff, n_boot=2000, seed=0)
    assert lo < hi < 0


def test_load_preregistration():
    pre = load_preregistration()
    assert pre["significance_unit"] == "ST"
    assert pre["min_effect_size"] == 0.05
    assert pre["test"] == "paired_permutation"
