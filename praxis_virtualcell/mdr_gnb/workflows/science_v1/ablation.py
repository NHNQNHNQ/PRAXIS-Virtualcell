"""S5.1:机制层可证伪验证——消融矩阵。

科学问题:rule-first + ML fusion 的优势来自哪里?机制特征有没有增益?
不是证明"机制层万能",而是拆解 fusion 优势来源,诚实量化每个成分的贡献:
  rule-first 主要降危险漏判(VME)、ML residual 补规则漏判、机制特征在部分药提供增益、
  去掉机制某些组合下降、机制无效组合诚实标记(可证伪的价值)。

本任务只做**本地 EC/KP 6 anchor**(PA/AB/SA 待 53)。

消融 6 版本(本项目真实特征轴:base=parse_genotypes,mech=augmented_features;**无 k-mer/unitig**):
  A_rule_only          纯规则(冻结 AMRFinderPlus 规则法),pred=rule_pred
  B_ml_only            纯 ML(base 特征),pred=(p_base>=0.5),不融合规则
  C_fusion             rule-first 融合,ML=base 特征:pred=where(rule==R,1,p_base>=t*_base)
  D_fusion_mech        rule-first 融合,ML=mech 特征(=冻结生产路径):pred=where(rule==R,1,p_mech>=t*_mech)
  E_fusion_mech_abstain D + abstain(选择性预测),报 covered 指标 + coverage
  F_ablate_mech        = C(从 D 去掉机制特征,作对照量化机制增益);数值同 C_fusion
机制增益 = D 的 VME − F(=C)的 VME(负=机制降低 VME)。

方法(frozen-consistent OOF,同 sweep):每 anchor 组合 5 折 ST-grouped OOF,两个 featurizer 各跑一遍
  拿 p_base / p_mech;规则预测确定性无需训练。t* 用 select_tstar(对齐规则 ME)。口径:
  VME=per-ST VME(st_level_vme 均值,同冻结面);ME=pooled(_me);AUC/ECE=_auc_ece(rule-only 无概率→空)。

一键复现:
    .venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.ablation \
        --species escherichia_coli,klebsiella_pneumoniae

产物(reports/antibacterial/mdr_gnb/science_v1/mechanism_falsification/):
    ablation_matrix.csv / mechanism_gain_by_drug.csv / mechanism_gain_by_species.csv
    failed_mechanism_cases.md
"""
from __future__ import annotations

import argparse
import csv
from collections import OrderedDict
from pathlib import Path

import numpy as np

from praxis_virtualcell.mdr_gnb.evaluators.significance import st_level_vme
from praxis_virtualcell.mdr_gnb.predictors.features import parse_genotypes
from praxis_virtualcell.mdr_gnb.predictors.mechanism_features import augmented_features
from praxis_virtualcell.mdr_gnb.predictors.rule_baseline import RuleBaselineSIR
from praxis_virtualcell.mdr_gnb.workflows.build_data_foundation import load_inputs_from_disk
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_evidence_sweep import _auc_ece, _combo_rows
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_locked import _me
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_nested_cv import _oof_predict, select_tstar
from praxis_virtualcell.mdr_gnb.workflows.science_v1._io import write_csv

# 仓库根(本文件在 praxis_virtualcell/mdr_gnb/workflows/science_v1/)
_ROOT = Path(__file__).resolve().parents[4]
_DATA = _ROOT / "data" / "mdr_gnb"
_SURFACE_CSV = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v0.9_freeze" / "02_evidence_surface_132.csv"
_OUT = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v1" / "mechanism_falsification"
DB = "2024-01-frozen"
SEED = 0

# 本地有评估数据(phenotype/ST 齐)的物种;PA/AB/SA 在 53
LOCAL_SPECIES = ("escherichia_coli", "klebsiella_pneumoniae")

# anchor panel(本地 6;panel 定义来自任务,数值全部现算不硬编码)
ANCHORS = (
    ("escherichia_coli", "ceftriaxone"),
    ("escherichia_coli", "meropenem"),
    ("escherichia_coli", "ciprofloxacin"),
    ("klebsiella_pneumoniae", "meropenem"),
    ("klebsiella_pneumoniae", "cefepime"),
    ("klebsiella_pneumoniae", "ciprofloxacin"),
)
# 53 待办 anchor(PA/AB/SA):与 holdout.PENDING_ANCHORS 一致;默认不跑,--all(53 数据)才并入
PENDING_ANCHORS = (
    ("pseudomonas_aeruginosa", "levofloxacin"),
    ("pseudomonas_aeruginosa", "meropenem"),
    ("acinetobacter_baumannii", "meropenem"),
    ("acinetobacter_baumannii", "tigecycline"),
    ("salmonella_enterica", "ceftriaxone"),
    ("salmonella_enterica", "ciprofloxacin"),
)
# --all 的完整 anchor 池(本地 6 + 53 待办 6 = 12);实际跑哪些由 run 的 surface gate 决定
ALL_ANCHORS = ANCHORS + PENDING_ANCHORS

VERSIONS = ("A_rule_only", "B_ml_only", "C_fusion", "D_fusion_mech",
            "E_fusion_mech_abstain", "F_ablate_mech")
_MATRIX_COLS = ["species", "drug", "version", "vme", "me", "auc_R", "ece", "coverage"]
_DRUG_COLS = ["drug", "n_combos", "delta_vme_D_minus_C", "mean_vme_C", "mean_vme_D"]
_SP_COLS = ["species", "n_combos", "delta_vme_D_minus_C"]

# E 版本 abstain:选择性预测覆盖率网格 + 运行点约束(复用 S2.1/riskcoverage 思路)
ABSTAIN_GRID = (1.0, 0.95, 0.90, 0.85, 0.80)   # 降序;coverage≥0.80 是运行点下限
ABSTAIN_MIN_COV = 0.80                          # 运行点覆盖率下限
COVERED_ME_CAP = 0.10                           # covered 子集 ME 上限(严格 < 0.10)


# ---------------------------------------------------------------- 小工具
def _load_surface() -> dict[tuple[str, str], dict]:
    """读冻结证据面 132,返回 {(species,drug): row}。用于 --all 的 surface gate。"""
    with open(_SURFACE_CSV, encoding="utf-8") as fh:
        return {(r["species"], r["drug"]): r for r in csv.DictReader(fh)}


def _per_st_vme(st, y, pred) -> float:
    """per-ST VME:st_level_vme 各 ST 观测的均值(同冻结面口径);无真R的ST → nan。"""
    d = st_level_vme(st, y, pred)
    return float(np.mean(list(d.values()))) if d else float("nan")


def _r4(x) -> float | str:
    """nan/None 留空,否则 4 位小数(确定性落盘)。"""
    if x is None:
        return ""
    x = float(x)
    return "" if x != x else round(x, 4)


def _keep_mask(conf: np.ndarray, coverage: float) -> np.ndarray:
    """按 conf 降序保留 top-k(k=round(N*coverage));稳定排序保证确定性。rule=R(conf=inf)恒保留。"""
    n = len(conf)
    k = int(round(n * coverage))
    order = np.argsort(-conf, kind="stable")
    keep = np.zeros(n, dtype=bool)
    keep[order[:k]] = True
    return keep


def _select_abstain_point(y, pred, p_mech, st, conf) -> tuple[dict, bool]:
    """选 E 运行点(复用 S2.1/riskcoverage 思路)。返回 (该点 covered 指标, 是否找到 ME-安全点)。

    在 coverage≥0.80 的网格里,取满足 covered ME<0.10 的运行点中 **covered per-ST VME 最低** 的那个
    (并列取最高覆盖率,尽量多覆盖病例)——展示选择性预测在 ME 受控下能把危险漏判压多低。
    若无网格点能把 covered ME 压到 <0.10(规则过度判 R、ME 失控)→ 退回满覆盖(E≡D),诚实标记
    abstain 在该组合无 ME-安全运行点(而非报 VME=0/ME 爆表的退化点)。"""
    best = None   # (排序键 (vme, -cov), coverage)
    for c in ABSTAIN_GRID:                        # 降序:1.0 → 0.80
        if c < ABSTAIN_MIN_COV - 1e-9:
            continue
        keep = _keep_mask(conf, c)
        me_c = _me(y[keep], pred[keep])
        vme_c = _per_st_vme(st[keep], y[keep], pred[keep])
        if me_c < COVERED_ME_CAP and vme_c == vme_c:      # ME 受控且 VME 非 nan
            cand = (vme_c, -c)                    # VME 最低优先;并列取最高覆盖率
            if best is None or cand < best[0]:
                best = (cand, c)
    found = best is not None
    chosen = best[1] if found else 1.0           # 无 ME-安全点 → 满覆盖(E≡D)
    keep = _keep_mask(conf, chosen)
    auc, ece = _auc_ece(y[keep], p_mech[keep])
    return {
        "vme": _per_st_vme(st[keep], y[keep], pred[keep]),
        "me": _me(y[keep], pred[keep]),
        "auc_R": auc, "ece": ece, "coverage": chosen,
    }, found


# ---------------------------------------------------------------- 单组合 6 版本
def ablate_combo(sp: str, drug: str) -> dict:
    """跑单 anchor 组合的 6 消融版本。两个 featurizer 各一遍 OOF(p_base / p_mech,ru/y/st 同序一致)。"""
    amr, st_map, _ = load_inputs_from_disk(sp, _DATA)
    rows = _combo_rows(amr, st_map, drug)
    rule = RuleBaselineSIR(db_version=DB)

    # 两路 OOF:base(parse_genotypes)与 mech(augmented_features);ru/y/st 两次一致,以 mech 那次为准(=冻结面)
    p_base, ru, y, st = _oof_predict(rows, st_map, rule, drug, parse_genotypes, SEED)
    p_mech, ru2, y2, st2 = _oof_predict(rows, st_map, rule, drug, augmented_features, SEED)
    assert np.array_equal(ru, ru2) and np.array_equal(y, y2) and np.array_equal(st, st2), \
        "两路 OOF 的 ru/y/st 必须逐字一致(同 rows/折/seed);不一致说明特征路径接错"

    rule_me = _me(y, ru)
    # C/D 的 t*:各自 OOF 上对齐规则 ME 选运行点(rule-first 融合)
    t_base = select_tstar(p_base, ru, y, st, rule_me=rule_me)[0]
    t_mech = select_tstar(p_mech, ru, y, st, rule_me=rule_me)[0]

    pred_C = np.where(ru == 1, 1, (p_base >= t_base).astype(int))
    pred_D = np.where(ru == 1, 1, (p_mech >= t_mech).astype(int))
    pred_B = (p_base >= 0.5).astype(int)                     # 纯 ML,0.5 阈,不借规则

    auc_base, ece_base = _auc_ece(y, p_base)
    auc_mech, ece_mech = _auc_ece(y, p_mech)

    # A_rule_only:规则无概率 → auc/ece 空
    row_A = {"version": "A_rule_only", "vme": _per_st_vme(st, y, ru), "me": _me(y, ru),
             "auc_R": None, "ece": None, "coverage": 1.0}
    row_B = {"version": "B_ml_only", "vme": _per_st_vme(st, y, pred_B), "me": _me(y, pred_B),
             "auc_R": auc_base, "ece": ece_base, "coverage": 1.0}
    row_C = {"version": "C_fusion", "vme": _per_st_vme(st, y, pred_C), "me": _me(y, pred_C),
             "auc_R": auc_base, "ece": ece_base, "coverage": 1.0}
    row_D = {"version": "D_fusion_mech", "vme": _per_st_vme(st, y, pred_D), "me": _me(y, pred_D),
             "auc_R": auc_mech, "ece": ece_mech, "coverage": 1.0}
    # E:D + abstain(基于 mech 融合的置信弃权)
    conf = np.where(ru == 1, np.inf, np.abs(p_mech - t_mech))
    e, e_found = _select_abstain_point(y, pred_D, p_mech, st, conf)
    row_E = {"version": "E_fusion_mech_abstain", **e}
    # F_ablate_mech = C(从 D 去掉机制),数值逐字同 C
    row_F = dict(row_C, version="F_ablate_mech")

    versions = [row_A, row_B, row_C, row_D, row_E, row_F]
    for v in versions:
        v["species"], v["drug"] = sp, drug
    return {
        "sp": sp, "drug": drug, "versions": versions,
        "vme_C": row_C["vme"], "vme_D": row_D["vme"],
        "delta_vme_D_minus_C": row_D["vme"] - row_C["vme"],   # 机制增益(负=机制降 VME)
        "vme_rule": row_A["vme"], "vme_ml_only": row_B["vme"],
        "vme_D_abstain": row_E["vme"], "cov_abstain": row_E["coverage"], "abstain_found": e_found,
        "t_base": t_base, "t_mech": t_mech,
    }


# ---------------------------------------------------------------- 聚合
def _gain_by(results: list[dict], group_key: str, out_col: str) -> list[dict]:
    """按 results[group_key] 聚合机制增益:n_combos + 组内 ΔVME(D-C)/vme_C/vme_D 均值。
    out_col 是落盘的列名(drug 用 'drug'、物种用 'species';后者 results 里键是 'sp')。"""
    groups: "OrderedDict[str, list[dict]]" = OrderedDict()
    for r in results:
        groups.setdefault(r[group_key], []).append(r)
    out = []
    for k, grp in groups.items():
        d = float(np.mean([g["delta_vme_D_minus_C"] for g in grp]))
        out.append({out_col: k, "n_combos": len(grp),
                    "delta_vme_D_minus_C": round(d, 4),
                    "mean_vme_C": round(float(np.mean([g["vme_C"] for g in grp])), 4),
                    "mean_vme_D": round(float(np.mean([g["vme_D"] for g in grp])), 4)})
    return out


# ---------------------------------------------------------------- failed_mechanism_cases.md
def _write_failed_cases(results: list[dict]) -> None:
    """诚实列出:机制无增益/反向(D-C≥0)的组合;以及机制/融合确实帮了的组合(D-C<0)。"""
    helped = sorted([r for r in results if r["delta_vme_D_minus_C"] < -1e-9],
                    key=lambda r: r["delta_vme_D_minus_C"])
    no_gain = sorted([r for r in results if r["delta_vme_D_minus_C"] >= -1e-9],
                     key=lambda r: r["delta_vme_D_minus_C"], reverse=True)

    L: list[str] = []
    L.append("# S5.1:机制消融——诚实清单(本地 EC/KP 6 anchor)\n")
    L.append(
        "拆解 rule-first + ML fusion 优势来源。机制增益 = D_fusion_mech 的 per-ST VME − F(=C_fusion)的 per-ST VME"
        "(负 = 机制特征降低危险漏判)。**机制不是万能**:某些药机制帮忙、某些没用甚至微增 VME,如实记录——"
        "这正是可证伪的价值。\n"
    )
    L.append("## 一键复现\n```bash")
    L.append(".venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.ablation \\\n"
             "    --species escherichia_coli,klebsiella_pneumoniae")
    L.append("```")
    L.append(f"\n确定性:seed={SEED};两路 featurizer(base=parse_genotypes / mech=augmented_features)各 5 折 "
             "ST-grouped OOF;重跑一致。D_fusion_mech 逐字复现冻结生产路径。\n")

    L.append("## 机制确实帮了的组合(D−C<0)\n")
    if helped:
        L.append("| species | drug | vme_C(base融合) | vme_D(mech融合) | ΔVME(D−C) |")
        L.append("|---|---|---:|---:|---:|")
        for r in helped:
            L.append(f"| {r['sp']} | {r['drug']} | {round(r['vme_C'], 4)} | "
                     f"{round(r['vme_D'], 4)} | {round(r['delta_vme_D_minus_C'], 4)} |")
    else:
        L.append("_(本 panel 无组合出现机制增益;诚实标记。)_")
    L.append("")

    L.append("## 机制无增益 / 反向的组合(D−C≥0)——诚实标记\n")
    if no_gain:
        L.append("| species | drug | vme_C(base融合) | vme_D(mech融合) | ΔVME(D−C) | 说明 |")
        L.append("|---|---|---:|---:|---:|---|")
        for r in no_gain:
            dv = r["delta_vme_D_minus_C"]
            if abs(dv) <= 1e-9:
                note = "机制与 base 融合等价(该药 VME 已由规则/base 特征吃满,机制无额外信息)"
            else:
                note = "机制融合 VME 略高于 base 融合(机制特征在该药未带来危险漏判增益)"
            L.append(f"| {r['sp']} | {r['drug']} | {round(r['vme_C'], 4)} | "
                     f"{round(r['vme_D'], 4)} | {round(dv, 4)} | {note} |")
    else:
        L.append("_(本 panel 所有组合机制均有增益。)_")
    L.append("")

    L.append("## rule vs ML vs fusion(危险漏判 VME 拆解)\n")
    L.append("| species | drug | A规则 | B纯ML | C base融合 | D mech融合 |")
    L.append("|---|---|---:|---:|---:|---:|")
    for r in sorted(results, key=lambda x: (x["sp"], x["drug"])):
        L.append(f"| {r['sp']} | {r['drug']} | {round(r['vme_rule'], 4)} | "
                 f"{round(r['vme_ml_only'], 4)} | {round(r['vme_C'], 4)} | {round(r['vme_D'], 4)} |")
    L.append(
        "\n解读:rule-first 融合(C/D)的 per-ST VME 恒 ≤ 规则法(A)——融合只在规则判 S 的样本上叠加 ML 判 R,"
        "不会漏掉规则已抓到的耐药,故危险漏判不增反降。纯 ML(B)不借规则兜底,VME 通常高于融合——"
        "这正是 rule-first 的安全价值。机制特征(D vs C)是否再降 VME 逐药类不同,见上表。\n"
    )

    L.append("## E:mech 融合 + abstain(选择性预测)\n")
    L.append("运行点 = coverage≥0.80 网格里 covered ME<0.10 的点中 covered per-ST VME 最低者(并列取最高覆盖率);"
             "无 ME-安全点则退回满覆盖(E≡D)。\n")
    L.append("| species | drug | D满覆盖VME | E covered VME | E coverage | ME-安全点? |")
    L.append("|---|---|---:|---:|:--:|:--:|")
    for r in sorted(results, key=lambda x: (x["sp"], x["drug"])):
        tag = "是" if r["abstain_found"] else "否(退回 D)"
        L.append(f"| {r['sp']} | {r['drug']} | {round(r['vme_D'], 4)} | "
                 f"{round(r['vme_D_abstain'], 4)} | {r['cov_abstain']} | {tag} |")
    L.append(
        "\n解读:abstain 只在 covered ME 能压到 <0.10 的组合上有 ME-安全运行点(如 EC×ceftriaxone,弃权 ~10% "
        "把 covered VME 再砍半)。规则过度判 R、covered ME 始终≥0.10 的组合(KP×mero/cefepime、KP×cipro),"
        "abstain 虽能把 covered VME 压到极低,却以 ME 爆表为代价——退化预测器,正是本项目 ME 纪律要挡的,"
        "故诚实退回满覆盖 D,不报该退化点。\n"
    )
    (_OUT / "failed_mechanism_cases.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 驱动
def run(species_filter: list[str]) -> None:
    _OUT.mkdir(parents=True, exist_ok=True)
    surface = _load_surface()
    # 候选 = 完整 anchor 池按物种过滤:默认 EC/KP → 本地 6;--all → 全 12。
    candidates = [(sp, dr) for (sp, dr) in ALL_ANCHORS if sp in species_filter]
    # 存在性 gate:只跑在冻结证据面 132 且有数据(n 非空)的 anchor。本地 6 恒满足(默认行为不变);
    # --all 的 AB×tigecycline(未收录进面)/SA×ciprofloxacin(收录但 tier=unevaluated、n 空)跳过并警告——
    # 避免 _combo_rows 空 → _oof_predict 崩;与 holdout 同口径,保持 S3.1/S5.1 anchor panel 一致。
    anchors: list[tuple[str, str]] = []
    for sp, dr in candidates:
        s = surface.get((sp, dr))
        if s and s.get("n"):
            anchors.append((sp, dr))
        else:
            reason = "未收录进冻结证据面 132" if s is None else "冻结面 tier=unevaluated(n 空)"
            print(f"  ⚠️ anchor {sp}×{dr} {reason},跳过消融", flush=True)
    print(f"anchor 组合 {len(anchors)}(过滤={species_filter});逐组合跑两路 OOF + 6 版本消融…", flush=True)

    results: list[dict] = []
    matrix_rows: list[dict] = []
    for i, (sp, drug) in enumerate(anchors, 1):
        res = ablate_combo(sp, drug)
        results.append(res)
        matrix_rows.extend(res["versions"])
        print(
            f"  [{i}/{len(anchors)}] {sp[:22]:22} × {drug:14} "
            f"A={res['vme_rule']:.4f} B={res['vme_ml_only']:.4f} C={res['vme_C']:.4f} "
            f"D={res['vme_D']:.4f} ΔVME(D-C)={res['delta_vme_D_minus_C']:+.4f}",
            flush=True,
        )

    # 落盘 1:消融矩阵(每组合×每版本)
    matrix_out = [{"species": v["species"], "drug": v["drug"], "version": v["version"],
                   "vme": _r4(v["vme"]), "me": _r4(v["me"]),
                   "auc_R": _r4(v["auc_R"]), "ece": _r4(v["ece"]),
                   "coverage": _r4(v["coverage"])}
                  for v in matrix_rows]
    write_csv(_OUT / "ablation_matrix.csv", _MATRIX_COLS, matrix_out)

    # 落盘 2/3:逐药类 / 逐物种机制增益
    write_csv(_OUT / "mechanism_gain_by_drug.csv", _DRUG_COLS, _gain_by(results, "drug", "drug"))
    write_csv(_OUT / "mechanism_gain_by_species.csv", _SP_COLS, _gain_by(results, "sp", "species"))

    # 落盘 4:诚实清单
    _write_failed_cases(results)

    n_helped = sum(r["delta_vme_D_minus_C"] < -1e-9 for r in results)
    print(
        f"\n落盘 → {_OUT}\n"
        f"  组合={len(results)}  矩阵行={len(matrix_out)}  机制有增益(D-C<0)={n_helped}/{len(results)}",
        flush=True,
    )


def _parse_species(args) -> list[str]:
    if args.all:
        # --all(53 数据):返回全 anchor 池涉及的 5 物种,run 再按 surface gate 决定实跑哪些。
        # 仅 53 有 PA/AB/SA 的 phenotype/ST,本地跑会在 load_inputs_from_disk 崩(预期)。
        return sorted({sp for sp, _ in ALL_ANCHORS})
    return [s.strip() for s in args.species.split(",") if s.strip()]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="S5.1 机制消融矩阵(本地 EC/KP 6 anchor)")
    ap.add_argument("--species", default=",".join(LOCAL_SPECIES), help="逗号分隔物种(默认本地 EC/KP)")
    ap.add_argument("--all", action="store_true", help="全 5 物种(53 数据):跑全 anchor panel")
    args = ap.parse_args()
    run(_parse_species(args))
