"""S4:高价值稀有组合定向补——聚焦 **colistin**(多黏菌素)high-risk demonstration。

科学背景与诚实定位(关键)
--------------------------------
colistin 是对抗泛耐药革兰氏阴性菌的「最后一线」药,临床极高价值。但:
  1. **规则表未收录 colistin**(已核实:RuleBaselineSIR 对 colistin 抛 KeyError)
     → colistin 是 **no_baseline**,**无规则基线可对照**。
  2. breakpoint 标准多变、表型测定噪声高、mcr 阴性耐药机制复杂。
所以 colistin 定位是 high-risk demonstration:诚实表征「能预测到什么程度」,
但因无规则基线,**不声称「优于规则」、不做规则对照/ΔVME、不硬求 strong-pass**。
这与项目诚实纪律一致。

方法(纯 ML OOF,不融合规则)
--------------------------------
不能用 _oof_predict / lever_a——它们内部调 _rule_pred,会对 colistin 抛 KeyError。
自己写纯 ML 的 ST 分组 OOF:
  - ST-grouped 5 折(make_lineage_splits,同一 ST 不跨 train/test);
  - 每折 RF(seed=0)训 augmented_features(build_X/fit_vocab,frozen-consistent);
  - OOF 概率 → 固定 0.5 阈值出预测(无规则可对齐 ME,故取自然阈);
  - 指标:per-ST VME(vme_ml)、ME(me_ml)、判别力 AUC_R、校准 ECE。
  - **无 ΔVME、无规则对照**(colistin 无规则基线)。

可行性(53 已核实 colistin R-ST)
--------------------------------
  KP×colistin: n=238 R=77 R-ST=26  → feasible(主案例)
  EC×colistin: n=541 R=16 R-ST=15  → feasible
  PA×colistin: n=144 R=14 R-ST=10  → underpowered(评估但 reliable=False)
  AB×colistin: n=303 R=24 R-ST= 8  → underpowered(评估但 reliable=False)
feasible/reliable 阈:R-ST≥12(MIN_R_ST)。

数据位点:colistin 表型/ST 只在 53。本地跑不出产物(load_inputs_from_disk 缺 colistin
表型即崩,预期)→ gate 本地先 FAIL;协调方在 53 跑完 rsync 回产物后 gate 转 PASS。

一键复现(在 53)
--------------------------------
    .venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.rare_combos

产物(reports/antibacterial/mdr_gnb/science_v1/rare_combos/)
    rare_combo_data_manifest.yaml / rare_combo_qc_report.md /
    rare_combo_metrics.csv / rare_combo_failure_modes.yaml / rare_combo_decision.md
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

from praxis_virtualcell.mdr_gnb.evaluators.significance import st_level_vme
from praxis_virtualcell.mdr_gnb.predictors.genotype_to_sir import GenotypeToSIR
from praxis_virtualcell.mdr_gnb.predictors.mechanism_features import augmented_features
from praxis_virtualcell.mdr_gnb.evaluators.lineage_split import make_lineage_splits
from praxis_virtualcell.mdr_gnb.workflows.build_data_foundation import load_inputs_from_disk
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_evidence_sweep import _auc_ece, _combo_rows
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_lever_a import build_X, fit_vocab
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_locked import _st_of, _y
from praxis_virtualcell.mdr_gnb.workflows.science_v1._io import write_csv

# 仓库根(本文件在 praxis_virtualcell/mdr_gnb/workflows/science_v1/)
_ROOT = Path(__file__).resolve().parents[4]
_DATA = _ROOT / "data" / "mdr_gnb"
_OUT = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v1" / "rare_combos"
SEED = 0
DRUG = "colistin"
MIN_R_ST = 12                       # feasible/reliable 阈值:R-ST≥12 才算够功效

# S4 聚焦 colistin 的 4 个物种组合(可行性已在 53 核实,见模块 docstring)
COLISTIN_SPECIES: list[str] = [
    "klebsiella_pneumoniae",        # R-ST=26 主案例
    "escherichia_coli",             # R-ST=15
    "pseudomonas_aeruginosa",       # R-ST=10 underpowered
    "acinetobacter_baumannii",      # R-ST= 8 underpowered
]

_METRIC_COLS = ["species", "drug", "n", "n_R", "n_R_ST",
                "vme_ml", "me_ml", "auc_R", "ece", "reliable"]


def _fmt(x) -> str:
    """None/nan → 空串;否则原样字符串(CSV 稳定)。"""
    if x is None or (isinstance(x, float) and x != x):
        return ""
    return str(x)


# ------------------------------------------------------------------ 核心:纯 ML OOF
def _eval_ml_only(rows: list[dict], st_map: dict[str, str], sp: str, drug: str) -> dict:
    """纯 ML 的 ST 分组 OOF(不融合规则)。接收 rows+st_map,便于合成自检(不碰磁盘)。

    返回 {species,drug,n,n_R,n_R_ST,vme_ml,me_ml,auc_R,ece,note}。
    无规则基线 → 固定 0.5 阈值;无 ΔVME、无规则对照(诚实核心)。
    ST 分组切不出 ≥2 组时短路(无 OOF 可算),记 note 与 NaN 指标。
    """
    id2 = {(r.get("genome_id") or "").strip(): r for r in rows}
    ids = list(id2)
    specs = make_lineage_splits(ids, st_map, n_splits=5)
    if not specs:
        # 唯一 ST<2:GroupKFold 不成立,无 OOF 可算 → 诚实短路(不 np.concatenate 空列表崩)
        y_all = _y(rows)
        return {"species": sp, "drug": drug, "n": len(rows),
                "n_R": int((y_all == 1).sum()), "n_R_ST": 0,
                "vme_ml": None, "me_ml": None, "auc_R": None, "ece": None,
                "note": "ST 分组不足(唯一 ST<2),无法做 ST-grouped OOF"}

    P, Y, ST = [], [], []
    for s in specs:
        tr = [id2[g] for g in s.train_ids]
        te = [id2[g] for g in s.test_ids]
        vocab = fit_vocab(tr, augmented_features)
        ml = GenotypeToSIR(random_state=SEED, model="rf").fit(
            build_X(tr, vocab, augmented_features), _y(tr))
        P.append(ml.predict_proba_r(build_X(te, vocab, augmented_features)))
        Y.append(_y(te))
        ST.append(_st_of(te, st_map))

    p = np.concatenate(P)
    y = np.concatenate(Y)
    st = np.concatenate(ST)
    pred = (p >= 0.5).astype(int)              # ML-only:固定 0.5 阈值(无规则可对齐 ME)
    auc, ece = _auc_ece(y, p)                  # OOF 判别力 + 校准误差(单类 → auc=None)
    per = st_level_vme(st, y, pred)            # per-ST VME(每 ST 一个观测)
    vme = float(np.mean(list(per.values()))) if per else float("nan")
    R = (y == 1)
    S = (y == 0)
    me = float((pred[S] == 1).mean()) if S.any() else 0.0
    return {"species": sp, "drug": drug, "n": len(rows), "n_R": int(R.sum()),
            "n_R_ST": len(per), "vme_ml": round(vme, 4), "me_ml": round(me, 4),
            "auc_R": auc, "ece": ece, "note": ""}


def ml_only_oof(sp: str, drug: str = DRUG) -> dict:
    """从磁盘读入 sp 的 colistin 数据(只在 53 有)→ 纯 ML OOF 评估。"""
    amr, st_map, _ = load_inputs_from_disk(sp, _DATA)
    rows = _combo_rows(amr, st_map, drug)
    return _eval_ml_only(rows, st_map, sp, drug)


# ------------------------------------------------------------------ colistin 标签 QC
def qc_colistin(sp: str, drug: str = DRUG) -> dict:
    """colistin 标签质量:冲突标签率 / 缺基因型率 / unknown-ST 率。诚实量化数据噪声。"""
    amr, st_map, _ = load_inputs_from_disk(sp, _DATA)
    raw = [r for r in amr if r.get("antibiotic") == drug]
    # 冲突标签:同一 genome_id 在 colistin 上同时出现 R 与 S(二分后)
    _bin = {"R": "R", "RESISTANT": "R", "S": "S", "SUSCEPTIBLE": "S"}
    by_gid: dict[str, set[str]] = defaultdict(set)
    for r in raw:
        g = (r.get("genome_id") or "").strip()
        b = _bin.get(str(r.get("resistant_phenotype", "")).strip().upper())
        if g and b:
            by_gid[g].add(b)
    n_gid = len(by_gid)
    n_conflict = sum(1 for v in by_gid.values() if {"R", "S"} <= v)

    rows = _combo_rows(amr, st_map, drug)          # 建模用去重行
    n_rows = len(rows)
    n_missing_geno = sum(1 for r in rows if not (r.get("ncbi_amr_genotypes") or "").strip())
    n_unknown_st = sum(1 for r in rows
                       if str(st_map.get((r.get("genome_id") or "").strip(), "unknown")).lower() == "unknown")
    return {
        "species": sp, "drug": drug,
        "n_raw_rows": len(raw), "n_unique_genome": n_gid, "n_modelable": n_rows,
        "conflict_labels": n_conflict,
        "conflict_rate": round(n_conflict / n_gid, 4) if n_gid else 0.0,
        "missing_genotype": n_missing_geno,
        "missing_genotype_rate": round(n_missing_geno / n_rows, 4) if n_rows else 0.0,
        "unknown_st": n_unknown_st,
        "unknown_st_rate": round(n_unknown_st / n_rows, 4) if n_rows else 0.0,
    }


# ------------------------------------------------------------------ 落盘:manifest
def _write_manifest(metrics: list[dict]) -> None:
    combos = []
    for m in metrics:
        n_rst = m["n_R_ST"]
        combos.append({
            "species": m["species"], "drug": m["drug"],
            "n": m["n"], "n_R": m["n_R"], "n_R_ST": n_rst,
            "feasible": bool(n_rst >= MIN_R_ST),
            "underpowered": bool(n_rst < MIN_R_ST),
            "data_locus": "53",
        })
    doc = {
        "task": "S4 rare-combo — colistin high-risk demonstration",
        "drug": DRUG,
        "positioning": ("colistin 无规则基线(no_baseline):ML-only 评估,诚实表征预测力,"
                        "不声称优于规则、不做 ΔVME、不硬求 strong-pass。"),
        "feasible_threshold": f"R-ST≥{MIN_R_ST}",
        "seed": SEED,
        "combos": combos,
    }
    (_OUT / "rare_combo_data_manifest.yaml").write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")


# ------------------------------------------------------------------ 落盘:metrics CSV
def _write_metrics(metrics: list[dict]) -> None:
    rows = []
    for m in metrics:
        rows.append({
            "species": m["species"], "drug": m["drug"],
            "n": m["n"], "n_R": m["n_R"], "n_R_ST": m["n_R_ST"],
            "vme_ml": _fmt(m["vme_ml"]), "me_ml": _fmt(m["me_ml"]),
            "auc_R": _fmt(m["auc_R"]), "ece": _fmt(m["ece"]),
            "reliable": str(bool(m["n_R_ST"] >= MIN_R_ST)),   # "True"/"False"
        })
    write_csv(_OUT / "rare_combo_metrics.csv", _METRIC_COLS, rows)


# ------------------------------------------------------------------ 落盘:failure modes
def _write_failure_modes() -> None:
    """colistin 失败模式(诚实):每条中文说明 + 为何不宣称强预测。gate 校验四个 key 齐全。"""
    fm = {
        "breakpoint_variability": {
            "说明": ("colistin 的 MIC 折点(breakpoint)历史上多次修订、各标准(CLSI/EUCAST)不一致,"
                     "R/S 判定随标准漂移。训练标签本身承载折点不确定性。"),
            "为何不宣称强预测": "标签金标准不稳,任何高 AUC 都可能只是拟合了特定标准的判定习惯,不宜外推。",
        },
        "phenotype_noise": {
            "说明": ("colistin 表型测定(肉汤微量稀释)技术难度高、重复性差,纸片扩散不可靠,"
                     "实验室间一致性低 → 表型标签噪声大。"),
            "为何不宣称强预测": "标签噪声抬高不可约误差下限,VME/ME 的绝对值不能当作真实临床错误率解读。",
        },
        "mcr_negative_mechanism": {
            "说明": ("colistin 耐药大量由 mcr 阴性机制驱动(mgrB/pmrAB/phoPQ 等染色体突变、脂多糖修饰),"
                     "机制多样且部分不在现有 AMRFinder 基因型特征覆盖内。"),
            "为何不宣称强预测": "关键耐药机制未被特征表征 → 模型对 mcr 阴性耐药存在系统性盲区,召回天花板低。",
        },
        "no_rule_baseline": {
            "说明": ("规则表(amrfinder_sir_rules.yaml)未收录 colistin,RuleBaselineSIR 对 colistin 抛 KeyError → "
                     "无规则基线可对照。"),
            "为何不宣称强预测": ("无对照就无从声称「优于规则」;本任务只做 ML-only 表征,"
                               "不算 ΔVME、不做规则对照、不硬求 strong-pass。"),
        },
    }
    (_OUT / "rare_combo_failure_modes.yaml").write_text(
        yaml.safe_dump(fm, allow_unicode=True, sort_keys=False), encoding="utf-8")


# ------------------------------------------------------------------ 落盘:QC report
def _write_qc_report(qcs: list[dict]) -> None:
    L: list[str] = ["# S4:colistin 标签质量核查(rare_combo QC)\n"]
    L.append("colistin 表型标签噪声高(见 failure_modes)。本表诚实量化:冲突标签率、缺基因型率、unknown-ST 率。\n")
    L.append("| species | drug | 原始行 | 唯一基因组 | 建模行 | 冲突标签 | 冲突率 | 缺基因型 | 缺基因型率 | unknown-ST | unknown-ST率 |")
    L.append("|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    for q in qcs:
        L.append(f"| {q['species']} | {q['drug']} | {q['n_raw_rows']} | {q['n_unique_genome']} | "
                 f"{q['n_modelable']} | {q['conflict_labels']} | {q['conflict_rate']} | "
                 f"{q['missing_genotype']} | {q['missing_genotype_rate']} | "
                 f"{q['unknown_st']} | {q['unknown_st_rate']} |")
    L.append("\n**读法**:冲突标签率反映同一菌株重复测定的 R/S 分歧(折点/测定噪声的直接体现);"
             "unknown-ST 株不进 ST 分组 OOF(被剔除),故建模评估的有效样本 < 原始。\n")
    (_OUT / "rare_combo_qc_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ 落盘:decision
def _write_decision(metrics: list[dict]) -> None:
    L: list[str] = ["# S4:高价值稀有组合 — colistin high-risk demonstration 决策\n"]
    L.append("## 定位(诚实核心)\n")
    L.append("colistin 是对抗泛耐药 GNB 的**最后一线**药,临床极高价值。但规则表**未收录** colistin"
             "(RuleBaselineSIR 抛 KeyError)→ **no_baseline**,无规则基线可对照。故 colistin 定位为"
             "**high-risk demonstration**:诚实表征「能预测到什么程度」,"
             "**不声称优于规则、不做 ΔVME/规则对照、不硬求 strong-pass**。\n")
    L.append("## 方法\n")
    L.append("纯 ML 的 ST 分组 5 折 OOF(不融合规则):augmented_features + RF(seed=0),"
             "OOF 概率固定 0.5 阈值出预测;报 per-ST VME、ME、AUC_R、ECE。无规则基线故无 ΔVME。\n")
    L.append("## 结果(每 colistin 组合)\n")
    L.append("| species | n | n_R | n_R_ST | VME(ml) | ME(ml) | AUC_R | ECE | 可靠? |")
    L.append("|---|--:|--:|--:|--:|--:|--:|--:|:--:|")
    for m in metrics:
        rel = "✅ reliable" if m["n_R_ST"] >= MIN_R_ST else "⚠️ underpowered"
        L.append(f"| {m['species']} | {m['n']} | {m['n_R']} | {m['n_R_ST']} | "
                 f"{_fmt(m['vme_ml']) or 'nan'} | {_fmt(m['me_ml']) or 'nan'} | "
                 f"{_fmt(m['auc_R']) or 'nan'} | {_fmt(m['ece']) or 'nan'} | {rel} |")
    L.append("")
    L.append("## 汇总结论\n")
    feas = [m["species"] for m in metrics if m["n_R_ST"] >= MIN_R_ST]
    under = [m["species"] for m in metrics if m["n_R_ST"] < MIN_R_ST]
    L.append(f"- **colistin = no_baseline high-risk demo**:无规则基线,只做 ML-only 表征,不声称优于规则。")
    L.append(f"- **可评估(R-ST≥{MIN_R_ST},reliable=True)**:{', '.join(feas) or '(53 跑后填)'}"
             "——KP/EC 为主案例,展示「能预测到什么程度」(看 AUC_R/VME),但受 colistin 标签噪声与机制盲区限制,不外推为临床错误率。")
    L.append(f"- **underpowered(R-ST<{MIN_R_ST},reliable=False)**:{', '.join(under) or '(53 跑后填)'}"
             "——R-ST 太少,指标不稳,评估但明确标注不可靠。")
    L.append("- **失败模式**见 rare_combo_failure_modes.yaml(breakpoint 变异 / 表型噪声 / mcr 阴性机制 / 无规则基线)。")
    L.append("")
    L.append("> 数据位点:colistin 表型/ST **只在 53**。本产物由协调方在 53 跑 `python -m ...rare_combos` 生成;"
             "本地无 colistin 数据,gate 待 53 跑完 rsync 回后转 pass。\n")
    (_OUT / "rare_combo_decision.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ 驱动
def run(species: list[str] | None = None) -> None:
    species = species or COLISTIN_SPECIES
    _OUT.mkdir(parents=True, exist_ok=True)
    print(f"S4 colistin rare-combo:{len(species)} 物种 → ML-only OOF(seed={SEED})", flush=True)

    metrics: list[dict] = []
    qcs: list[dict] = []
    for i, sp in enumerate(species, 1):
        m = ml_only_oof(sp, DRUG)
        metrics.append(m)
        qcs.append(qc_colistin(sp, DRUG))
        rel = "reliable" if m["n_R_ST"] >= MIN_R_ST else "UNDERPOWERED"
        print(f"  [{i}/{len(species)}] {sp:26} n={m['n']:>4} n_R={m['n_R']:>4} "
              f"R-ST={m['n_R_ST']:>3} VME={_fmt(m['vme_ml']) or 'nan':>6} "
              f"ME={_fmt(m['me_ml']) or 'nan':>6} AUC={_fmt(m['auc_R']) or 'nan':>6} "
              f"ECE={_fmt(m['ece']) or 'nan':>6}  [{rel}]"
              f"{'  ' + m['note'] if m.get('note') else ''}", flush=True)

    _write_manifest(metrics)
    _write_metrics(metrics)
    _write_failure_modes()
    _write_qc_report(qcs)
    _write_decision(metrics)
    print(f"\n落盘 → {_OUT}(manifest / metrics.csv / failure_modes.yaml / qc_report.md / decision.md)",
          flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="S4 colistin 稀有组合 ML-only 评估(high-risk demo;数据在 53)")
    ap.add_argument("--species", default=",".join(COLISTIN_SPECIES),
                    help="逗号分隔物种(默认 4 个 colistin 组合)")
    args = ap.parse_args()
    run([s.strip() for s in args.species.split(",") if s.strip()])
