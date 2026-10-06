"""S2.1:把 practical 组合经 abstain-aware(选择性预测)分级为 strong / safety-pass / practical-only。

本任务只做**本地 EC/KP 13 组合**(PA/AB/SA 待 53)。

科学立意:
  24 个 practical 组合 = rule-first 融合的 per-ST VME 不劣于规则法但**未达统计显著**(ΔVME 常<0 而 p>0.05)。
  它们不该浪费——通过 abstain(对低置信样本弃权),很多能在保持高覆盖率(≥70%)下把 covered 子集的
  危险漏判 VME 压到 ≤ 规则法且 ME 受控,从而升级为 **safety-pass**(平台"fail-closed + abstain"叙事核心),
  而不是硬凑 strong-pass。

口径(两个 VME 别混):
  * coverage-risk 曲线用 **pooled VME**(covered 里 y==1 & base==0 的比例)——选择性预测标准口径。
  * strong-pass 显著性判据用 **per-ST VME**(st_level_vme 均值 + 配对置换)——与冻结面 sweep 同口径。

复用路径(关键):复用证据面同款 OOF(机制特征 augmented_features + GroupKFold-by-ST),
  与冻结 v0.9 证据面数值一致;**不**走 run_g2r_riskcoverage 里的旧特征路径。

一键复现:
    .venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.abstain_practical \
        --species escherichia_coli,klebsiella_pneumoniae

产物(reports/antibacterial/mdr_gnb/science_v1/abstain_m3/):
    practical_24_coverage_risk.csv / upgraded_to_strong.csv / upgraded_to_safety_pass.csv
    remained_practical.csv / abstain_reason_taxonomy.yaml / practical_24_decision.md
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import numpy as np
import yaml

from praxis_virtualcell.mdr_gnb.evaluators.significance import (
    align_st_vme,
    paired_permutation_test,
    st_level_vme,
)
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
_DETAIL_CSV = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v0.9_freeze" / "05_practical_24_detail.csv"
_OUT = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v1" / "abstain_m3"
DB = "2024-01-frozen"
SEED = 0
N_PERM = 10000

# 本地有评估数据(phenotype/ST 齐)的物种;PA/AB/SA/SE 在 53
LOCAL_SPECIES = ("escherichia_coli", "klebsiella_pneumoniae")
# 全 5 物种(53 数据):--all 用,过滤冻结明细即跑全 24 practical
ALL_SPECIES = (
    "escherichia_coli",
    "klebsiella_pneumoniae",
    "pseudomonas_aeruginosa",
    "acinetobacter_baumannii",
    "salmonella_enterica",
)

# ---- 判据常量(写死,别改)-------------------------------------------------
COVERAGE_GRID = (1.0, 0.9, 0.8, 0.7, 0.6)     # 固定覆盖率网格
SAFETY_COVERAGES = (0.9, 0.8, 0.7)            # safety-pass 允许的覆盖率(c≥0.70),取满足条件的最高 c
COVERED_ME_CAP = 0.10                         # covered 子集 ME 上限(严格 < 0.10)
STRONG_P = 0.05                               # strong-pass 显著性阈
_EPS = 1e-9
RARE_R_ST_MAX = 2                             # R-ST 稀少判定:该 ST 全池真R株数 ≤ 此值 → 稀少/外推

_RISK_COLS = ["species", "drug", "coverage", "vme", "me", "ece", "abstain_rate", "n"]
_STRONG_COLS = ["species", "drug", "coverage_at_pass", "delta_vme", "p_value"]
_SAFETY_COLS = ["species", "drug", "coverage_at_pass", "vme_covered", "vme_rule", "me_covered"]
_PRACTICAL_COLS = ["species", "drug", "reason"]


# ---------------------------------------------------------------- practical 清单
def load_practical_combos(species_filter: list[str] | None) -> list[tuple[str, str]]:
    """读冻结的 24 practical 明细,过滤到指定物种(默认本地 EC/KP → 13 个)。别硬编码药名。"""
    combos: list[tuple[str, str]] = []
    with open(_DETAIL_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("tier") != "practical":
                continue
            sp = r["species"]
            if species_filter is not None and sp not in species_filter:
                continue
            combos.append((sp, r["drug"]))
    return combos


# ---------------------------------------------------------------- 选择性预测核心
def _pooled_vme(y: np.ndarray, pred: np.ndarray) -> float:
    """pooled VME:真 R(y==1)中被判 S(pred==0)的比例;无真 R → nan。"""
    m = y == 1
    return float((pred[m] == 0).mean()) if m.any() else float("nan")


def _keep_mask(conf: np.ndarray, coverage: float) -> np.ndarray:
    """按 conf 降序保留 top-k(k=round(N*coverage));稳定排序保证确定性。"""
    n = len(conf)
    k = int(round(n * coverage))
    order = np.argsort(-conf, kind="stable")   # conf 降序;rule=R 的 inf 恒在前(必保留)
    keep = np.zeros(n, dtype=bool)
    keep[order[:k]] = True
    return keep


def _coverage_risk_rows(sp, drug, y, p, base, conf) -> list[dict]:
    """每覆盖点算 covered 子集 pooled VME/ME + 校准 ECE,返回 5 行。"""
    rows = []
    for c in COVERAGE_GRID:
        keep = _keep_mask(conf, c)
        yk, bk, pk = y[keep], base[keep], p[keep]
        _, ece = _auc_ece(yk, pk)              # covered 子集校准误差(取 ECE)
        rows.append({
            "species": sp, "drug": drug, "coverage": c,
            "vme": round(_pooled_vme(yk, bk), 4),
            "me": round(_me(yk, bk), 4),
            "ece": ece,
            "abstain_rate": round(1.0 - c, 4),
            "n": int(keep.sum()),
        })
    return rows


# ---------------------------------------------------------------- 单组合分级
def analyze_combo(sp: str, drug: str) -> dict:
    """跑单组合 OOF → coverage-risk 曲线 + 三分层判定 + abstain 诊断。"""
    amr, st_map, _ = load_inputs_from_disk(sp, _DATA)
    rows = _combo_rows(amr, st_map, drug)
    rule = RuleBaselineSIR(db_version=DB)
    # 满覆盖 OOF(4 元组,与冻结面同款机制特征):p=ML R 概率, ru=规则 0/1, y=真值 0/1, st=ST 标签
    p, ru, y, st = _oof_predict(rows, st_map, rule, drug, augmented_features, SEED)

    rule_me = _me(y, ru)
    t_star, _, _ = select_tstar(p, ru, y, st, rule_me=rule_me)
    base = np.where(ru == 1, 1, (p >= t_star).astype(int))   # rule-first 融合预测
    conf = np.where(ru == 1, np.inf, np.abs(p - t_star))     # 置信度:rule=R 恒保留(inf),否则离阈越远越有把握

    rule_vme = _pooled_vme(y, ru)                            # 满覆盖规则 pooled VME(safety 参照)
    risk_rows = _coverage_risk_rows(sp, drug, y, p, base, conf)
    full_fusion_vme = risk_rows[0]["vme"]                    # coverage=1.0 行 = 满覆盖融合 VME

    # ---- strong-pass:满覆盖 per-ST ΔVME<0 且 置换 p<0.05(与 sweep 同口径)
    vf, vr = st_level_vme(st, y, base), st_level_vme(st, y, ru)
    keys, mm, rr = align_st_vme(vf, vr)
    if len(keys):
        perm = paired_permutation_test(mm, rr, keys, n_perm=N_PERM, seed=SEED)
        p_value = float(perm["p_value"])
        delta_vme = float(mm.mean() - rr.mean())
    else:
        p_value, delta_vme = float("nan"), float("nan")
    is_strong = bool(len(keys) and delta_vme < 0 and p_value < STRONG_P)

    # ---- safety-pass:非 strong,且某 c∈{0.9,0.8,0.7} 使 covered VME≤规则VME 且 covered ME<0.10
    #      且 abstain 确实有用(该 c 的 covered VME < 满覆盖融合 VME)。取满足条件的最高 c。
    safety = None
    if not is_strong:
        by_c = {r["coverage"]: r for r in risk_rows}
        for c in SAFETY_COVERAGES:              # 0.9 → 0.8 → 0.7,最高优先
            r = by_c[c]
            vme_c, me_c = r["vme"], r["me"]
            if (vme_c <= rule_vme + _EPS
                    and me_c < COVERED_ME_CAP
                    and vme_c < full_fusion_vme - _EPS):    # 弃权确实降低了 VME
                safety = {"coverage_at_pass": c, "vme_covered": vme_c,
                          "vme_rule": round(rule_vme, 4), "me_covered": me_c}
                break

    if is_strong:
        tier = "strong"
    elif safety is not None:
        tier = "safety_pass"
    else:
        tier = "practical_only"

    diag = _diagnose(sp, drug, y, st, base, conf, ru, rule_vme, full_fusion_vme,
                     risk_rows, delta_vme, p_value, tier)

    return {
        "sp": sp, "drug": drug, "tier": tier, "risk_rows": risk_rows,
        "delta_vme": delta_vme, "p_value": p_value,
        "rule_vme": rule_vme, "full_fusion_vme": full_fusion_vme,
        "safety": safety, "diag": diag,
    }


# ---------------------------------------------------------------- abstain 诊断/reason
def _diagnose(sp, drug, y, st, base, conf, ru, rule_vme, full_fusion_vme,
              risk_rows, delta_vme, p_value, tier) -> dict:
    """算 reason taxonomy 命中标记 + practical-only 的落层原因。

    reason 三类(abstain 为何弃权,聚合):
      low_confidence     : |p - t*| 小(ML 对 rule=S 样本无把握)——弃权主力(所有 ML 弃权皆源于此)
      st_extrapolation   : 弃权样本落在训练里 R-ST 稀少/未见 ST(全池真R株数≤RARE_R_ST_MAX)
      coverage_insufficient : 压到 covered ME<0.10 需弃权>30%(c≥0.70 内 ME 始终≥0.10)
    """
    by_c = {r["coverage"]: r for r in risk_rows}
    # 弃权样本(c=0.7 下被剔除的最低置信集)——选择性预测标准考察点
    keep70 = _keep_mask(conf, 0.7)
    abst = ~keep70
    n_abst = int(abst.sum())

    # low_confidence:弃权集全部来自 rule=S 的低 |p-t*|(rule=R conf=inf 恒保留);只要有 ML 弃权即命中
    n_abst_ml = int((abst & (ru == 0)).sum())
    hit_low_conf = n_abst_ml > 0

    # st_extrapolation:弃权的真R样本中,**多数**(占比≥0.5)落在稀少 R-ST(全池该 ST 真R株数≤RARE_R_ST_MAX);
    # 即该组合的 VME 降幅主要来自剔除克隆群证据薄弱的稀少 ST(而非纯阈值邻近)。presence-based 会 13/13 无区分度,
    # 故用占比阈值让本类具判别力。
    r_count_by_st = Counter(st[i] for i in range(len(st)) if y[i] == 1)
    n_abst_R = int(sum(1 for i in range(len(st)) if abst[i] and y[i] == 1))
    n_abst_rareR = int(sum(1 for i in range(len(st))
                          if abst[i] and y[i] == 1 and r_count_by_st.get(st[i], 0) <= RARE_R_ST_MAX))
    rareR_frac = (n_abst_rareR / n_abst_R) if n_abst_R else 0.0
    hit_st_extrap = bool(n_abst_R > 0 and rareR_frac >= 0.5)

    # coverage_insufficient:c≥0.70 内 covered ME 始终 ≥ 0.10(压不下去,须弃权>30%)
    me_ge_cap_all = all(by_c[c]["me"] >= COVERED_ME_CAP for c in SAFETY_COVERAGES)
    me_060 = by_c[0.6]["me"]
    hit_cov_insuff = bool(me_ge_cap_all)

    # practical-only 落层主因(单选,给 remained_practical.csv 的 reason 列)
    reason = ""
    if tier == "practical_only":
        if not (isinstance(delta_vme, float) and delta_vme < 0):
            # ΔVME≥0(ML 无增益)或规则 VME 已 0:无提升空间
            if rule_vme <= _EPS:
                reason = f"rule_vme 已 0(规则无漏判),无提升空间;ΔVME={_r4(delta_vme)} p={_r4(p_value)}"
            else:
                reason = f"ΔVME={_r4(delta_vme)} p={_r4(p_value)}(ML 无增益),abstain 无从降 VME"
        elif hit_cov_insuff:
            reason = (f"coverage_insufficient:c≥0.70 内 covered ME 始终≥{COVERED_ME_CAP}"
                      f"(c=0.6 时 ME={me_060}),压 ME<0.10 须弃权>30%")
        elif full_fusion_vme <= _EPS:
            reason = "满覆盖融合 VME 已 0,abstain 无 VME 可降"
        else:
            reason = ("abstain 未在 c≥0.70 降 covered VME 至 <满覆盖融合 VME"
                      f"(ΔVME={_r4(delta_vme)} p={_r4(p_value)},弃权增益不足)")

    return {
        "n_abst": n_abst, "n_abst_ml": n_abst_ml,
        "n_abst_R": n_abst_R, "n_abst_rareR": n_abst_rareR, "rareR_frac": round(rareR_frac, 3),
        "hit": {"low_confidence": hit_low_conf,
                "st_extrapolation": hit_st_extrap,
                "coverage_insufficient": hit_cov_insuff},
        "reason": reason,
    }


def _r4(x):
    """nan 留空,否则 4 位小数。"""
    return round(float(x), 4) if isinstance(x, float) and x == x else ""


def _build_taxonomy(results: list[dict]) -> dict:
    """聚合三类 reason:每类给中文说明 + 命中组合数/示例。"""
    cats = {
        "low_confidence": (
            "|prob_R − t*| 小:ML 对规则判 S 的样本无把握。弃权主力——所有 ML 弃权本质都是剔除离阈最近的低置信 "
            "rule=S 样本(rule=R 样本 conf=∞ 恒保留)。safety-pass 正是靠它把危险漏判压到规则法之下。"
        ),
        "st_extrapolation": (
            f"弃权的危险漏判候选(真 R 弃权样本)中**多数**(占比≥50%)落在训练里 R-ST 稀少的 ST"
            f"(全池该 ST 真 R 株数≤{RARE_R_ST_MAX})。此类 isolate 的耐药机制在克隆群层面证据薄弱、"
            "ML 外推不可靠,弃权本质是规避 ST 级过拟合而非纯阈值邻近。"
        ),
        "coverage_insufficient": (
            f"要把 covered ME 压到 <{COVERED_ME_CAP} 需弃权 >30%(覆盖率 c<0.70),达不到 safety-pass 的高覆盖要求;"
            "多见于规则本身大量误判 R(ME 高)的组合,abstain 无法在保覆盖前提下同时控 VME 与 ME。"
        ),
    }
    out = {}
    for key, desc in cats.items():
        hits = [f"{r['sp']}::{r['drug']}" for r in results if r["diag"]["hit"][key]]
        out[key] = {
            "说明": desc,
            "命中组合数": len(hits),
            "示例": sorted(hits)[:5],
        }
    return out


# ---------------------------------------------------------------- 决策 md
def _write_decision(results: list[dict], species_filter) -> None:
    strong = [r for r in results if r["tier"] == "strong"]
    safety = [r for r in results if r["tier"] == "safety_pass"]
    practical = [r for r in results if r["tier"] == "practical_only"]
    sp_arg = ",".join(species_filter) if species_filter else ",".join(LOCAL_SPECIES)

    L: list[str] = []
    L.append("# S2.1:practical 组合 abstain-aware 分级(本地 EC/KP 13 组合)\n")
    L.append(
        "把 24 个 practical(rule-first 融合不劣于规则法但未达统计显著)组合,通过 **abstain(选择性预测)** "
        "重新分级:对低置信样本弃权,考察能否在高覆盖率(≥70%)下把 covered 子集危险漏判 VME 压到 ≤ 规则法且 "
        "ME 受控,从而升级为 **safety-pass**(平台 fail-closed + abstain 叙事核心)。\n"
    )
    L.append("## 进度\n")
    L.append(
        f"- 本地 **{len(results)}/24** 组合已做(EC/KP);PA/AB/SA 的 11 个 practical 待 53 数据管线(S2 后续)。\n"
        f"- 分层:**strong-pass {len(strong)}** · **safety-pass {len(safety)}** · **practical-only {len(practical)}**。\n"
    )
    L.append("## 一键复现\n")
    L.append("```bash")
    L.append(
        ".venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.abstain_practical \\\n"
        f"    --species {sp_arg}"
    )
    L.append("```")
    L.append(f"\n确定性:seed={SEED};置换检验 {N_PERM} 次固定 seed;覆盖率网格 {{1.0,0.9,0.8,0.7,0.6}};重跑一致。\n")

    if safety:
        L.append("## safety-pass 亮点\n")
        L.append("| species | drug | coverage_at_pass | covered VME | 规则 VME | covered ME |")
        L.append("|---|---|:--:|---:|---:|---:|")
        for r in sorted(safety, key=lambda x: (x["sp"], x["drug"])):
            s = r["safety"]
            L.append(
                f"| {r['sp']} | {r['drug']} | {s['coverage_at_pass']} | "
                f"{s['vme_covered']} | {s['vme_rule']} | {s['me_covered']} |"
            )
        L.append(
            "\n解读:在保留 ≥70% 样本的前提下,covered 子集的危险漏判 VME 已 ≤ 规则法(且 ME<0.10);"
            "对弃权的低置信少数样本回落 fail-closed(判 R),整体不劣于规则法而覆盖多数病例。\n"
        )

    if practical:
        L.append("## remained practical-only\n")
        L.append("| species | drug | 落层原因 |")
        L.append("|---|---|---|")
        for r in sorted(practical, key=lambda x: (x["sp"], x["drug"])):
            L.append(f"| {r['sp']} | {r['drug']} | {r['diag']['reason']} |")
        L.append("")

    L.append("## 分组合 coverage-risk 摘要\n")
    L.append("| species | drug | 分层 | 满覆盖融合VME | 规则VME | ΔVME(per-ST) | p |")
    L.append("|---|---|:--:|---:|---:|---:|---:|")
    for r in sorted(results, key=lambda x: (x["sp"], x["drug"])):
        L.append(
            f"| {r['sp']} | {r['drug']} | {r['tier']} | {r['full_fusion_vme']} | "
            f"{round(r['rule_vme'], 4)} | {_r4(r['delta_vme'])} | {_r4(r['p_value'])} |"
        )
    L.append(
        "\n口径提醒:coverage-risk 曲线用 **pooled VME**(covered 里 y==1 且 base==0 的比例);"
        "strong-pass 显著性用 **per-ST VME**(st_level_vme 均值 + 配对置换),两者不可混。\n"
    )
    (_OUT / "practical_24_decision.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 驱动
def run(species_filter: list[str] | None) -> None:
    _OUT.mkdir(parents=True, exist_ok=True)
    combos = load_practical_combos(species_filter)
    print(f"practical 组合 {len(combos)}(过滤={species_filter or 'local EC/KP'});逐组合跑 OOF + abstain 分级…",
          flush=True)

    results: list[dict] = []
    for i, (sp, drug) in enumerate(combos, 1):
        res = analyze_combo(sp, drug)
        results.append(res)
        s = res["safety"]
        tag = res["tier"]
        extra = (f" c*={s['coverage_at_pass']} coveredVME={s['vme_covered']} ruleVME={s['vme_rule']}"
                 if s else f" reason={res['diag']['reason'][:40]}")
        print(
            f"  [{i}/{len(combos)}] {sp[:20]:20} × {drug:26} "
            f"满覆盖融合VME={res['full_fusion_vme']:.4f} ΔVME={_r4(res['delta_vme'])} p={_r4(res['p_value'])} "
            f"→ {tag}{extra}",
            flush=True,
        )

    # 落盘:coverage-risk / 三分层 CSV / taxonomy / decision md
    all_risk = [row for r in results for row in r["risk_rows"]]
    write_csv(_OUT / "practical_24_coverage_risk.csv", _RISK_COLS, all_risk)

    strong_rows = [{"species": r["sp"], "drug": r["drug"], "coverage_at_pass": 1.0,
                    "delta_vme": _r4(r["delta_vme"]), "p_value": _r4(r["p_value"])}
                   for r in results if r["tier"] == "strong"]
    write_csv(_OUT / "upgraded_to_strong.csv", _STRONG_COLS, strong_rows)

    safety_rows = [{"species": r["sp"], "drug": r["drug"], **r["safety"]}
                   for r in results if r["tier"] == "safety_pass"]
    write_csv(_OUT / "upgraded_to_safety_pass.csv", _SAFETY_COLS, safety_rows)

    practical_rows = [{"species": r["sp"], "drug": r["drug"], "reason": r["diag"]["reason"]}
                      for r in results if r["tier"] == "practical_only"]
    write_csv(_OUT / "remained_practical.csv", _PRACTICAL_COLS, practical_rows)

    (_OUT / "abstain_reason_taxonomy.yaml").write_text(
        yaml.safe_dump(_build_taxonomy(results), allow_unicode=True, sort_keys=True),
        encoding="utf-8",
    )
    _write_decision(results, species_filter)

    n_strong = sum(r["tier"] == "strong" for r in results)
    n_safety = sum(r["tier"] == "safety_pass" for r in results)
    n_prac = sum(r["tier"] == "practical_only" for r in results)
    print(
        f"\n落盘 → {_OUT}\n"
        f"  组合={len(results)}  coverage-risk 行={len(all_risk)}  "
        f"strong={n_strong} safety-pass={n_safety} practical-only={n_prac}",
        flush=True,
    )


def _parse_species(args) -> list[str] | None:
    if args.all:
        # --all(53 全物种):过滤冻结明细即跑全 24 practical。仅 53 有 PA/AB/SA 的
        # phenotype/ST,本地跑会在 load_inputs_from_disk 崩(预期)。
        return list(ALL_SPECIES)
    return [s.strip() for s in args.species.split(",") if s.strip()]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="S2.1 practical abstain-aware 分级(本地 EC/KP 13 组合)")
    ap.add_argument("--species", default=",".join(LOCAL_SPECIES), help="逗号分隔物种(默认本地 EC/KP)")
    ap.add_argument("--all", action="store_true", help="全 5 物种(53 数据):跑全 24 practical")
    args = ap.parse_args()
    run(_parse_species(args))
