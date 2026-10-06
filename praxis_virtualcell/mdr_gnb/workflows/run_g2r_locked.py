"""G2R locked-test 评估(Milestone 3-4)。预注册、防 p-hacking、ST 不跨层、locked 只跑一次。

流程(单 species×drug):
  1. st_dev_locked_split:按 ST 把样本分 DEV/LOCKED(ST 不跨层,unknown-ST 全归 dev)。
  2. dev 上 ST 分组 5 折 CV,每折训一次 ML(RF),从同一 ML 概率派生 5 个候选:
       rule / ml_aligned / ml_budget / fusion_aligned / fusion_budget
     (fusion=rule-first:rule 判 R 直接 R,否则 ML;budget=阈值在 train 上调到 ME≈ME_budget)。
  3. select_candidate(预注册):dev per-ST VME 最小,约束 ME<ME_budget,并列取 ME 更低。
  4. locked:用**全 dev** 重训 ML + 在 dev 定阈值,选中候选**只在 locked 上跑一次** → per-ST VME
     vs 规则 + 置换检验 → 判定 strong/practical/fail。

红线:locked 只跑一次;所有选择只看 dev;VME 优先、ME 预算 0.10;结果诚实落 reports/antibacterial/mdr_gnb/g2r_locked/。
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np

from ..evaluators.ast_metrics import compute_ast_metrics
from ..evaluators.lineage_split import make_lineage_splits
from ..evaluators.significance import align_st_vme, paired_permutation_test, st_level_vme
from ..predictors.features import FeatureSpec, build_feature_matrix
from ..predictors.genotype_to_sir import GenotypeToSIR
from ..predictors.rule_baseline import RuleBaselineSIR

_BIN = {"S": 0, "I": 0, "R": 1, "SUSCEPTIBLE": 0, "INTERMEDIATE": 0, "RESISTANT": 1}
ME_BUDGET = 0.10                       # 预注册:ME 绝对预算(VME 优先,ME 放宽到此)
CANDIDATES = ("rule", "ml_aligned", "ml_budget", "fusion_aligned", "fusion_budget")


def _y(rws):
    return np.array([_BIN.get(str(r.get("resistant_phenotype", "")).strip().upper(), -1) for r in rws], dtype=int)


def _rule_pred(rule, drug, rws):
    return np.array([1 if rule.predict_one_genotype(drug, r.get("ncbi_amr_genotypes", "")) == "R" else 0
                     for r in rws], dtype=int)


def _me(y_true, y_pred):
    s = y_true == 0
    return float((y_pred[s] == 1).mean()) if s.any() else 0.0


def _threshold_for_me(p_tr, y_tr, target_me):
    ths = np.linspace(0.01, 0.99, 99)
    me = np.array([_me(y_tr, (p_tr >= t).astype(int)) for t in ths])
    return float(ths[int(np.argmin(np.abs(me - target_me)))])


def st_dev_locked_split(ids, st_map, *, locked_frac=0.25, seed=0):
    """按 ST 分 DEV/LOCKED(ST 不跨层)。unknown-ST 全归 dev(不能安全分组进 locked)。"""
    st_to_ids = defaultdict(list)
    unknown = []
    for i in ids:
        st = st_map.get(i, "unknown")
        (unknown if st == "unknown" else st_to_ids[st]).append(i)
    sts = sorted(st_to_ids)
    rng = np.random.RandomState(seed)
    perm = rng.permutation(len(sts))
    n_lock = int(round(len(sts) * locked_frac))
    lock_sts = {sts[j] for j in perm[:n_lock]}
    dev_ids, lock_ids = [], []
    for st, grp in st_to_ids.items():
        (lock_ids if st in lock_sts else dev_ids).extend(grp)
    dev_ids.extend(unknown)
    return dev_ids, lock_ids


def _candidate_preds(p_te, rule_te, *, t_aligned, t_budget):
    """从 ML 概率 + 规则预测派生 5 候选的 test 预测(阈值均已在 train 上定好)。"""
    ml_a = (p_te >= t_aligned).astype(int)
    ml_b = (p_te >= t_budget).astype(int)
    return {
        "rule": rule_te,
        "ml_aligned": ml_a,
        "ml_budget": ml_b,
        "fusion_aligned": np.where(rule_te == 1, 1, ml_a),
        "fusion_budget": np.where(rule_te == 1, 1, ml_b),
    }


def _fit_fold(tr, te, st_map, rule, drug, seed, model):
    fm = build_feature_matrix(tr, st_map)
    Xte = FeatureSpec.transform(fm.spec, te)
    ml = GenotypeToSIR(random_state=seed, model=model).fit(fm.X, fm.y_sir)
    p_tr, p_te = ml.predict_proba_r(fm.X), ml.predict_proba_r(Xte)
    rule_tr, rule_te = _rule_pred(rule, drug, tr), _rule_pred(rule, drug, te)
    t_aligned = _threshold_for_me(p_tr, fm.y_sir, _me(fm.y_sir, rule_tr))   # 对齐规则 ME
    t_budget = _threshold_for_me(p_tr, fm.y_sir, ME_BUDGET)                 # 顶到 ME 预算(压 VME)
    return p_te, rule_te, t_aligned, t_budget


def _st_of(rws, st_map):
    return np.array([st_map.get((r.get("genome_id") or "").strip(), "unknown") for r in rws])


def dev_select(rows, st_map, rule, drug, *, seed=0, model="rf"):
    """dev ST 分组 5 折 CV,算 5 候选 per-ST VME/ME,按预注册规则选。返回 (best, table)。"""
    id2 = {(r.get("genome_id") or "").strip(): r for r in rows}
    ids = list(id2)
    specs = make_lineage_splits(ids, st_map, n_splits=5)
    oof = {c: [] for c in CANDIDATES}
    oof_y, oof_st = [], []
    for s in specs:
        tr = [id2[g] for g in s.train_ids]
        te = [id2[g] for g in s.test_ids]
        p_te, rule_te, t_a, t_b = _fit_fold(tr, te, st_map, rule, drug, seed, model)
        preds = _candidate_preds(p_te, rule_te, t_aligned=t_a, t_budget=t_b)
        for c in CANDIDATES:
            oof[c].append(preds[c])
        oof_y.append(_y(te)); oof_st.append(_st_of(te, st_map))
    y = np.concatenate(oof_y); st = np.concatenate(oof_st)
    table = {}
    for c in CANDIDATES:
        pred = np.concatenate(oof[c])
        m = compute_ast_metrics(y, pred, st)
        vme_st = st_level_vme(st, y, pred)
        table[c] = {"per_st_vme": float(np.mean(list(vme_st.values()))) if vme_st else float("nan"),
                    "me": m["me"], "vme_global": m["vme"]}
    # 预注册选择:ME<预算 的候选里 per-ST VME 最小,并列取 ME 更低
    eligible = [(c, table[c]) for c in CANDIDATES if table[c]["me"] < ME_BUDGET]
    if not eligible:                       # 全超预算 → 退回规则(最安全,practical)
        best = "rule"
    else:
        best = min(eligible, key=lambda kv: (kv[1]["per_st_vme"], kv[1]["me"]))[0]
    return best, table


def locked_verdict(dev_rows, lock_rows, st_map, rule, drug, best, *, seed=0, model="rf", n_perm=10000):
    """locked 只跑一次:全 dev 重训 + dev 定阈值,选中候选在 locked 上评 per-ST VME vs 规则。"""
    p_te, rule_te, t_a, t_b = _fit_fold(dev_rows, lock_rows, st_map, rule, drug, seed, model)
    preds = _candidate_preds(p_te, rule_te, t_aligned=t_a, t_budget=t_b)
    pred = preds[best]
    y = _y(lock_rows); st = _st_of(lock_rows, st_map)
    v_best = st_level_vme(st, y, pred); v_rule = st_level_vme(st, y, rule_te)
    keys, mm, rr = align_st_vme(v_best, v_rule)
    if len(keys) >= 1:
        perm = paired_permutation_test(mm, rr, keys, n_perm=n_perm, seed=seed)
        effect, pval = perm["mean_diff"], perm["p_value"]
    else:
        effect, pval = float("nan"), float("nan")
    m_best = compute_ast_metrics(y, pred, st); m_rule = compute_ast_metrics(y, rule_te, st)
    dv = float(mm.mean() - rr.mean()) if len(keys) else float("nan")
    if len(keys) and dv < 0 and pval < 0.05 and m_best["me"] < ME_BUDGET:
        verdict = "G2R-strong-pass"
    elif len(keys) and dv <= 0.001 and m_best["me"] < ME_BUDGET:
        verdict = "G2R-practical-pass"
    else:
        verdict = "G2R-fail"
    return {
        "best_candidate": best, "verdict": verdict, "n_locked": len(lock_rows), "n_st_with_R": len(keys),
        "per_st_vme_best": float(mm.mean()) if len(keys) else float("nan"),
        "per_st_vme_rule": float(rr.mean()) if len(keys) else float("nan"),
        "delta_vme": dv, "p_value": pval,
        "me_best": m_best["me"], "me_rule": m_rule["me"], "vme_global_best": m_best["vme"],
    }
