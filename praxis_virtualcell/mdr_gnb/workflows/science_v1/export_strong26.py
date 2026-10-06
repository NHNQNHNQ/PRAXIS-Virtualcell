"""S1.1:把 26 strong 组合做成"可复现科学资产"——导出 per-fold / per-isolate 预测 + 统计检验。

本任务只做**本地 EC/KP 13 组合**(PA/AB/SA/SE 在 53,是后续 S1.2)。

科学口径(与冻结 v0.9 证据面一致,严格复现):
  证据面 sweep 的单遍 OOF ST-CV 就是冻结面 VME 的来源。这里给它加装 per-isolate + fold 记录,
  复现同样的数值(seed=0、RF、机制特征 augmented_features、GroupKFold-by-ST)。

  逐组合流程:
    1. load_inputs_from_disk → _combo_rows 拿该组合可评估 isolate 行。
    2. ST 分组 5 折 OOF:逐折训 RF → 对 test 出 ml_prob_r + rule_pred,保留 genome_id + fold。
       (make_lineage_splits 剔除 unknown-ST,故 OOF 覆盖=全部已知 ST isolate,无弃权 → coverage=1.0)
    3. 汇总全 OOF → select_tstar 选 t*(ME≤规则ME+0.05 下 per-ST VME 最小)→ rule-first 融合。
       安全保证:rule_pred=R 的 isolate 强制 fused_sir=R(rule-first,VME≤规则兜底)。
    4. 统计:per-ST VME(融合 vs 规则)+ 配对置换(10000)+ ΔVME bootstrap CI(2000)。

一键复现:
    .venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.export_strong26 \
        --species escherichia_coli,klebsiella_pneumoniae

产物(reports/antibacterial/mdr_gnb/science_v1/strong_26/):
    strong_26_summary.csv / strong_26_per_fold_metrics.csv
    strong_26_per_isolate_predictions.parquet / strong_26_stat_tests.json / strong_26_reproduction.md
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd

from praxis_virtualcell.mdr_gnb.evaluators.significance import (
    align_st_vme,
    bootstrap_effect_ci,
    paired_permutation_test,
    st_level_vme,
)
from praxis_virtualcell.mdr_gnb.predictors.mechanism_features import augmented_features
from praxis_virtualcell.mdr_gnb.predictors.rule_baseline import RuleBaselineSIR
from praxis_virtualcell.mdr_gnb.workflows.build_data_foundation import load_inputs_from_disk
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_evidence_sweep import _auc_ece, _combo_rows
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_locked import _me
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_nested_cv import ME_MARGIN, _oof_predict, select_tstar
from praxis_virtualcell.mdr_gnb.workflows.science_v1._io import dump_json, write_csv

# 仓库根(本文件在 praxis_virtualcell/mdr_gnb/workflows/science_v1/)
_ROOT = Path(__file__).resolve().parents[4]
_DATA = _ROOT / "data" / "mdr_gnb"
_DETAIL_CSV = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v0.9_freeze" / "04_strong_26_detail.csv"
_OUT = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v1" / "strong_26"
DB = "2024-01-frozen"
SEED = 0
N_PERM = 10000
N_BOOT = 2000

# 本地有评估数据(phenotype/ST 齐)的物种;其余(PA/AB/SA/SE)在 53
LOCAL_SPECIES = ("escherichia_coli", "klebsiella_pneumoniae")
# 全 5 物种(53 数据):--all 用,过滤冻结明细即跑全 26 strong
ALL_SPECIES = (
    "escherichia_coli",
    "klebsiella_pneumoniae",
    "pseudomonas_aeruginosa",
    "acinetobacter_baumannii",
    "salmonella_enterica",
)

_SUMMARY_COLS = [
    "species", "drug", "n", "n_R_ST", "t_star",
    "per_st_vme_fusion", "per_st_vme_rule", "delta_vme", "p_value",
    "me_fusion", "me_rule", "auc_R", "ece", "coverage",
]
_FOLD_COLS = ["species", "drug", "fold", "n", "vme_fusion", "me_fusion"]
_ISO_COLS = ["species", "drug", "strain_id", "st", "y_true", "rule_pred", "ml_prob_r", "fused_sir", "fold"]


# ---------------------------------------------------------------- strong 清单
def load_strong_combos(species_filter: list[str] | None) -> list[tuple[str, str]]:
    """读冻结的 26 strong 明细,过滤到指定物种(默认本地 EC/KP)。别硬编码药名。"""
    combos: list[tuple[str, str]] = []
    with open(_DETAIL_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("tier") != "strong":
                continue
            sp = r["species"]
            if species_filter is not None and sp not in species_filter:
                continue
            combos.append((sp, r["drug"]))
    return combos


# ---------------------------------------------------------------- 单组合 OOF + 统计
def export_combo(sp: str, drug: str) -> dict:
    """跑单组合 OOF ST-CV,记录 per-isolate/per-fold,复现冻结面 VME + 统计。

    返回 dict:{per_iso, per_fold, summary, stat}(供上层汇总落盘)。
    """
    amr, st_map, _ = load_inputs_from_disk(sp, _DATA)
    rows = _combo_rows(amr, st_map, drug)                 # 该组合可评估 isolate 行
    rule = RuleBaselineSIR(db_version=DB)

    # 唯一真源:直接复用证据面 OOF(return_ids 拿 per-isolate 的 genome_id + fold),
    # 不复制折循环 → 将来 _oof_predict 改 featurizer/split,本导出自动跟随、绝不静默停止复现。
    p, ru, y, st, iso_ids, iso_fold = _oof_predict(
        rows, st_map, rule, drug, augmented_features, SEED, return_ids=True
    )
    rule_me = _me(y, ru)
    t_star, _, _ = select_tstar(p, ru, y, st, rule_me=rule_me)
    fu = np.where(ru == 1, 1, (p >= t_star).astype(int))  # rule=R 强制 R,否则 ML 阈值

    # per-isolate 记录:全部字段派生自这一次 _oof_predict(顺序与聚合数组逐位对齐)
    per_iso: list[dict] = []
    for i in range(len(iso_ids)):
        per_iso.append({
            "species": sp, "drug": drug,
            "strain_id": str(iso_ids[i]),
            "st": str(st[i]),
            "y_true": int(y[i]),
            "rule_pred": "R" if ru[i] == 1 else "S",
            "ml_prob_r": float(p[i]),
            "fused_sir": "R" if fu[i] == 1 else "S",      # ← 安全保证:rule=R 必 fused=R
            "fold": int(iso_fold[i]),
        })

    # 统计(照 sweep_combo):per-ST VME 融合 vs 规则 + 配对置换 + ΔVME bootstrap CI
    vf, vr = st_level_vme(st, y, fu), st_level_vme(st, y, ru)
    keys, mm, rr = align_st_vme(vf, vr)
    if len(keys):
        perm = paired_permutation_test(mm, rr, keys, n_perm=N_PERM, seed=SEED)
        p_value = float(perm["p_value"])
        delta_vme = float(mm.mean() - rr.mean())
        per_st_vme_fusion = float(mm.mean())
        per_st_vme_rule = float(rr.mean())
        ci_lo, ci_hi = bootstrap_effect_ci(mm - rr, n_boot=N_BOOT, seed=SEED)
    else:
        # R-ST 太少 → 统计 nan,如实记录(strong 13 不会触发,防御性保留)
        p_value = delta_vme = per_st_vme_fusion = per_st_vme_rule = float("nan")
        ci_lo = ci_hi = float("nan")

    me_fusion = _me(y, fu)
    auc, ece = _auc_ece(y, p)

    # per-fold 指标:各折 test 子集 pooled VME/ME(VME=该折真R中fused==S比例;ME=该折真S中fused==R比例)
    per_fold: list[dict] = []
    yi = y; fui = fu; foldi = np.array([d["fold"] for d in per_iso])
    for f in sorted(set(foldi.tolist())):
        m = foldi == f
        yf, ff = yi[m], fui[m]
        rmask, smask = (yf == 1), (yf == 0)
        vme_f = float((ff[rmask] == 0).mean()) if rmask.any() else float("nan")
        me_f = float((ff[smask] == 1).mean()) if smask.any() else 0.0
        per_fold.append({
            "species": sp, "drug": drug, "fold": int(f), "n": int(m.sum()),
            "vme_fusion": round(vme_f, 4) if vme_f == vme_f else "",   # nan→留空
            "me_fusion": round(me_f, 4),
        })

    summary = {
        "species": sp, "drug": drug, "n": len(rows), "n_R_ST": len(keys),
        "t_star": round(float(t_star), 3),
        "per_st_vme_fusion": _r4(per_st_vme_fusion),
        "per_st_vme_rule": _r4(per_st_vme_rule),
        "delta_vme": _r4(delta_vme),
        "p_value": _r4(p_value),
        "me_fusion": round(me_fusion, 4),
        "me_rule": round(rule_me, 4),
        "auc_R": auc if auc is not None else "",
        "ece": ece,
        # coverage=进折(已知 ST)isolate 的非弃权率,不是对 n 的覆盖:本流程无弃权,进折者全有预测 → 1.0。
        # 注意 n 含被 make_lineage_splits 剔除的 unknown-ST 行,故 per-isolate 行数 < n 属正常(非缺口)。
        "coverage": 1.0,
    }
    stat = {
        "p_value": p_value,
        "delta_vme": delta_vme,
        "delta_vme_ci": [_r4(ci_lo), _r4(ci_hi)],
        "me_margin_ok": bool(me_fusion <= rule_me + ME_MARGIN),
    }
    return {"per_iso": per_iso, "per_fold": per_fold, "summary": summary, "stat": stat}


def _r4(x: float):
    """nan 留空(CSV/JSON 里显式空),否则 4 位小数。"""
    return round(float(x), 4) if x == x else ""


# ---------------------------------------------------------------- 复现说明
def _write_reproduction(summaries: list[dict], stats: dict, species_filter) -> None:
    sp_arg = ",".join(species_filter) if species_filter else "escherichia_coli,klebsiella_pneumoniae"
    lines: list[str] = []
    lines.append("# S1.1:26 strong 组合可复现证据(本地 EC/KP 13 组合)\n")
    lines.append(
        "把冻结 v0.9 证据面里 rule-first 融合**显著优于** AMRFinderPlus 规则法的 strong 组合,\n"
        "从结果表变成可追溯到每个 isolate 预测、可一键复现的证据。\n"
    )
    lines.append("## 一键复现\n")
    lines.append("```bash")
    lines.append(
        ".venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.export_strong26 \\\n"
        f"    --species {sp_arg}"
    )
    lines.append("```")
    lines.append(
        f"\n确定性:seed={SEED}(RF + GroupKFold-by-ST);置换 {N_PERM} 次固定 seed;"
        f"ΔVME bootstrap {N_BOOT} 次固定 seed。特征=机制增强(augmented_features)。"
        "重跑得到一致数值。\n"
    )
    lines.append("## 汇总\n")
    lines.append("| species | drug | n | R-ST | t\\* | 融合VME | 规则VME | ΔVME | p | ME融合 | ME规则 | AUC | 显著 |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:--:|")
    for s in summaries:
        sig = "✅" if (isinstance(s["p_value"], float) and s["p_value"] < 0.05) else "—"
        lines.append(
            f"| {s['species']} | {s['drug']} | {s['n']} | {s['n_R_ST']} | {s['t_star']} | "
            f"{s['per_st_vme_fusion']} | {s['per_st_vme_rule']} | {s['delta_vme']} | {s['p_value']} | "
            f"{s['me_fusion']} | {s['me_rule']} | {s['auc_R']} | {sig} |"
        )
    lines.append("\n## 每组合 6 问\n")
    for s in summaries:
        key = f"{s['species']}::{s['drug']}"
        stt = stats[key]
        vf, vr = s["per_st_vme_fusion"], s["per_st_vme_rule"]
        dv = s["delta_vme"]
        rel = f"{abs(dv) / vr * 100:.0f}%" if (isinstance(vr, float) and vr > 0 and isinstance(dv, float)) else "—"
        ci = stt["delta_vme_ci"]
        lines.append(f"### {s['species']} × {s['drug']}\n")
        lines.append(
            f"1. **为什么比 AMRFinderPlus 安全**:融合 per-ST VME={vf} < 规则 per-ST VME={vr}"
            f"(VME=真耐药被误判为敏感的危险漏判;融合更少漏判 R)。\n"
            f"2. **VME 降多少**:ΔVME={dv}(相对降幅≈{rel}),bootstrap 95% CI=[{ci[0]}, {ci[1]}]"
            f"(CI 上界<0 → 稳健优于规则)。\n"
            f"3. **是否牺牲过多 ME**:ME融合={s['me_fusion']} vs ME规则={s['me_rule']}"
            f"(判据 ≤规则ME+{ME_MARGIN}:{'通过' if stt['me_margin_ok'] else '未过'});"
            f"rule-first 只在规则判 S 处用 ML,不放大误判。\n"
            f"4. **是否显著**:配对置换检验 p={s['p_value']}"
            f"({'显著' if (isinstance(s['p_value'], float) and s['p_value'] < 0.05) else '不显著'},单侧 model<rule)。\n"
            f"5. **ST 无泄漏**:GroupKFold 按 ST 分组,同一 ST(克隆群)绝不跨 train/test;"
            f"unknown-ST 剔出折;coverage={s['coverage']}(进折 isolate 全覆盖,无弃权)。\n"
            f"6. **如何复现**:上方一键命令;本组合 n={s['n']}、R-ST={s['n_R_ST']}、t\\*={s['t_star']};"
            f"per-isolate 预测见 strong_26_per_isolate_predictions.parquet。\n"
        )
    (_OUT / "strong_26_reproduction.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 驱动
def run(species_filter: list[str] | None) -> None:
    _OUT.mkdir(parents=True, exist_ok=True)
    combos = load_strong_combos(species_filter)
    print(f"strong 组合 {len(combos)}(过滤={species_filter or 'local EC/KP'});逐组合跑 OOF ST-CV…", flush=True)

    all_iso: list[dict] = []
    all_fold: list[dict] = []
    summaries: list[dict] = []
    stats: dict = {}
    for i, (sp, drug) in enumerate(combos, 1):
        res = export_combo(sp, drug)
        all_iso.extend(res["per_iso"])
        all_fold.extend(res["per_fold"])
        summaries.append(res["summary"])
        stats[f"{sp}::{drug}"] = res["stat"]
        s = res["summary"]
        print(
            f"  [{i}/{len(combos)}] {sp[:20]:20} × {drug:18} "
            f"n={s['n']:5} R-ST={s['n_R_ST']:3} t*={s['t_star']} "
            f"融合VME={s['per_st_vme_fusion']} 规则VME={s['per_st_vme_rule']} "
            f"ΔVME={s['delta_vme']} p={s['p_value']}",
            flush=True,
        )

    # 落盘:CSV / parquet / JSON / MD
    write_csv(_OUT / "strong_26_summary.csv", _SUMMARY_COLS, summaries)
    write_csv(_OUT / "strong_26_per_fold_metrics.csv", _FOLD_COLS, all_fold)
    pd.DataFrame(all_iso, columns=_ISO_COLS).to_parquet(
        _OUT / "strong_26_per_isolate_predictions.parquet", index=False
    )
    dump_json(_OUT / "strong_26_stat_tests.json", stats)
    _write_reproduction(summaries, stats, species_filter)

    n_combo = len({(d["species"], d["drug"]) for d in all_iso})
    print(
        f"\n落盘 → {_OUT}\n"
        f"  组合={n_combo}  per-isolate={len(all_iso)}  per-fold={len(all_fold)}",
        flush=True,
    )


def _parse_species(args) -> list[str] | None:
    if args.all:
        # --all(53 全物种):过滤冻结明细即跑全 26 strong。仅 53 有 PA/AB/SA/SE 的
        # phenotype/ST,本地跑会在 load_inputs_from_disk 崩(预期)。
        return list(ALL_SPECIES)
    return [s.strip() for s in args.species.split(",") if s.strip()]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="S1.1 导出 26 strong 的 per-fold/per-isolate 证据(本地 EC/KP 13 组合)")
    ap.add_argument(
        "--species",
        default=",".join(LOCAL_SPECIES),
        help="逗号分隔物种(默认本地 EC/KP)",
    )
    ap.add_argument("--all", action="store_true", help="全 5 物种(53 数据):跑全 26 strong")
    args = ap.parse_args()
    run(_parse_species(args))
