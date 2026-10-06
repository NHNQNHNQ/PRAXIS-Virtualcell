"""G2R 证据面 sweep:对本地可评估的 EC+KP 组合(R-ST≥12)批量跑 OOF ST-CV 全功效评估
(机制特征 + rule-first 融合 + 预注册运行点),分层 strong/practical,产 registry 证据分层补丁。

说明:sweep 用 OOF ST-CV(单集选运行点,轻微乐观);锚点已用嵌套 CV 确认偏差<0.01。
rule-first 融合保证 per-ST VME≤规则,故最差是 practical(不劣于规则),strong=显著优于规则。
PA/AB/SE 本地无评估数据(phenotype/ST 缺)→ 不在本 sweep,需 53 数据管线(见 runbook)。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import numpy as np

from ..evaluators.significance import align_st_vme, paired_permutation_test, st_level_vme
from ..predictors.mechanism_features import augmented_features
from ..predictors.rule_baseline import RuleBaselineSIR
from .build_data_foundation import _modelable_ids, load_inputs_from_disk
from .run_g2r_locked import _me, _rule_pred, _st_of, _y
from .run_g2r_nested_cv import ME_MARGIN, _oof_predict, select_tstar

DB = "2024-01-frozen"
DATA = Path("data/mdr_gnb")
MODEL_SPECIES = ("escherichia_coli", "klebsiella_pneumoniae")   # 本地有评估数据的物种
MIN_R_ST, MIN_N = 12, 50


def _trained_drugs(sp: str) -> list[str]:
    m = DATA / "models" / sp / "MANIFEST.txt"
    out = []
    if m.exists():
        for line in m.read_text().splitlines():
            g = re.match(r"OK (.+?): n=", line.strip())
            if g:
                out.append(g.group(1))
    return out


def _auc_ece(y, p, bins: int = 10):
    """OOF ROC-AUC(R 为正类)+ 期望校准误差 ECE(10 分箱)。单类 → auc=None。"""
    from sklearn.metrics import roc_auc_score
    y = np.asarray(y); p = np.asarray(p, dtype=float)
    auc = round(float(roc_auc_score(y, p)), 4) if len(set(y.tolist())) > 1 else None
    edges = np.linspace(0.0, 1.0, bins + 1)
    n, ece = len(y), 0.0
    for i in range(bins):
        hi = p <= edges[i + 1] if i == bins - 1 else p < edges[i + 1]
        m = (p >= edges[i]) & hi
        if m.sum():
            ece += m.sum() / n * abs(float(p[m].mean()) - float(y[m].mean()))
    return auc, round(ece, 4)


def _combo_rows(amr, st_map, drug):
    mids = set(_modelable_ids(amr, drug))
    seen, rows = set(), []
    for r in amr:
        if r.get("antibiotic") == drug:
            g = (r.get("genome_id") or "").strip()
            if g in mids and g not in seen:
                seen.add(g); rows.append(r)
    return rows


def sweep_combo(sp: str, drug: str, seed: int = 0, cc_map: dict | None = None) -> dict:
    """cc_map=None(默认)→ 全链按精确 ST(旧行为,逐字不变)。传入 cc_map(ST→CC)→
    OOF 切折、运行点选择、per-单元 VME 聚合全按克隆复合体单元:同时堵切分跨折泄漏
    与聚合伪重复(n_R_ST 变为独立 R-CC 数,置换检验分母不再虚高)。"""
    amr, st_map, _ = load_inputs_from_disk(sp, DATA)
    rows = _combo_rows(amr, st_map, drug)
    rule = RuleBaselineSIR(db_version=DB)
    p, ru, y, st = _oof_predict(rows, st_map, rule, drug, augmented_features, seed, cc_map=cc_map)
    auc, ece = _auc_ece(y, p)          # OOF 判别力 + 校准误差
    rule_me = _me(y, ru)
    t_star, _, _ = select_tstar(p, ru, y, st, rule_me=rule_me, cc_map=cc_map)
    fu = np.where(ru == 1, 1, (p >= t_star).astype(int))
    vf, vr = st_level_vme(st, y, fu, cc_map=cc_map), st_level_vme(st, y, ru, cc_map=cc_map)
    keys, mm, rr = align_st_vme(vf, vr)
    perm = paired_permutation_test(mm, rr, keys, n_perm=10000, seed=seed) if len(keys) else {"p_value": float("nan")}
    dv = float(mm.mean() - rr.mean()) if len(keys) else float("nan")
    me_fu = _me(y, fu)
    if len(keys) and dv < 0 and perm["p_value"] < 0.05 and me_fu <= rule_me + ME_MARGIN:
        tier = "strong"
    else:
        tier = "practical"          # rule-first 保证 VME≤规则 → 最差不劣于规则
    return {"species": sp, "drug": drug, "n": len(rows), "n_R_ST": len(keys),
            "per_st_vme_fusion": round(float(mm.mean()), 4) if len(keys) else None,
            "per_st_vme_rule": round(float(rr.mean()), 4) if len(keys) else None,
            "delta_vme": round(dv, 4) if len(keys) else None,
            "p_value": round(float(perm["p_value"]), 4), "me_fusion": round(me_fu, 4),
            "me_rule": round(rule_me, 4), "t_star": round(float(t_star), 3),
            "auc_R": auc, "calibration_ece": ece, "tier": tier}


def feasible_combos(cc_maps: dict[str, dict] | None = None) -> list[tuple[str, str]]:
    """可行性判据的独立观测数。

    cc_maps=None(默认)→ 按 R-ST 数(旧行为,逐字不变)。传入 cc_maps(species→{ST:CC})
    → 按 **R-CC** 数:接 CC 后独立观测单元是 CC 不是 ST,否则会把"CC 数不够"的组合
    误判可行(把一个克隆复合体的多个 ST 当成多个独立观测,虚高分母)。
    """
    out = []
    for sp in MODEL_SPECIES:
        amr, st_map, _ = load_inputs_from_disk(sp, DATA)
        cc_map = cc_maps.get(sp) if cc_maps else None
        for dr in _trained_drugs(sp):
            rows = _combo_rows(amr, st_map, dr)
            R = [r for r in rows if str(r.get("resistant_phenotype", "")).strip().upper() in ("R", "RESISTANT")]
            units = set()
            for r in R:
                st = st_map.get((r.get("genome_id") or "").strip(), "unknown")
                units.add(cc_map.get(st, st) if cc_map else st)
            n_rst = len(units - {"unknown"})
            if n_rst >= MIN_R_ST and len(rows) >= MIN_N:
                out.append((sp, dr))
    return out


def _worker(args):
    # 兼容 2 元组(sp, dr,旧行为)与 3 元组(sp, dr, cc_map,接 CC 后)。
    sp, dr, *rest = args
    cc_map = rest[0] if rest else None
    try:
        return sweep_combo(sp, dr, cc_map=cc_map)
    except Exception as e:  # noqa: BLE001
        return {"species": sp, "drug": dr, "error": str(e), "tier": "error"}


if __name__ == "__main__":
    import json
    from concurrent.futures import ProcessPoolExecutor

    from ..evaluators.clonal_complex import load_cc_map
    os.chdir(Path(__file__).resolve().parents[3])
    # 源头 load 克隆复合体映射(本地无 mlst_raw.tsv → load_cc_map 返回 {} → 全链回退 ST,
    # 逐字旧行为;.53 有等位谱 → 得真实 ST→CC → CC 分组闭合两病灶)。
    cc_maps = {sp: load_cc_map(sp, DATA) for sp in MODEL_SPECIES}
    combos = feasible_combos(cc_maps=cc_maps)
    tasks = [(sp, dr, cc_maps.get(sp)) for sp, dr in combos]
    print(f"可评估组合 {len(combos)}(EC+KP,R-单元≥{MIN_R_ST});多进程跑…", flush=True)
    results = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for i, d in enumerate(ex.map(_worker, tasks), 1):
            results.append(d)
            print(f"  [{i}/{len(combos)}] {d['species'][:20]:20} × {d.get('drug',''):16} "
                  f"tier={d.get('tier'):9} ΔVME={d.get('delta_vme')} p={d.get('p_value')} R-ST={d.get('n_R_ST')}", flush=True)
    out = Path("reports/antibacterial/mdr_gnb/g2r_locked/evidence_sweep.json")
    json.dump(results, open(out, "w"), indent=1, default=float)
    strong = [r for r in results if r.get("tier") == "strong"]
    print(f"\nstrong={len(strong)}  practical={sum(1 for r in results if r.get('tier')=='practical')}  "
          f"error={sum(1 for r in results if r.get('tier')=='error')}  → {out}")
