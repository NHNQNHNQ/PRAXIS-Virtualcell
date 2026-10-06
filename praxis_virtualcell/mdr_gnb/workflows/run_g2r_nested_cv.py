"""G2R 嵌套 CV(方法学打磨):运行点选择与显著性检验彻底分离,消除同集选阈乐观偏差。

外层 ST 分组 K 折(每折=locked);对每个外折:
  内层在 **outer_train** 上做 ST 分组 CV OOF → 按预注册规则选 t*(min per-ST VME s.t. ME≤规则ME+MARGIN),
  **绝不看 outer_test**;用全 outer_train 重训 ML → 以内层选的 t* 在 outer_test 上出 rule-first 融合预测。
聚合全外折 OOF → per-ST VME(融合)vs 规则 + 全 R-ST 配对置换。

红线:t* 只从 outer_train 定;融合=rule-first(VME≤规则兜底);ME 判据=不显著劣于规则(≤规则ME+MARGIN)。
"""
from __future__ import annotations

import numpy as np

from ..evaluators.lineage_split import make_lineage_splits
from ..evaluators.significance import align_st_vme, paired_permutation_test, st_level_vme
from ..predictors.genotype_to_sir import GenotypeToSIR
from ..predictors.features import parse_genotypes
from .run_g2r_lever_a import build_X, fit_vocab
from .run_g2r_locked import _me, _rule_pred, _st_of, _y

ME_MARGIN = 0.05        # 预注册:ME 不显著劣于规则 = ≤ 规则ME + MARGIN
_T_GRID = np.linspace(0.02, 0.98, 49)


def select_tstar(p, ru, y, st, *, rule_me, margin=ME_MARGIN, grid=_T_GRID, cc_map=None):
    """纯选择:在 ME≤规则ME+margin 的 t* 里选 per-单元 VME 最小(rule-first 融合)。
    无合格 → 退 0.98(近规则,最保守 ME)。返回 (t_star, per_unit_vme, me)。

    cc_map=None(默认)→ 选择判据按精确 ST 聚合(旧行为)。传入 cc_map → 按克隆复合体
    聚合:与最终评估同单元,避免"选点用 ST、评估用 CC"的口径错配。"""
    cap = rule_me + margin
    best = None
    for t in grid:
        fu = np.where(ru == 1, 1, (p >= t).astype(int))
        me = _me(y, fu)
        if me <= cap:
            per = st_level_vme(st, y, fu, cc_map=cc_map)
            pv = float(np.mean(list(per.values()))) if per else float("inf")
            if best is None or pv < best[1]:
                best = (float(t), pv, me)
    return best if best is not None else (0.98, float("nan"), float("nan"))


def _oof_predict(rows, st_map, rule, drug, featurizer, seed, n_splits=5, return_ids=False,
                 cc_map=None):
    """rows 上 ST/克隆复合体分组 CV OOF:返回 (p, rule_pred, y, st)。

    return_ids=True 时额外同序返回 (ids, fold):每 isolate 的 genome_id 与其所属 OOF 折索引。
    默认(False)返回值与签名行为逐字不变——sweep_combo/nested_cv_verdict 的 4 元组解包零改动。
    此函数是"证据面 OOF"的唯一真源:S1.1 的 per-isolate 导出经 return_ids 复用它,禁止另抄折循环。

    cc_map=None(默认)→ 分组按精确 ST(旧行为,逐字不变)。传入 cc_map(ST→CC)→ 按
    克隆复合体分组切折,堵住把一个近缘克隆群切成多组的跨折泄漏。
    """
    id2 = {(r.get("genome_id") or "").strip(): r for r in rows}
    ids = list(id2)
    specs = make_lineage_splits(ids, st_map, n_splits=n_splits, cc_map=cc_map)
    P, RU, Y, ST, IDS, FOLD = [], [], [], [], [], []
    for fold_idx, s in enumerate(specs):
        tr = [id2[g] for g in s.train_ids]; te = [id2[g] for g in s.test_ids]
        vocab = fit_vocab(tr, featurizer)
        ml = GenotypeToSIR(random_state=seed, model="rf").fit(build_X(tr, vocab, featurizer), _y(tr))
        P.append(ml.predict_proba_r(build_X(te, vocab, featurizer)))
        RU.append(_rule_pred(rule, drug, te)); Y.append(_y(te)); ST.append(_st_of(te, st_map))
        IDS.append(np.array([(r.get("genome_id") or "").strip() for r in te], dtype=object))
        FOLD.append(np.full(len(te), fold_idx, dtype=int))
    p, ru, y, st = np.concatenate(P), np.concatenate(RU), np.concatenate(Y), np.concatenate(ST)
    if return_ids:
        return p, ru, y, st, np.concatenate(IDS), np.concatenate(FOLD)
    return p, ru, y, st


def nested_cv_verdict(rows, st_map, rule, drug, *, featurizer=parse_genotypes, seed=0,
                      n_outer=5, n_inner=5, n_perm=10000, cc_map=None):
    """嵌套 CV 终判:内层(outer_train)选 t*,外层(outer_test)评,聚合全 R-单元 置换。

    cc_map=None(默认)→ 分组/选点/聚合全按精确 ST(旧行为,逐字不变)。传入 cc_map →
    外层切折、内层选点、外层评估全按克隆复合体单元(同时堵切分泄漏与聚合伪重复)。"""
    id2 = {(r.get("genome_id") or "").strip(): r for r in rows}
    ids = list(id2)
    outer = make_lineage_splits(ids, st_map, n_splits=n_outer, cc_map=cc_map)
    OY, OST, OFU, ORU, tstars = [], [], [], [], []
    for s in outer:
        otr = [id2[g] for g in s.train_ids]; ote = [id2[g] for g in s.test_ids]
        # 内层:只在 outer_train 上选 t*
        pi, rui, yi, sti = _oof_predict(otr, st_map, rule, drug, featurizer, seed, n_inner,
                                        cc_map=cc_map)
        t_star, _, _ = select_tstar(pi, rui, yi, sti, rule_me=_me(yi, rui), cc_map=cc_map)
        tstars.append(round(t_star, 3))
        # 用全 outer_train 重训,以内层 t* 评 outer_test
        vocab = fit_vocab(otr, featurizer)
        ml = GenotypeToSIR(random_state=seed, model="rf").fit(build_X(otr, vocab, featurizer), _y(otr))
        p_te = ml.predict_proba_r(build_X(ote, vocab, featurizer))
        rule_te = _rule_pred(rule, drug, ote)
        fu = np.where(rule_te == 1, 1, (p_te >= t_star).astype(int))
        OY.append(_y(ote)); OST.append(_st_of(ote, st_map)); OFU.append(fu); ORU.append(rule_te)
    y = np.concatenate(OY); st = np.concatenate(OST); fu = np.concatenate(OFU); ru = np.concatenate(ORU)
    vf, vr = st_level_vme(st, y, fu, cc_map=cc_map), st_level_vme(st, y, ru, cc_map=cc_map)
    keys, mm, rr = align_st_vme(vf, vr)
    perm = paired_permutation_test(mm, rr, keys, n_perm=n_perm, seed=seed) if len(keys) else {"p_value": float("nan")}
    dv = float(mm.mean() - rr.mean()) if len(keys) else float("nan")
    me_fu, me_ru = _me(y, fu), _me(y, ru)
    if len(keys) and dv < 0 and perm["p_value"] < 0.05 and me_fu <= me_ru + ME_MARGIN:
        verdict = "G2R-strong-pass"
    elif len(keys) and dv <= 0.001 and me_fu <= me_ru + ME_MARGIN:
        verdict = "G2R-practical-pass"
    else:
        verdict = "G2R-fail"
    return {"verdict": verdict, "n_st_R": len(keys), "tstars_per_fold": tstars,
            "per_st_vme_fusion": float(mm.mean()) if len(keys) else float("nan"),
            "per_st_vme_rule": float(rr.mean()) if len(keys) else float("nan"),
            "delta_vme": dv, "p_value": perm["p_value"], "me_fusion": me_fu, "me_rule": me_ru}
