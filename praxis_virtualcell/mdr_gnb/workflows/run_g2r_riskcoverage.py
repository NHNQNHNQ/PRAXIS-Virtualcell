"""G2R v2:abstain-aware risk-coverage 曲线(选择性预测)。

预测器 = rule-first 融合 + 置信度弃权:
  - rule 判 R → 判 R,置信度=∞(恒保留,规则强信号不弃)。
  - rule 判 S → ML:pred=(prob_R≥t*),置信度=|prob_R−t*|(离阈值越远越有把握)。
  - 弃权最不确定的样本 → 覆盖率下降,covered 子集上算 pooled VME/ME。

纪律:t* 在 dev 上对齐规则 ME;ML 训练只用 dev;曲线在 held-out locked 上一次算出。
诚实:曲线用 pooled VME/ME(选择性预测标准);另在满覆盖与运行点报 per-ST VME 与规则对齐一致性。
"""
from __future__ import annotations

import numpy as np

from ..evaluators.lineage_split import make_lineage_splits
from ..evaluators.significance import align_st_vme, paired_permutation_test, st_level_vme
from ..predictors.features import FeatureSpec, build_feature_matrix
from ..predictors.genotype_to_sir import GenotypeToSIR
from .run_g2r_locked import _me, _rule_pred, _st_of, _threshold_for_me, _y

COV_FLOOR = 0.80        # 预注册:覆盖率地板(弃权 ≤20%,保工具可用)
ME_CAP = 0.10           # 预注册:covered 子集 ME 上限


def _pooled(y, pred):
    R, S = (y == 1), (y == 0)
    vme = float((pred[R] == 0).mean()) if R.any() else float("nan")
    me = float((pred[S] == 1).mean()) if S.any() else float("nan")
    return vme, me


def risk_coverage_curve(y, pred, conf, *, n_points=19):
    """按置信度降序保留,扫覆盖率 → [(coverage, vme, me, n), ...]。coverage=1 即满覆盖 base。"""
    order = np.argsort(-conf, kind="stable")     # 高置信在前(∞ 的 rule-R 恒在最前)
    N = len(y)
    pts = []
    for frac in np.linspace(0.0, 0.9, n_points):  # 弃权最低置信的 frac 比例
        k = max(1, int(round(N * (1.0 - frac))))
        keep = order[:k]
        vme, me = _pooled(y[keep], pred[keep])
        pts.append({"coverage": round(k / N, 4), "vme": round(vme, 4), "me": round(me, 4), "n": k})
    return pts


def anchor_risk_coverage(dev_rows, lock_rows, st_map, rule, drug, *, seed=0, model="rf", n_points=19):
    """训 ML(全 dev)→ locked 上 rule-first 融合 + 置信弃权 → risk-coverage 曲线。"""
    fm = build_feature_matrix(dev_rows, st_map)
    Xlk = FeatureSpec.transform(fm.spec, lock_rows)
    ml = GenotypeToSIR(random_state=seed, model=model).fit(fm.X, fm.y_sir)
    p_dev = ml.predict_proba_r(fm.X)
    p_lk = ml.predict_proba_r(Xlk)
    rule_dev = _rule_pred(rule, drug, dev_rows)
    t_star = _threshold_for_me(p_dev, fm.y_sir, _me(fm.y_sir, rule_dev))   # dev 上对齐规则 ME
    rule_lk = _rule_pred(rule, drug, lock_rows)
    y = _y(lock_rows)
    base = np.where(rule_lk == 1, 1, (p_lk >= t_star).astype(int))         # rule-first 融合
    conf = np.where(rule_lk == 1, np.inf, np.abs(p_lk - t_star))           # rule-R 恒保留
    curve = risk_coverage_curve(y, base, conf, n_points=n_points)
    rule_vme, rule_me = _pooled(y, rule_lk)                                # locked 上规则法参照(满覆盖)
    return {"drug": drug, "n_locked": len(lock_rows), "t_star": round(float(t_star), 3),
            "curve": curve, "rule_vme": round(rule_vme, 4), "rule_me": round(rule_me, 4)}


def _per_st_vme_covered(st, y, pred, covered):
    """covered 子集上的 per-ST VME 均值(仅计有 covered 真 R 的 ST)。"""
    stc, yc, pc = st[covered], y[covered], pred[covered]
    v = st_level_vme(stc, yc, pc)
    return float(np.mean(list(v.values()))) if v else float("nan")


def _dev_oof(dev_rows, st_map, rule, drug, seed, model):
    """dev 5 折 OOF:返回 (y, st, base_pred, rule_pred, conf)。base=rule-first 融合,conf=|p-t*|(rule-R=inf)。"""
    id2 = {(r.get("genome_id") or "").strip(): r for r in dev_rows}
    ids = list(id2)
    specs = make_lineage_splits(ids, st_map, n_splits=5)
    Y, ST, BASE, RULE, CONF = [], [], [], [], []
    for s in specs:
        tr = [id2[g] for g in s.train_ids]; te = [id2[g] for g in s.test_ids]
        fm = build_feature_matrix(tr, st_map)
        Xte = FeatureSpec.transform(fm.spec, te)
        ml = GenotypeToSIR(random_state=seed, model=model).fit(fm.X, fm.y_sir)
        p_tr, p_te = ml.predict_proba_r(fm.X), ml.predict_proba_r(Xte)
        rule_tr, rule_te = _rule_pred(rule, drug, tr), _rule_pred(rule, drug, te)
        t = _threshold_for_me(p_tr, fm.y_sir, _me(fm.y_sir, rule_tr))
        base = np.where(rule_te == 1, 1, (p_te >= t).astype(int))
        conf = np.where(rule_te == 1, np.inf, np.abs(p_te - t))
        Y.append(_y(te)); ST.append(_st_of(te, st_map)); BASE.append(base); RULE.append(rule_te); CONF.append(conf)
    return (np.concatenate(Y), np.concatenate(ST), np.concatenate(BASE),
            np.concatenate(RULE), np.concatenate(CONF))


def dev_operating_point(dev_rows, st_map, rule, drug, *, seed=0, model="rf"):
    """预注册运行点选择:dev OOF 上,覆盖率≥COV_FLOOR 且 covered ME<ME_CAP 时,选 per-ST VME 最小的
    置信阈值 τ*(并列取更高覆盖)。返回 (tau_star, dev_table)。"""
    y, st, base, rule_p, conf = _dev_oof(dev_rows, st_map, rule, drug, seed, model)
    N = len(y)
    finite = np.sort(np.unique(conf[np.isfinite(conf)]))
    taus = [0.0] + [float(t) for t in finite]        # τ=0 → 满覆盖
    rows = []
    for tau in taus:
        covered = conf >= tau
        cov = float(covered.mean())
        if cov < COV_FLOOR:                          # 低于地板不考虑(但记录用于诊断)
            continue
        me_c = _me(y[covered], base[covered])
        if me_c >= ME_CAP:
            continue
        vme_c = _per_st_vme_covered(st, y, base, covered)
        rows.append({"tau": tau, "coverage": cov, "per_st_vme": vme_c, "me": me_c})
    if not rows:                                     # 无合格 τ → 满覆盖兜底
        covered = conf >= 0.0
        rows = [{"tau": 0.0, "coverage": 1.0,
                 "per_st_vme": _per_st_vme_covered(st, y, base, covered),
                 "me": _me(y, base)}]
    best = min(rows, key=lambda r: (r["per_st_vme"], -r["coverage"]))
    return best["tau"], rows


def locked_operating_verdict(dev_rows, lock_rows, st_map, rule, drug, tau, *, seed=0, model="rf", n_perm=10000):
    """把 dev 选定的 τ 应用到 locked 一次:covered 子集上 fusion vs 规则 per-ST VME + 置换检验。"""
    fm = build_feature_matrix(dev_rows, st_map)
    Xlk = FeatureSpec.transform(fm.spec, lock_rows)
    ml = GenotypeToSIR(random_state=seed, model=model).fit(fm.X, fm.y_sir)
    t = _threshold_for_me(ml.predict_proba_r(fm.X), fm.y_sir, _me(fm.y_sir, _rule_pred(rule, drug, dev_rows)))
    p_lk = ml.predict_proba_r(Xlk)
    rule_lk = _rule_pred(rule, drug, lock_rows)
    y, stv = _y(lock_rows), _st_of(lock_rows, st_map)
    base = np.where(rule_lk == 1, 1, (p_lk >= t).astype(int))
    conf = np.where(rule_lk == 1, np.inf, np.abs(p_lk - t))
    covered = conf >= tau
    # 同一 covered 子集上,fusion vs 规则的 per-ST VME + 配对置换
    stc, yc, bc, rc = stv[covered], y[covered], base[covered], rule_lk[covered]
    v_fu, v_ru = st_level_vme(stc, yc, bc), st_level_vme(stc, yc, rc)
    keys, mm, rr = align_st_vme(v_fu, v_ru)
    if len(keys) >= 1:
        perm = paired_permutation_test(mm, rr, keys, n_perm=n_perm, seed=seed)
        effect, pval = perm["mean_diff"], perm["p_value"]
    else:
        effect, pval = float("nan"), float("nan")
    me_fu, me_ru = _me(yc, bc), _me(yc, rc)
    dv = float(mm.mean() - rr.mean()) if len(keys) else float("nan")
    if len(keys) and dv < 0 and pval < 0.05 and me_fu < ME_CAP:
        verdict = "G2R-strong-pass"
    elif len(keys) and dv <= 0.001 and me_fu < ME_CAP:
        verdict = "G2R-practical-pass"
    else:
        verdict = "G2R-fail"
    return {"tau": tau, "verdict": verdict, "coverage": float(covered.mean()),
            "n_locked": len(lock_rows), "n_covered": int(covered.sum()), "n_st_with_R": len(keys),
            "per_st_vme_fusion": float(mm.mean()) if len(keys) else float("nan"),
            "per_st_vme_rule": float(rr.mean()) if len(keys) else float("nan"),
            "delta_vme": dv, "p_value": pval, "me_fusion": me_fu, "me_rule": me_ru}
