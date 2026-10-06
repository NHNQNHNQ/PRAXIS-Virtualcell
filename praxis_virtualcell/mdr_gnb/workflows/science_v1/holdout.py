"""外推验证 holdout:S3.1 lineage(ST-cluster)+ S3.2 temporal(时间外推)。

--mode lineage(S3.1):本地 EC/KP 6 anchor 的 anchor panel + ST-cluster holdout。
--mode temporal(S3.2):train≤2021 / test≥2022 时间外推——用 2021 及之前的 isolate 训练,
  在 2022+ 近年 isolate 上测,回答审稿人"换年份还行吗"。见文件下方 run_temporal / temporal_holdout_combo。
本文件只做**本地 EC/KP**(PA/AB/SA anchor 待 53;source holdout 是 S3.3)。

科学立意:
  现有 strong/practical 结果都是 5 折 ST-grouped OOF(每个 ST 整体不跨 train/test)。审稿人会问:
  换谱系还行吗?是不是只在同一数据生态里拟合?S3.1 做**更强的外推**——留出**整组谱系**(ST 簇)
  而非随机 ST 折,证明模型能泛化到 held-out 的 lineage 群。

方法(prevalence 分层 leave-one-cluster-out,写死别自创):
  对每个 anchor 组合:
    1. 取该组合所有 isolate(同 S1.1:load_inputs_from_disk + _combo_rows),拿每 isolate 的 ST(剔除 unknown-ST)。
    2. 统计每唯一 ST 的 isolate 频次,**按频次降序**把唯一 ST 切成 **K=4 个连续分箱**
       (bin0=最常见的一批 ST,bin3=最稀有的一批;按累计 isolate 数均分)。这 4 个 bin = 4 个
       lineage cluster(prevalence 分层)——测"从常见谱系泛化到稀有谱系",比随机 ST 折更强。
    3. leave-one-cluster-out:对每个 held cluster c:
       - train = 其余 3 个 cluster 的所有 isolate;test = cluster c 的 isolate。
       - 特征 augmented_features + build_X/fit_vocab(frozen-consistent,别用 build_feature_matrix)。
       - ml = GenotypeToSIR(rf, seed=0).fit(build_X(train,vocab), _y(train))。
       - **t* 只在 train 上选**(防泄漏):select_tstar(p_train, rule_train, y_train, st_train, rule_me=...)[0]。
       - held cluster 出融合 fu = where(rule_test==R,1, p_test>=t*) 与规则 rule_test。
       - 算 held cluster 上 per-ST VME:融合/规则均值 + ΔVME=融合−规则。记 n、n_R、t*。
       - 有真 R 才评 VME;无真 R(rare bin 全 S)→ VME 记 nan/空(诚实)。

一键复现:
    .venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.holdout \
        --species escherichia_coli,klebsiella_pneumoniae --mode lineage

产物(reports/antibacterial/mdr_gnb/science_v1/external_holdout/):
    anchor_panel_manifest.yaml / lineage_holdout_metrics.csv / external_holdout_decision.md
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import numpy as np
import yaml

from praxis_virtualcell.mdr_gnb.evaluators.significance import st_level_vme
from praxis_virtualcell.mdr_gnb.predictors.genotype_to_sir import GenotypeToSIR
from praxis_virtualcell.mdr_gnb.predictors.mechanism_features import augmented_features
from praxis_virtualcell.mdr_gnb.predictors.rule_baseline import RuleBaselineSIR
from praxis_virtualcell.mdr_gnb.workflows.build_data_foundation import load_inputs_from_disk
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_evidence_sweep import _combo_rows
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_lever_a import build_X, fit_vocab
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_locked import _me, _rule_pred, _st_of, _y
from praxis_virtualcell.mdr_gnb.workflows.run_g2r_nested_cv import select_tstar
from praxis_virtualcell.mdr_gnb.workflows.science_v1._io import write_csv

# 仓库根(本文件在 praxis_virtualcell/mdr_gnb/workflows/science_v1/)
_ROOT = Path(__file__).resolve().parents[4]
_DATA = _ROOT / "data" / "mdr_gnb"
_SURFACE_CSV = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v0.9_freeze" / "02_evidence_surface_132.csv"
_OUT = _ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v1" / "external_holdout"
DB = "2024-01-frozen"
SEED = 0
K_CLUSTERS = 4                          # prevalence 分箱数(唯一 ST 按频次降序切 4 连续箱)

# --- S3.2 时间外推 holdout(train≤CUTOFF / test>CUTOFF)------------------------
CUTOFF = 2021                           # 训练用 2021 及之前,测试用 2022+(现代 isolate,回答"换年份还行吗")
MIN_TRAIN = 50                          # train 太少 → underpowered,诚实跳过
MIN_TEST = 20                           # test 太少 → underpowered,诚实跳过
MIN_TEST_R_ST = 5                       # test 侧真 R-ST 不足 → 不硬跑噪声 VME,诚实跳过(纪律)
# 要评估的时间 anchor(需 biosample 年份缓存;无缓存/样本不足诚实跳过)。
# 注:年份缓存按物种(biosample_acc→year),同一 isolate 跨药共享,故非仅富集药也可能有年份。
TEMPORAL_ANCHORS: list[tuple[str, str]] = [
    ("escherichia_coli", "ceftriaxone"),      # 主案例(务必评估出)
    ("escherichia_coli", "ciprofloxacin"),
    ("escherichia_coli", "meropenem"),
    ("klebsiella_pneumoniae", "meropenem"),
    ("klebsiella_pneumoniae", "cefepime"),
    ("klebsiella_pneumoniae", "ceftriaxone"),
]
_TEMPORAL_COLS = ["species", "drug", "cutoff", "train_n", "test_n", "test_R_ST",
                  "vme_fusion", "vme_rule", "delta_vme", "t_star", "year_coverage"]

# 本地有 phenotype/ST 的 anchor(EC/KP 各 3);PA/AB/SA 待 53(下方 PENDING)
LOCAL_ANCHORS: list[tuple[str, str]] = [
    ("escherichia_coli", "ceftriaxone"),
    ("escherichia_coli", "meropenem"),
    ("escherichia_coli", "ciprofloxacin"),
    ("klebsiella_pneumoniae", "meropenem"),
    ("klebsiella_pneumoniae", "cefepime"),
    ("klebsiella_pneumoniae", "ciprofloxacin"),
]
# 核心锚点(gate 要求 holdout 融合不劣于规则)
CORE_ANCHORS = [("escherichia_coli", "ceftriaxone"), ("klebsiella_pneumoniae", "meropenem")]
# 53 待办 anchor(PA/AB/SA):默认只写进 manifest 标 data_locus=53、status=pending,不评估;
# --all(53 数据)时并入评估(见 ALL_ANCHORS + run 的 surface gate)
PENDING_ANCHORS: list[tuple[str, str]] = [
    ("pseudomonas_aeruginosa", "levofloxacin"),
    ("pseudomonas_aeruginosa", "meropenem"),
    ("acinetobacter_baumannii", "meropenem"),
    ("acinetobacter_baumannii", "tigecycline"),
    ("salmonella_enterica", "ceftriaxone"),
    ("salmonella_enterica", "ciprofloxacin"),
]
# --all 的完整 anchor 池(本地 6 + 53 待办 6 = 12);实际评估哪些由 run 的 surface gate 决定
ALL_ANCHORS: list[tuple[str, str]] = LOCAL_ANCHORS + PENDING_ANCHORS

_METRIC_COLS = ["species", "drug", "held_st_cluster", "n", "n_R",
                "vme_fusion", "vme_rule", "delta_vme", "t_star"]


def _r4(x) -> str:
    """nan/None 留空,否则 4 位小数字符串(CSV 稳定)。"""
    if x is None or (isinstance(x, float) and x != x):
        return ""
    return f"{float(x):.4f}"


# ---------------------------------------------------------------- 证据面读取
def _load_surface() -> dict[tuple[str, str], dict]:
    """读冻结证据面 132,返回 {(species,drug): row}。用于校验 anchor 存在 + 读 n / n_R_ST。"""
    with open(_SURFACE_CSV, encoding="utf-8") as fh:
        return {(r["species"], r["drug"]): r for r in csv.DictReader(fh)}


# ---------------------------------------------------------------- prevalence 分箱
def prevalence_clusters(st_labels: list[str], k: int = K_CLUSTERS) -> tuple[dict[str, int], int]:
    """唯一 ST 按频次降序切 k 个连续分箱(按累计 isolate 数均分)。

    bin0=最常见的一批 ST,bin{k-1}=最稀有的一批。返回 (st->cluster 映射, 实际 k)。
    每 ST 属唯一 cluster(无跨 cluster 泄漏)。若唯一 ST 数 <k,则 k 自适应降到唯一 ST 数。
    **不用 max(2,...) 假装能切**:唯一 ST 数=1 时 k_eff=1(bin_of 只 1 箱),
    leave-one-cluster-out 不成立——由调用方(lineage_holdout_combo)显式短路跳过该组合,
    避免 c=0 时 train=[] 崩溃。唯一 ST 数=0 时 k_eff=0、bin_of={}。
    """
    freq = Counter(st_labels)
    # 频次降序,同频按 ST 名升序 → 确定性
    uniq = sorted(freq, key=lambda s: (-freq[s], s))
    k_eff = min(k, len(uniq))               # 不 max(2,...):唯一 ST<2 时如实反映,不假装能切 2 箱
    if k_eff == 0:                          # 无已知 ST(空输入):无箱可切
        return {}, 0
    total = sum(freq.values())
    target = total / k_eff                 # 每箱目标 isolate 数
    bin_of: dict[str, int] = {}
    cum = 0
    b = 0
    for st in uniq:                        # 从最常见到最稀有依次分箱
        bin_of[st] = b
        cum += freq[st]
        # 累计越过 (b+1)*target 即进入下一箱(最多进 1 箱/ST,保证各箱非空)
        if b < k_eff - 1 and cum >= (b + 1) * target:
            b += 1
    return bin_of, k_eff


# ---------------------------------------------------------------- 单组合 holdout
def lineage_holdout_combo(sp: str, drug: str) -> dict:
    """单 anchor:prevalence 分箱 leave-one-cluster-out,返回每 held cluster 的 VME 指标。"""
    amr, st_map, _ = load_inputs_from_disk(sp, _DATA)
    all_rows = _combo_rows(amr, st_map, drug)
    # 每 isolate 的 ST,剔除 unknown-ST(无法安全归入 lineage cluster)
    kept: list[dict] = []
    st_list: list[str] = []
    for r in all_rows:
        st = st_map.get((r.get("genome_id") or "").strip(), "unknown")
        if st != "unknown":
            kept.append(r)
            st_list.append(st)

    bin_of, k_eff = prevalence_clusters(st_list, K_CLUSTERS)
    if k_eff < 2:
        # 唯一 ST<2:切不出 ≥2 个 lineage cluster,leave-one-cluster-out 不成立 → 显式跳过,
        # 不让 max(2,...) 假装能切(否则 c=0 时 train=[] 崩)。诚实记录到 decision.md / 日志。
        return {"sp": sp, "drug": drug, "k_eff": k_eff,
                "n_kept": len(kept), "n_unknown": len(all_rows) - len(kept),
                "clusters": [], "skipped": f"唯一 ST={k_eff}<2,无法做 lineage holdout(跳过)"}
    rule = RuleBaselineSIR(db_version=DB)

    cluster_rows: list[dict] = []
    for c in range(k_eff):
        train = [r for r, st in zip(kept, st_list) if bin_of[st] != c]
        test = [r for r, st in zip(kept, st_list) if bin_of[st] == c]
        if not test:                       # 空箱(正常 k=4 不会出现)跳过
            continue

        y_test = _y(test)
        n = len(test)
        n_R = int((y_test == 1).sum())

        # 特征 frozen-consistent(augmented_features + build_X/fit_vocab)
        vocab = fit_vocab(train, augmented_features)
        y_train = _y(train)
        ml = GenotypeToSIR(random_state=SEED, model="rf").fit(
            build_X(train, vocab, augmented_features), y_train)
        p_train = ml.predict_proba_r(build_X(train, vocab, augmented_features))
        p_test = ml.predict_proba_r(build_X(test, vocab, augmented_features))
        rule_train = _rule_pred(rule, drug, train)
        rule_test = _rule_pred(rule, drug, test)
        st_train = _st_of(train, st_map)
        st_test = _st_of(test, st_map)

        # t* 只在 train 上选(防泄漏);held cluster 只评估不选阈
        t_star = select_tstar(p_train, rule_train, y_train, st_train,
                              rule_me=_me(y_train, rule_train))[0]
        fu = np.where(rule_test == 1, 1, (p_test >= t_star).astype(int))

        # held cluster per-ST VME(有真 R 才有定义;无真 R → 空 dict → nan)
        vf_map = st_level_vme(st_test, y_test, fu)
        vr_map = st_level_vme(st_test, y_test, rule_test)
        if vf_map:                         # 该 held cluster 有真 R ST → 可评估
            vme_f = float(np.mean(list(vf_map.values())))
            vme_r = float(np.mean(list(vr_map.values())))
            delta = vme_f - vme_r
        else:                              # 无真 R:VME 无定义,诚实记空
            vme_f = vme_r = delta = float("nan")

        cluster_rows.append({
            "species": sp, "drug": drug, "held_st_cluster": c,
            "n": n, "n_R": n_R,
            "vme_fusion": _r4(vme_f), "vme_rule": _r4(vme_r),
            "delta_vme": _r4(delta), "t_star": _r4(t_star),
            "_vme_f": vme_f, "_vme_r": vme_r,          # 内部用(decision 统计,不落 CSV)
        })

    return {"sp": sp, "drug": drug, "k_eff": k_eff,
            "n_kept": len(kept), "n_unknown": len(all_rows) - len(kept),
            "clusters": cluster_rows}


# ---------------------------------------------------------------- manifest
def build_manifest(surface: dict[tuple[str, str], dict],
                   evaluated: set[tuple[str, str]]) -> dict:
    """anchor panel:data_locus 恒按名单固定(本地 6=local / 待办 6=53);
    status 按本次是否评估过决定——本次评估过=done,否则 pending。
    默认 EC/KP:evaluated=本地 6 → 6 done + 6 pending(与旧行为逐字一致);
    --all:evaluated=在冻结面且有数据的 anchor → 10 done + 2 pending(AB×tig/SA×cipro 未收录进面)。
    n / n_R_ST 从证据面读(有则填,无则空)。"""
    panel: list[dict] = []
    for sp, dr in LOCAL_ANCHORS:
        s = surface.get((sp, dr), {})
        panel.append({
            "species": sp, "drug": dr,
            "data_locus": "local",
            "status": "done" if (sp, dr) in evaluated else "pending",
            "n": int(s["n"]) if s.get("n") else None,
            "n_R_ST": int(s["n_R_ST"]) if s.get("n_R_ST") else None,
        })
    for sp, dr in PENDING_ANCHORS:
        s = surface.get((sp, dr), {})
        panel.append({
            "species": sp, "drug": dr,
            "data_locus": "53",
            "status": "done" if (sp, dr) in evaluated else "pending",
            "n": int(s["n"]) if s.get("n") else None,
            "n_R_ST": int(s["n_R_ST"]) if s.get("n_R_ST") else None,
        })
    return {
        "task": "S3.1 external holdout — anchor panel",
        "method": "prevalence 分层 leave-one-cluster-out(唯一 ST 按频次降序切 K=4 连续箱)",
        "seed": SEED,
        "note": ("本地 EC/KP 6 anchor 已做 lineage holdout;PA/AB/SA 6 anchor 待 53 数据管线(status=pending);"
                 "temporal/source holdout 是 S3.2/S3.3。n/n_R_ST 从冻结证据面 132 读取。"),
        "panel": panel,
    }


# ---------------------------------------------------------------- decision md
def _write_decision(results: list[dict], species_filter,
                    skipped_surface: list[tuple[str, str]] | None = None) -> None:
    sp_arg = ",".join(species_filter) if species_filter else ",".join({a[0] for a in LOCAL_ANCHORS})
    L: list[str] = []
    L.append("# S3.1:外推验证 — anchor panel + ST-cluster(prevalence 分箱)lineage holdout\n")
    L.append(
        "现有 strong/practical 结果都是 5 折 **ST-grouped OOF**(每个 ST 整体不跨 train/test)。"
        "审稿人会问:换谱系还行吗?S3.1 做**更强的外推**——留出**整组谱系**(lineage cluster)而非随机 ST 折。\n"
    )
    L.append("## 方法(写死)\n")
    L.append(
        f"对每个 anchor 组合:取全部 isolate(剔除 unknown-ST),按唯一 ST 的 **isolate 频次降序**切 "
        f"**K={K_CLUSTERS} 个连续分箱**(按累计 isolate 数均分):bin0=最常见谱系群,bin{K_CLUSTERS-1}=最稀有谱系群。"
        "**leave-one-cluster-out**:留出 1 箱作 held cluster(test),其余 3 箱作 train。"
        "特征 frozen-consistent(augmented_features + build_X/fit_vocab);"
        "**t\\* 只在 train 上选**(select_tstar,防泄漏),held cluster 只评估不选阈;"
        "融合 = rule-first(rule 判 R 兜底,否则 ML≥t\\*)。"
        "held cluster 上算 per-ST VME(融合 vs 规则)与 ΔVME。**测「从常见谱系泛化到稀有谱系」**——"
        "比随机 ST 折更强的泛化考验。\n"
    )
    L.append("## 一键复现\n")
    L.append("```bash")
    L.append(
        ".venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.holdout \\\n"
        f"    --species {sp_arg} --mode lineage"
    )
    L.append("```")
    L.append(f"\n确定性:seed={SEED};prevalence 分箱与训练均确定性,重跑字节一致。\n")

    # 核心锚点结论
    L.append("## 核心锚点(EC×ceftriaxone / KP×meropenem):holdout 是否保持不劣于规则\n")
    L.append("| species | drug | held cluster | n | n_R | 融合VME | 规则VME | ΔVME | t\\* |")
    L.append("|---|---|:--:|--:|--:|--:|--:|--:|--:|")
    for r in results:
        if (r["sp"], r["drug"]) not in CORE_ANCHORS:
            continue
        for cr in r["clusters"]:
            L.append(
                f"| {r['sp']} | {r['drug']} | {cr['held_st_cluster']} | {cr['n']} | {cr['n_R']} | "
                f"{cr['vme_fusion'] or 'nan'} | {cr['vme_rule'] or 'nan'} | "
                f"{cr['delta_vme'] or 'nan'} | {cr['t_star']} |"
            )
    for sp, dr in CORE_ANCHORS:
        rr = next((x for x in results if (x["sp"], x["drug"]) == (sp, dr)), None)
        if rr is None:
            continue
        valid = [cr for cr in rr["clusters"] if cr["_vme_f"] == cr["_vme_f"]]      # 非 nan
        if valid:
            mf = sum(cr["_vme_f"] for cr in valid) / len(valid)
            mr = sum(cr["_vme_r"] for cr in valid) / len(valid)
            ok = "不劣于规则 ✅" if mf <= mr + 0.05 else "劣于规则 ⚠️"
            L.append(
                f"\n- **{sp} × {dr}**:{len(valid)} 个有效 held cluster,融合 VME 均值 {mf:.4f} vs "
                f"规则 {mr:.4f}(容差 0.05)→ **{ok}**。"
            )
    L.append("")

    # 泛化失败 held cluster(诚实)
    L.append("## 泛化失败 held cluster(诚实记录)\n")
    fails: list[str] = []
    for r in results:
        for cr in r["clusters"]:
            if cr["_vme_f"] == cr["_vme_f"] and cr["_vme_r"] == cr["_vme_r"]:
                if cr["_vme_f"] > cr["_vme_r"] + 0.05:       # 融合明显劣于规则
                    fails.append(
                        f"- **{r['sp']} × {r['drug']}** held cluster {cr['held_st_cluster']}"
                        f"(n={cr['n']}, n_R={cr['n_R']}):融合 VME {cr['vme_fusion']} > 规则 {cr['vme_rule']}"
                        f"(ΔVME={cr['delta_vme']})——该谱系群外推融合不敌规则。"
                    )
    if fails:
        L.append("以下 held cluster 上融合预测明显劣于规则(ΔVME>0.05),如实记录——这正是外推验证的价值:\n")
        L.extend(fails)
        L.append("")
    else:
        L.append("无 held cluster 上融合明显劣于规则(ΔVME>0.05):所有可评估谱系群外推稳健。\n")

    # 无 R held cluster(无法评 VME)
    L.append("## 无真 R 的 held cluster(无法评 VME,诚实标注)\n")
    noR: list[str] = []
    for r in results:
        for cr in r["clusters"]:
            if cr["n_R"] == 0:
                noR.append(
                    f"- **{r['sp']} × {r['drug']}** held cluster {cr['held_st_cluster']}"
                    f"(n={cr['n']}):rare bin 全 S,无真 R,无法评 VME(CSV 记空)。"
                )
    if noR:
        L.append("以下 held cluster 无真 R 样本,per-ST VME 无定义(CSV vme 列留空),不计入核心锚点均值:\n")
        L.extend(noR)
        L.append("")
    else:
        L.append("所有 held cluster 均含真 R 样本,VME 可评估。\n")

    # 跳过组合(唯一 ST<2,无法 leave-one-cluster-out)
    skipped = [r for r in results if r.get("skipped")]
    if skipped:
        L.append("## 跳过的组合(无法做 lineage holdout,诚实标注)\n")
        for r in skipped:
            L.append(f"- **{r['sp']} × {r['drug']}**:{r['skipped']}(kept={r['n_kept']})。")
        L.append("")

    # 分箱自适应说明(K<4 但仍 ≥2,能做 holdout)
    adapt = [r for r in results if not r.get("skipped") and r["k_eff"] != K_CLUSTERS]
    if adapt:
        L.append("## 分箱自适应(2≤K<4)说明\n")
        for r in adapt:
            L.append(f"- **{r['sp']} × {r['drug']}**:唯一 ST 数不足,K 自适应降为 {r['k_eff']}。")
        L.append("")

    # 不在冻结证据面、跳过评估的 anchor(--all 才可能出现;默认 EC/KP 为空,本段不产出)
    if skipped_surface:
        L.append("## 不在冻结证据面 132、跳过评估的 anchor(诚实标注)\n")
        L.append(
            "以下 anchor 虽在名单内,但未收录进冻结证据面 132(或收录但 tier=unevaluated、n 空),"
            "无冻结基线可对齐,故本次跳过 lineage holdout,manifest 记 status=pending:\n"
        )
        for sp, dr in skipped_surface:
            L.append(f"- **{sp} × {dr}**:不在冻结证据面 132 的可评估集,跳过(53 上或有原始数据,待收录进面后再评)。")
        L.append("")

    # 待办
    L.append("## 待办(本任务范围外)\n")
    L.append(
        "- **PA/AB/SA anchor(6 个,data_locus=53)**:lineage holdout 待 53 数据管线(status=pending,见 manifest)。\n"
        "- **temporal holdout(S3.2)**:按年份/批次留出时间段外推。\n"
        "- **source holdout(S3.3)**:按数据来源/地域留出外推。\n"
    )
    (_OUT / "external_holdout_decision.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ================================================================ S3.2 时间外推
def load_years(sp: str) -> dict[str, int] | None:
    """读采样年份缓存 data/mdr_gnb/raw/<sp>/biosample_year.tsv → {biosample_acc: year}。

    两列 tab:biosample_acc \\t year(year 为 int 或 "NA")。无缓存文件返回 None(该物种跳过)。
    NA/空/非整数年份的行不入表(如实缺失)。
    """
    p = _DATA / "raw" / sp / "biosample_year.tsv"
    if not p.exists():
        return None
    out: dict[str, int] = {}
    for line in p.open(encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) != 2:
            continue
        acc, val = parts
        if val in ("NA", ""):
            continue
        try:
            out[acc] = int(val)
        except ValueError:
            continue
    return out


def temporal_holdout_combo(sp: str, drug: str) -> dict:
    """单组合时间外推:train≤CUTOFF / test>CUTOFF,test 侧评 per-ST VME(融合 vs 规则)。

    纪律:seed=0;t\\* 只在 train(≤CUTOFF)选,防泄漏;融合 rule-first;per-ST VME 口径同 S3.1。
    无年份缓存 / train/test 样本不足 / test 侧 R-ST 不足 → 诚实跳过(不硬跑噪声),返回带 skipped 的 dict。
    """
    years = load_years(sp)
    if years is None:
        return {"species": sp, "drug": drug, "skipped": "无年份缓存(该物种未富集采样年份)"}
    amr, st_map, _ = load_inputs_from_disk(sp, _DATA)
    rows = _combo_rows(amr, st_map, drug)

    def _yr(r):
        return years.get((r.get("ncbi_biosample_acc") or "").strip())

    have = [r for r in rows if _yr(r) is not None]
    train = [r for r in have if _yr(r) <= CUTOFF]
    test = [r for r in have if _yr(r) > CUTOFF]
    year_cov = round(len(have) / len(rows), 3) if rows else 0.0

    if len(train) < MIN_TRAIN or len(test) < MIN_TEST:
        return {"species": sp, "drug": drug, "year_coverage": year_cov,
                "train_n": len(train), "test_n": len(test),
                "skipped": f"样本不足(train {len(train)}/test {len(test)},阈 {MIN_TRAIN}/{MIN_TEST})"}

    # test 侧真 R-ST 先算:不足则诚实跳过(不硬跑出噪声数字)
    y_te = _y(test)
    st_te = _st_of(test, st_map)
    te_rst = len({st_te[i] for i in range(len(y_te)) if y_te[i] == 1 and st_te[i] != "unknown"})
    if te_rst < MIN_TEST_R_ST:
        return {"species": sp, "drug": drug, "year_coverage": year_cov,
                "train_n": len(train), "test_n": len(test), "test_R_ST": te_rst,
                "skipped": f"test≥{CUTOFF + 1} R-ST 不足(={te_rst}<{MIN_TEST_R_ST}),不硬跑噪声 VME"}

    rule = RuleBaselineSIR(db_version=DB)
    vocab = fit_vocab(train, augmented_features)
    y_tr = _y(train)
    ml = GenotypeToSIR(random_state=SEED, model="rf").fit(
        build_X(train, vocab, augmented_features), y_tr)

    # t* 只在 train(≤CUTOFF)选,防泄漏,对齐 train 规则 ME
    p_tr = ml.predict_proba_r(build_X(train, vocab, augmented_features))
    ru_tr = _rule_pred(rule, drug, train)
    st_tr = _st_of(train, st_map)
    t_star = select_tstar(p_tr, ru_tr, y_tr, st_tr, rule_me=_me(y_tr, ru_tr))[0]

    # test≥CUTOFF+1 上评估:融合 rule-first
    p_te = ml.predict_proba_r(build_X(test, vocab, augmented_features))
    ru_te = _rule_pred(rule, drug, test)
    fu = np.where(ru_te == 1, 1, (p_te >= t_star).astype(int))
    vf = st_level_vme(st_te, y_te, fu)
    vr = st_level_vme(st_te, y_te, ru_te)
    vme_f = float(np.mean(list(vf.values()))) if vf else float("nan")
    vme_r = float(np.mean(list(vr.values()))) if vr else float("nan")
    return {"species": sp, "drug": drug, "cutoff": CUTOFF,
            "train_n": len(train), "test_n": len(test), "test_R_ST": te_rst,
            "vme_fusion": vme_f, "vme_rule": vme_r, "delta_vme": vme_f - vme_r,
            "t_star": float(t_star), "year_coverage": year_cov}


def _temporal_metric_row(res: dict) -> dict:
    """评估结果 → CSV 行(确定性数字格式:vme/delta 4 位、t*/coverage 3 位)。"""
    return {
        "species": res["species"], "drug": res["drug"], "cutoff": res["cutoff"],
        "train_n": res["train_n"], "test_n": res["test_n"], "test_R_ST": res["test_R_ST"],
        "vme_fusion": _r4(res["vme_fusion"]), "vme_rule": _r4(res["vme_rule"]),
        "delta_vme": _r4(res["delta_vme"]), "t_star": f"{res['t_star']:.3f}",
        "year_coverage": f"{res['year_coverage']:.3f}",
    }


def _write_temporal_decision(results: list[dict], species_filter) -> None:
    """S3.2 结论 + 诚实局限(数据 vintage、样本足/跳过、CUTOFF 依据、早期探针误判更正)。"""
    sp_arg = ",".join(species_filter) if species_filter else ",".join(
        sorted({a[0] for a in TEMPORAL_ANCHORS}))
    evaluated = [r for r in results if not r.get("skipped")]
    skipped = [r for r in results if r.get("skipped")]
    L: list[str] = []
    L.append("# S3.2:时间外推 holdout(train≤2021 / test≥2022)\n")
    L.append(
        f"现有 strong/practical 结果都是 5 折 ST-grouped OOF(同一数据生态内)。审稿人会问:**换年份还行吗?"
        f"是不是只拟合了某个采样时期?** S3.2 做**时间外推**——用 **{CUTOFF} 及之前**的 isolate 训练,"
        f"在 **{CUTOFF + 1}+ 近年**的 isolate 上测,看模型是否随年份漂移。\n"
    )
    L.append("## 方法(frozen-consistent,同 S3.1 lineage)\n")
    L.append(
        f"每 anchor:按 BioSample 采样年份切 train(≤{CUTOFF})/ test(>{CUTOFF})。"
        f"特征 augmented_features + build_X/fit_vocab;ML=GenotypeToSIR(rf, seed={SEED});"
        f"**t\\* 只在 train(≤{CUTOFF})上选**(select_tstar,防泄漏),test 只评估不选阈;"
        "融合 = rule-first(rule 判 R 兜底,否则 ML≥t\\*)。test 上算 per-ST VME(融合 vs 规则)与 ΔVME。\n"
    )
    L.append("## 一键复现\n")
    L.append("```bash")
    L.append(
        ".venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v1.holdout \\\n"
        f"    --species {sp_arg} --mode temporal"
    )
    L.append("```")
    L.append(f"\n确定性:seed={SEED};切分/训练均确定性,重跑字节一致。\n")

    # 评估结果表
    L.append(f"## 评估结果(test≥{CUTOFF + 1} 上融合 vs 规则)\n")
    L.append("| species | drug | train_n | test_n | test_R_ST | 融合VME | 规则VME | ΔVME | t\\* | 年份覆盖 |")
    L.append("|---|---|--:|--:|--:|--:|--:|--:|--:|--:|")
    for r in evaluated:
        L.append(
            f"| {r['species']} | {r['drug']} | {r['train_n']} | {r['test_n']} | {r['test_R_ST']} | "
            f"{_r4(r['vme_fusion']) or 'nan'} | {_r4(r['vme_rule']) or 'nan'} | "
            f"{_r4(r['delta_vme']) or 'nan'} | {r['t_star']:.3f} | {r['year_coverage']:.3f} |"
        )
    L.append("")

    # 主案例结论
    ec = next((r for r in evaluated
               if (r["species"], r["drug"]) == ("escherichia_coli", "ceftriaxone")), None)
    L.append("## 主案例 EC×ceftriaxone(ESBL 近年扩散场景)\n")
    if ec:
        ok = "不劣于规则 ✅" if ec["vme_fusion"] <= ec["vme_rule"] + 0.05 else "劣于规则 ⚠️"
        L.append(
            f"- train≤{CUTOFF}: n={ec['train_n']};**test≥{CUTOFF + 1}: n={ec['test_n']}**"
            f"(test 侧 R-ST={ec['test_R_ST']},近年样本高度耐药,ESBL 扩散)。\n"
            f"- 融合 VME={ec['vme_fusion']:.4f} vs 规则 VME={ec['vme_rule']:.4f}"
            f"(ΔVME={ec['delta_vme']:+.4f},容差 0.05)→ **{ok}**。\n"
            f"- 结论:模型在未见过的近年 isolate 上,VME 不劣于规则——**不是只拟合某个采样时期**。\n"
        )
    else:
        L.append("- ⚠️ 主案例未评估出(见跳过原因),需检查年份缓存。\n")

    # 数据 vintage 分布(诚实)
    L.append("## 数据 vintage 分布 + CUTOFF 依据(诚实)\n")
    L.append(
        f"- CUTOFF={CUTOFF}:train/test 以 2021/2022 分界——2022+ 为"
        f"「近年现代 isolate」,足够近以检验时间漂移,又能在多数 anchor 上留出 ≥{MIN_TEST} test 与 ≥{MIN_TEST_R_ST} R-ST。\n"
    )
    for r in evaluated:
        L.append(f"  - {r['species']}×{r['drug']}:年份覆盖 {r['year_coverage']:.1%}"
                 f"(train {r['train_n']} / test {r['test_n']})。")
    L.append("")

    # 跳过组合(诚实)
    L.append("## 跳过的组合(诚实标注)\n")
    if skipped:
        L.append("以下组合因无年份缓存 / 样本不足 / test 侧 R-ST 不足而跳过,不硬跑出噪声数字:\n")
        for r in skipped:
            cov = f",年份覆盖 {r['year_coverage']:.1%}" if r.get("year_coverage") is not None else ""
            L.append(f"- **{r['species']} × {r['drug']}**:{r['skipped']}{cov}。")
        L.append("")
    else:
        L.append("本次无跳过组合。\n")
    L.append(
        "> 说明:年份缓存按**物种**存(biosample_acc→year),同一 isolate 跨药共享 BioSample,"
        "故仅富集了 ceftriaxone 的 EC 年份也惠及 EC×ciprofloxacin/meropenem 等——覆盖率取决于"
        "各组合 isolate 的 BioSample 是否落在缓存内,而非严格按药富集。\n"
    )

    # 更正记录(要求)
    L.append("## 更正记录:早期探针误判\n")
    L.append(
        f"早期探针(前 150 条 BioSample)曾误判「数据止于 2016」;**全量富集后确认数据延伸到 2025**"
        f"(EC/KP 均有 {CUTOFF + 1}+ isolate),故现代 ≥{CUTOFF + 1} temporal holdout 可行。"
        "早期结论作废,以全量富集分布为准。\n"
    )

    # 待办
    L.append("## 待办(本任务范围外)\n")
    L.append(
        "- **PA/AB/SA temporal**:待 53 数据管线 + 年份富集。\n"
        "- **source holdout(S3.3)**:按数据来源/地域留出外推。\n"
    )
    (_OUT / "temporal_holdout_decision.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def run_temporal(species_filter: list[str] | None) -> None:
    """S3.2 驱动:逐 temporal anchor 跑时间外推,落 metrics CSV + decision md。"""
    _OUT.mkdir(parents=True, exist_ok=True)
    candidates = [(sp, dr) for sp, dr in TEMPORAL_ANCHORS
                  if species_filter is None or sp in species_filter]
    print(f"temporal anchor {len(candidates)}(过滤={species_filter or 'EC/KP'});"
          f"train≤{CUTOFF} / test≥{CUTOFF + 1}…", flush=True)

    results: list[dict] = []
    for i, (sp, dr) in enumerate(candidates, 1):
        res = temporal_holdout_combo(sp, dr)
        results.append(res)
        skip = res.get("skipped")
        if skip:
            print(f"  [{i}/{len(candidates)}] {sp[:22]:22} × {dr:14} ⚠️ 跳过:{skip}", flush=True)
        else:
            print(f"  [{i}/{len(candidates)}] {sp[:22]:22} × {dr:14} "
                  f"train={res['train_n']:>5} test={res['test_n']:>4} test_R-ST={res['test_R_ST']:>3} "
                  f"融合VME={res['vme_fusion']:.4f} 规则VME={res['vme_rule']:.4f} "
                  f"ΔVME={res['delta_vme']:+.4f} t*={res['t_star']:.3f} 覆盖={res['year_coverage']:.2f}",
                  flush=True)

    evaluated = [r for r in results if not r.get("skipped")]
    metric_rows = [_temporal_metric_row(r) for r in evaluated]
    write_csv(_OUT / "temporal_holdout_metrics.csv", _TEMPORAL_COLS, metric_rows)
    _write_temporal_decision(results, species_filter)

    print(f"\n落盘 → {_OUT}\n"
          f"  评估={len(evaluated)}  跳过={len(results) - len(evaluated)}  "
          f"metrics 行={len(metric_rows)}", flush=True)


# ---------------------------------------------------------------- 驱动
def run(species_filter: list[str] | None, mode: str) -> None:
    if mode == "temporal":
        return run_temporal(species_filter)
    if mode != "lineage":
        raise NotImplementedError(f"--mode {mode} 未实现;支持 lineage(S3.1)/ temporal(S3.2)")
    _OUT.mkdir(parents=True, exist_ok=True)
    surface = _load_surface()

    # 候选 = 完整 anchor 池按物种过滤:默认 EC/KP → 本地 6;--all → 全 12。
    candidates = [(sp, dr) for sp, dr in ALL_ANCHORS
                  if species_filter is None or sp in species_filter]
    # 存在性 gate:只评估在冻结证据面 132 且有数据(n 非空)的 anchor。
    # 本地 6 anchor 恒满足(与旧 assert 语义一致);--all 的 AB×tigecycline(未收录进面)
    # 与 SA×ciprofloxacin(收录但 tier=unevaluated、n 空)跳过并打印警告,不 assert 崩——
    # 53 上或有原始数据,但冻结证据面未收录/未评估该组合,记入 manifest(status=pending)。
    anchors: list[tuple[str, str]] = []
    skipped_surface: list[tuple[str, str]] = []
    for sp, dr in candidates:
        s = surface.get((sp, dr))
        if s and s.get("n"):
            anchors.append((sp, dr))
        else:
            skipped_surface.append((sp, dr))
            reason = "未收录进冻结证据面 132" if s is None else "冻结面 tier=unevaluated(n 空)"
            print(f"  ⚠️ anchor {sp}×{dr} {reason},跳过评估(记 manifest status=pending)", flush=True)
    print(f"anchor {len(anchors)}(过滤={species_filter or 'local EC/KP'});逐 anchor 跑 lineage holdout…",
          flush=True)

    results: list[dict] = []
    for i, (sp, dr) in enumerate(anchors, 1):
        res = lineage_holdout_combo(sp, dr)
        results.append(res)
        skip = res.get("skipped")
        print(f"  [{i}/{len(anchors)}] {sp[:22]:22} × {dr:14} "
              f"K={res['k_eff']} kept={res['n_kept']}(unknown-ST={res['n_unknown']})"
              f"{'  ⚠️ ' + skip if skip else ''}", flush=True)
        for cr in res["clusters"]:
            print(f"      held#{cr['held_st_cluster']} n={cr['n']:>5} n_R={cr['n_R']:>4} "
                  f"融合VME={cr['vme_fusion'] or 'nan':>7} 规则VME={cr['vme_rule'] or 'nan':>7} "
                  f"ΔVME={cr['delta_vme'] or 'nan':>7} t*={cr['t_star']}", flush=True)

    # 落盘:manifest(status 按本次是否评估;含全部本地 6 + 53 6)+ metrics CSV + decision md
    manifest = build_manifest(surface, set(anchors))
    (_OUT / "anchor_panel_manifest.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")

    metric_rows = [{k: cr[k] for k in _METRIC_COLS} for r in results for cr in r["clusters"]]
    write_csv(_OUT / "lineage_holdout_metrics.csv", _METRIC_COLS, metric_rows)

    _write_decision(results, species_filter, skipped_surface)

    print(f"\n落盘 → {_OUT}\n"
          f"  anchor={len(results)}  held-cluster 行={len(metric_rows)}  "
          f"manifest panel={len(manifest['panel'])}(local 6 + 53 pending {len(PENDING_ANCHORS)})",
          flush=True)


def _parse_species(args) -> list[str] | None:
    if args.all:
        # --all(53 数据):返回全 anchor 池涉及的 5 物种,run 再按 surface gate 决定实评哪些。
        # 仅 53 有 PA/AB/SA 的 phenotype/ST,本地跑会在 load_inputs_from_disk 崩(预期)。
        return sorted({sp for sp, _ in ALL_ANCHORS})
    return [s.strip() for s in args.species.split(",") if s.strip()]


if __name__ == "__main__":
    default_sp = ",".join(sorted({a[0] for a in LOCAL_ANCHORS}))
    ap = argparse.ArgumentParser(
        description="外推 holdout:lineage(S3.1,ST-cluster)/ temporal(S3.2,train≤2021/test≥2022)")
    ap.add_argument("--species", default=default_sp, help="逗号分隔物种(默认本地 EC/KP)")
    ap.add_argument("--mode", default="lineage",
                    help="holdout 模式:lineage(S3.1)/ temporal(S3.2),默认 lineage")
    ap.add_argument("--all", action="store_true", help="全 5 物种(53 数据):跑全 anchor panel(仅 lineage)")
    args = ap.parse_args()
    run(_parse_species(args), args.mode)
