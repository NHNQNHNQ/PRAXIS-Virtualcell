"""单 species×drug G2 评估 runner(NCBI-native,确定性)。

决策变更(2026-07-03)NCBI-only:计划 2.10 的 MIC 回归/torch/pandas/折点全不适用。
本 runner 串起:ST 分组 5 折 → 每折训 GenotypeToSIR(ML)+ 版本冻结 RuleBaselineSIR →
**操作点对齐**(ML 阈值在 train 上调到与规则法相同 ME,test 上应用,防 test 调阈泄漏)→
汇聚 OOF → compute_ast_metrics(全局)+ st_level_vme + paired_permutation_test + bootstrap_ci →
evaluate_combo_gate。纯函数吃 rows+st_map(可离线单测),CLI 从盘读。

**红队**:features 即 AMRFinderPlus 输出与规则法同源,ST 去泄漏后 ML 增量可能坍缩——如实归类。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ..evaluators.ast_metrics import compute_ast_metrics
from ..evaluators.combo_gate import GatePrereg, evaluate_combo_gate
from ..evaluators.lineage_split import make_lineage_splits
from ..evaluators.significance import (
    align_st_vme, bootstrap_effect_ci, paired_permutation_test, st_level_vme,
)
from ..predictors.features import FeatureSpec, build_feature_matrix
from ..predictors.genotype_to_sir import GenotypeToSIR
from ..predictors.rule_baseline import RuleBaselineSIR

_BIN = {"S": 0, "I": 0, "R": 1, "SUSCEPTIBLE": 0, "INTERMEDIATE": 0, "RESISTANT": 1}


def _y(rws):
    return np.array([_BIN.get(str(r.get("resistant_phenotype", "")).strip().upper(), -1) for r in rws], dtype=int)


def _rule_pred(rule: RuleBaselineSIR, drug: str, rws):
    return np.array([1 if rule.predict_one_genotype(drug, r.get("ncbi_amr_genotypes", "")) == "R" else 0
                     for r in rws], dtype=int)


def _me(y_true, y_pred):
    s = y_true == 0
    return float((y_pred[s] == 1).mean()) if s.any() else 0.0


def run_combo_eval(
    species_dir: str, drug: str, rows: list[dict], st_map: dict[str, str],
    *, prereg: GatePrereg, db_version: str, n_splits: int = 5, seed: int = 0,
    model: str = "logreg",
) -> dict:
    """单 species×drug G2 评估。rows 为该药去重后的有效 SIR 记录(每行含
    genome_id/ncbi_amr_genotypes/resistant_phenotype);返回 gate + 指标 + 显著性。
    """
    id2row = {(r.get("genome_id") or "").strip(): r for r in rows}
    ids = [(r.get("genome_id") or "").strip() for r in rows]
    n_strains = len(rows)
    rule = RuleBaselineSIR(db_version=db_version)

    specs = make_lineage_splits(ids, st_map, n_splits=n_splits)
    if not specs:
        # ST 组数不足以分折 → 无法做 ST 级检验
        gate = evaluate_combo_gate(
            species_dir, drug, n_strains=n_strains, n_st_with_R=0,
            vme_model=None, vme_rule=None, effect_size=None, p_value=None, prereg=prereg)
        return {"gate": gate, "n_strains": n_strains, "n_st_with_R": 0,
                "vme_model": float("nan"), "vme_rule": float("nan"),
                "me_model": float("nan"), "me_rule": float("nan"),
                "effect_size": None, "p_value": None}

    oof_st, oof_y, oof_ml, oof_rule = [], [], [], []
    for s in specs:
        tr = [id2row[g] for g in s.train_ids]
        te = [id2row[g] for g in s.test_ids]
        fm = build_feature_matrix(tr, st_map)
        ytr = fm.y_sir
        Xte = FeatureSpec.transform(fm.spec, te)
        yte = _y(te)
        stte = np.array([st_map.get((r.get("genome_id") or "").strip(), "unknown") for r in te])

        ml = GenotypeToSIR(random_state=seed, model=model).fit(fm.X, ytr)
        p_tr = ml.predict_proba_r(fm.X)
        p_te = ml.predict_proba_r(Xte)

        # 操作点对齐:在 train 上把 ML 阈值调到与规则法相同 ME
        target_me = _me(ytr, _rule_pred(rule, drug, tr))
        ths = np.linspace(0.01, 0.99, 99)
        me_tr = np.array([_me(ytr, (p_tr >= t).astype(int)) for t in ths])
        t_star = float(ths[int(np.argmin(np.abs(me_tr - target_me)))])

        oof_st.append(stte); oof_y.append(yte)
        oof_ml.append((p_te >= t_star).astype(int))
        oof_rule.append(_rule_pred(rule, drug, te))

    st = np.concatenate(oof_st); y = np.concatenate(oof_y)
    ml_pred = np.concatenate(oof_ml); ru_pred = np.concatenate(oof_rule)

    m_ml = compute_ast_metrics(y, ml_pred, st)
    m_ru = compute_ast_metrics(y, ru_pred, st)
    vme_ml_st = st_level_vme(st, y, ml_pred)
    vme_ru_st = st_level_vme(st, y, ru_pred)
    keys, mm, rr = align_st_vme(vme_ml_st, vme_ru_st)
    if len(keys) >= 1:
        perm = paired_permutation_test(mm, rr, keys, n_perm=10000, seed=seed)
        lo, hi = bootstrap_effect_ci(mm - rr, n_boot=10000, seed=seed)
        effect = perm["mean_diff"]
        pval = perm["p_value"]
    else:
        effect, pval, lo, hi = None, None, float("nan"), float("nan")

    gate = evaluate_combo_gate(
        species_dir, drug, n_strains=n_strains, n_st_with_R=len(keys),
        vme_model=round(float(mm.mean()), 4) if len(keys) else None,
        vme_rule=round(float(rr.mean()), 4) if len(keys) else None,
        effect_size=effect, p_value=pval, prereg=prereg)

    return {
        "gate": gate,
        "n_strains": n_strains,
        "n_st_with_R": len(keys),
        "vme_model": m_ml["vme"], "vme_rule": m_ru["vme"],
        "me_model": m_ml["me"], "me_rule": m_ru["me"],
        "per_st_vme_model": float(mm.mean()) if len(keys) else float("nan"),
        "per_st_vme_rule": float(rr.mean()) if len(keys) else float("nan"),
        "effect_size": effect, "p_value": pval, "ci": (lo, hi),
    }


def load_and_eval(
    species_dir: str, drug: str, data_root: Path, *, prereg: GatePrereg,
    db_version: str, n_splits: int = 5, seed: int = 0, model: str = "logreg",
) -> dict:
    """从盘读该 species×drug 的去重有效 SIR 记录 + st_map,跑 run_combo_eval。"""
    from .build_data_foundation import load_inputs_from_disk, _modelable_ids
    from ..predictors.features import parse_genotypes  # noqa: F401 (确保可导入)

    amr, st_map, _ = load_inputs_from_disk(species_dir, data_root)
    mids = set(_modelable_ids(amr, drug))
    seen, rows = set(), []
    for r in amr:
        if r.get("antibiotic") == drug:
            g = (r.get("genome_id") or "").strip()
            if g in mids and g not in seen:
                seen.add(g); rows.append(r)
    return run_combo_eval(species_dir, drug, rows, st_map,
                          prereg=prereg, db_version=db_version, n_splits=n_splits,
                          seed=seed, model=model)
