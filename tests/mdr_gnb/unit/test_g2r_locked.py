"""G2R locked 评估的方法学不变量(Milestone 3-4)。防 ST 泄漏、候选逻辑、选择规则。"""
import numpy as np

from praxis_virtualcell.mdr_gnb.workflows.run_g2r_locked import (
    st_dev_locked_split, _candidate_preds, dev_select, CANDIDATES, ME_BUDGET,
)


def test_st_no_leak_between_dev_and_locked():
    # 同一 ST 的样本绝不能跨 dev/locked(否则 locked 泄漏)
    ids = [f"g{i}" for i in range(200)]
    st_map = {f"g{i}": f"ST{i % 20}" for i in range(200)}   # 20 个 ST
    dev, lock = st_dev_locked_split(ids, st_map, locked_frac=0.25, seed=0)
    dev_st = {st_map[i] for i in dev}
    lock_st = {st_map[i] for i in lock}
    assert dev_st.isdisjoint(lock_st), "ST 跨 dev/locked 泄漏!"
    assert set(dev) | set(lock) == set(ids)            # 无丢样本
    assert set(dev) & set(lock) == set()               # 无重叠


def test_unknown_st_goes_to_dev():
    ids = ["a", "b", "c"]
    st_map = {"a": "ST1", "b": "ST2"}                  # c 无 ST
    dev, lock = st_dev_locked_split(ids, st_map, locked_frac=0.5, seed=1)
    assert "c" in dev and "c" not in lock              # unknown-ST 全归 dev


def test_split_deterministic():
    ids = [f"g{i}" for i in range(100)]
    st_map = {f"g{i}": f"ST{i % 10}" for i in range(100)}
    a = st_dev_locked_split(ids, st_map, seed=0)
    b = st_dev_locked_split(ids, st_map, seed=0)
    assert a == b                                      # 同 seed 可复现


def test_fusion_never_worse_vme_than_rule():
    # rule-first 融合:真 R 被判 S(VME)当且仅当 rule=S 且 ml=S → 融合 VME ≤ 规则 VME
    p_te = np.array([0.1, 0.9, 0.1, 0.8])
    rule = np.array([0, 0, 1, 0])
    preds = _candidate_preds(p_te, rule, t_aligned=0.5, t_budget=0.5)
    fusion = preds["fusion_aligned"]
    # 融合处处 ≥ 规则(规则判 R 的位置融合也判 R)
    assert np.all(fusion >= rule)


def test_candidates_complete():
    p_te = np.array([0.2, 0.7]); rule = np.array([0, 1])
    preds = _candidate_preds(p_te, rule, t_aligned=0.5, t_budget=0.3)
    assert set(preds) == set(CANDIDATES)


def test_me_budget_is_prereg_constant():
    assert ME_BUDGET == 0.10           # 预注册常数,改动即改门(留痕)
