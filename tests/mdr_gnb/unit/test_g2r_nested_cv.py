"""G2R 嵌套 CV 的纯选择逻辑不变量。"""
import numpy as np

from praxis_virtualcell.mdr_gnb.workflows.run_g2r_nested_cv import select_tstar, ME_MARGIN


def test_select_respects_me_cap():
    # 构造:低 t* → 融合 ME 高;高 t* → ME 低。选中的 t* 必须满足 ME≤规则ME+MARGIN
    rng = np.random.RandomState(0)
    n = 400
    y = (rng.rand(n) < 0.4).astype(int)
    ru = np.where(y == 1, (rng.rand(n) < 0.6).astype(int), (rng.rand(n) < 0.1).astype(int))
    p = np.clip(y * 0.6 + rng.rand(n) * 0.5, 0, 1)   # 概率与标签相关
    st = np.array([f"ST{i%20}" for i in range(n)])
    rule_me = float((ru[y == 0] == 1).mean())
    t, pv, me = select_tstar(p, ru, y, st, rule_me=rule_me)
    assert me <= rule_me + ME_MARGIN + 1e-9        # 满足 ME 判据
    assert 0.02 <= t <= 0.98


def test_fusion_never_exceeds_rule_vme():
    # rule-first:选出的融合 per-ST VME 不会高于规则(兜底),即 pv 有限且 ≤ 规则 per-ST VME
    rng = np.random.RandomState(1)
    n = 300
    y = (rng.rand(n) < 0.5).astype(int)
    ru = np.where(y == 1, (rng.rand(n) < 0.5).astype(int), (rng.rand(n) < 0.15).astype(int))
    p = np.clip(y * 0.5 + rng.rand(n) * 0.6, 0, 1)
    st = np.array([f"ST{i%15}" for i in range(n)])
    from praxis_virtualcell.mdr_gnb.evaluators.significance import st_level_vme
    rule_vme = float(np.mean(list(st_level_vme(st, y, ru).values())))
    rule_me = float((ru[y == 0] == 1).mean())
    t, pv, me = select_tstar(p, ru, y, st, rule_me=rule_me)
    assert pv <= rule_vme + 1e-9                   # 融合 VME ≤ 规则 VME


def test_me_margin_prereg():
    assert ME_MARGIN == 0.05
