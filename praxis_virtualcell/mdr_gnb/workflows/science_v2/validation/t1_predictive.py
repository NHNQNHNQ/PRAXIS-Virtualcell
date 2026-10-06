"""T1A:SIR 预测正确性双轨验证(两轨都诚实标 stratum,互不冒充)。

轨A(sir_face_validity):curated 已知株跑**部署平台**,验证 ①服务链通 ②输出合理(强机制→必 R)
  ③训练集记忆正确。指标显式标 stratum="train_set_optimistic"——部署 artifact 训过**全量**数据,
  真实株跑平台=训练集乐观估计,**不作泛化门槛**,只作 serving+合理性 gate。
轨B(sir_generalization):复用已有留出——G2R evidence_tiers 的 strong combos 的留出 VME/AUC
  (run_g2r_evidence_sweep 产的真留出数字)。**泛化门槛下在这一轨**。不重训、不编数据。

保真:golden 的 amr_profile 用 base 名(token 剥 =modifier),与部署模型训练特征化
(augmented_features:gene=/mut=/mech=)经服务端 _amr_to_X 逐位一致 —— 由 verify_amr_fidelity.py
(及 tests/.../test_amr_fidelity.py)真跑真断言,一键可复现,故轨A accuracy 有意义。

局限(诚实标注,同步进 t1a_sir.json 的 limitations 字段):
  - 轨A 面值仅覆盖 EC/KP 两物种 —— 本地仅这两个物种有 ncbi_amr_phenotypes.tsv
    (PA/AB/SE 无本地 tsv,不纳入);轨A 是训练集乐观估计,不作泛化门槛。
  - 轨B 泛化基于 evidence_tiers 全 26 strong combos,覆盖 5 物种(含 PA/AB/SE),
    是留出真泛化数字,泛化门槛下在此轨。
"""
from __future__ import annotations

import math
from pathlib import Path
from statistics import median
from typing import Any

import pandas as pd
import yaml

from praxis_virtualcell.mdr_gnb.coordinator.fusion import load_evidence_tiers
from praxis_virtualcell.mdr_gnb.workflows.science_v2.validation import harness
from praxis_virtualcell.mdr_gnb.workflows.science_v2.validation.build_golden_sir import (
    ANCHORS as _GOLDEN_ANCHORS,
)

# 仓库根(本文件 parents:[0]=validation [1]=science_v2 [2]=workflows [3]=mdr_gnb
# [4]=praxis_virtualcell [5]=仓库根;与 build_golden_sir.py / harness.py 同口径,实测核对)。
_REPO_ROOT = Path(__file__).resolve().parents[5]
_GOLDEN_PATH = _REPO_ROOT / "data" / "mdr_gnb" / "golden" / "golden_set_sir.yaml"

# T1A 局限(诚实标注,写入报告 limitations 字段)。
LIMITATIONS: dict[str, str] = {
    "face_validity_species_coverage": (
        "轨A 面值仅覆盖 escherichia_coli / klebsiella_pneumoniae 两物种,"
        "因 pseudomonas_aeruginosa / acinetobacter_baumannii / salmonella_enterica "
        "本地无 ncbi_amr_phenotypes.tsv;且轨A 为训练集乐观估计,不作泛化门槛。"
    ),
    "generalization_species_coverage": (
        "轨B 泛化基于 evidence_tiers 全 26 strong combos,覆盖 5 物种(含 PA/AB/SE),"
        "为留出真泛化数字;泛化门槛下在此轨。"
    ),
    "fidelity_reproducible": (
        "轨A amr_profile(base 名)与训练特征化逐位一致,由 verify_amr_fidelity.py "
        "一键复现(N/N 逐位相等),不写死具体数字。"
    ),
}

# 强机制锚点(教科书级基因→表型,必出 R)。合理性哨兵。
# 单一定义源:build_golden_sir.ANCHORS(golden 里 curated_anchor 行的生成源)—— 从它派生,
# 避免锚点字面量两份硬编码漂移(expect = 该锚点在 golden 里的 true_sir)。
SIR_ANCHORS: list[dict[str, Any]] = [
    {"species": a["species"], "amr_profile": a["amr_profile"], "drug": a["drug"],
     "drug_class": a["drug_class"], "expect": a["true_sir"]}
    for a in _GOLDEN_ANCHORS
]

# 轨B 泛化门槛(不随本任务调整;fail 如实记录为发现)。
SIR_GEN_GATES = {"vme_le_0.10": 0.10, "auc_ge_0.85": 0.85}


def _sir_query(species: str, amr_profile: dict, drug: str, drug_class: str) -> dict[str, Any]:
    """构造 SIR 平台查询(harness.run_query 的 raw)。"""
    return {
        "species": species,
        "amr_profile": amr_profile,
        "drug_panel": [{"drug": drug, "drug_class": drug_class}],
        "requested_outputs": ["SIR"],
    }


def _run_anchors() -> tuple[list[dict[str, Any]], bool]:
    """跑强机制锚点(顺序按 SIR_ANCHORS 原序,确定性)。返回结果表 + 是否全出 R。"""
    results = []
    for a in SIR_ANCHORS:
        out = harness.run_query(_sir_query(
            a["species"], a["amr_profile"], a["drug"], a["drug_class"]))
        results.append({
            "species": a["species"], "drug": a["drug"], "expect": a["expect"],
            "got": out["sir"], "abstained": bool(out["abstained"]),
        })
    all_r = all(x["got"] == "R" and not x["abstained"] for x in results)
    return results, all_r


def sir_face_validity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """轨A 面值:golden 真实株跑部署平台 → classification_metrics + 锚点合理性。

    stratum=train_set_optimistic(部署 artifact 见过全量,此为训练集乐观估计,非泛化)。
    确定性:遍历顺序严格按 rows 原序,不引入 set/dict 无序。
    """
    y_true: list = []
    y_pred: list = []
    abstained: list = []
    for r in rows:
        out = harness.run_query(_sir_query(
            r["species"], r.get("amr_profile") or {}, r["drug"], r.get("drug_class", "")))
        y_true.append(r["true_sir"])
        y_pred.append(out["sir"])
        abstained.append(bool(out["abstained"]))
    m = harness.classification_metrics(y_true, y_pred, abstained)

    anchors, anchors_all_R = _run_anchors()
    return {
        "stratum": "train_set_optimistic",
        "metrics": m,
        "anchors": anchors,
        "gates": {
            "anchors_all_R": anchors_all_R,
            "coverage_ge_0.70": m["coverage"] >= 0.70,
        },
        "note": ("部署模型见过全量,此为训练集乐观估计,非泛化;"
                 "泛化见 sir_generalization()"),
    }


def sir_generalization(tiers: dict | None = None) -> dict[str, Any]:
    """轨B 泛化:evidence_tiers 的 strong combos 留出 VME/AUC(G2R sweep 真留出)。

    中位数用固定排序,None 先滤;门槛不劣化(SIR_GEN_GATES),fail 如实记录。
    """
    tiers = tiers if tiers is not None else load_evidence_tiers()
    strong = [v for v in tiers.values() if v.get("tier") == "strong"]
    vmes = sorted(v["per_st_vme_fusion"] for v in strong
                  if v.get("per_st_vme_fusion") is not None)
    aucs = sorted(v["auc_R"] for v in strong if v.get("auc_R") is not None)
    med_vme = round(median(vmes), 4) if vmes else None
    med_auc = round(median(aucs), 4) if aucs else None
    return {
        "stratum": "held_out",
        "source": "evidence_tiers.yaml",
        "n_strong": len(strong),
        "n_vme": len(vmes),
        "n_auc": len(aucs),
        "median_vme_fusion": med_vme,
        "median_auc_R": med_auc,
        "gates": {
            "vme_le_0.10": (med_vme is not None and med_vme <= SIR_GEN_GATES["vme_le_0.10"]),
            "auc_ge_0.85": (med_auc is not None and med_auc >= SIR_GEN_GATES["auc_ge_0.85"]),
        },
        "note": ("留出泛化数字来自 G2R evidence_tiers(per-ST VME / AUC_R),非训练集;"
                 "门槛不随任务调整,fail 如实记录为发现"),
    }


def build_report(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """确定性组装 T1A 报告 payload(含 limitations),供 write_report 落盘、可一键复现。"""
    if rows is None:
        rows = yaml.safe_load(_GOLDEN_PATH.read_text(encoding="utf-8"))
    return {
        "face_validity": sir_face_validity(rows),
        "generalization": sir_generalization(),
        "limitations": LIMITATIONS,
    }


# ===========================================================================
# T1B:小分子活性(sm_activity)预测正确性双轨。同 T1A 风格,两轨都诚实标 stratum。
#
# 轨A(compound_face_validity):curated 已知药跑**部署平台**(SmallMoleculeModel
#   artifact 在全量 27175 化合物上训过),验证服务链通 + 输出合理(锚点环丙沙星→低 MIC),
#   regression_metrics,显式标 stratum="train_set_optimistic",不作泛化门槛。
# 轨B(compound_generalization):复用已有 scaffold-OOF 留出
#   (reports/antibacterial/mdr_gnb/science_v2/qsar_baseline/qsar_per_compound.parquet,每化合物由未见其骨架的折
#   预测=真留出),真读 parquet 用 harness.regression_metrics 复算 R²(不写死数字)。
#   泛化门槛下在此轨。不重训、不编数据。
# ===========================================================================

_GOLDEN_COMPOUNDS_PATH = _REPO_ROOT / "data" / "mdr_gnb" / "golden" / "golden_compounds.csv"
_QSAR_OOF_PATH = (_REPO_ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v2" / "qsar_baseline"
                  / "qsar_per_compound.parquet")

# 轨B 泛化门槛(不随本任务调整;fail 如实记录为发现)。
COMPOUND_GEN_GATES: dict[str, float] = {"r2_ge_0.40": 0.40, "mae_le_0.75": 0.75}

# golden_compounds.csv 全量来自 EC 训练 parquet,固定单一物种(见 build_golden_compounds.py)。
_COMPOUND_SPECIES = "escherichia_coli"


def _compound_query(smiles: str) -> dict[str, Any]:
    """构造小分子活性平台查询(harness.run_query 的 raw)。drug 名用 smiles 占位(逐条唯一)。"""
    return {
        "species": _COMPOUND_SPECIES,
        "smiles": smiles,
        "drug_panel": [{"drug": smiles, "drug_class": "novel_compound"}],
        "requested_outputs": ["activity"],
    }


def compound_face_validity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """轨A 面值:golden 已知药跑**部署平台** → regression_metrics + 环丙沙星锚点合理性。

    只对 label_source 有效(非 None/空/"none")且有 smiles、mic_ug_ml 的行评分——
    label_source="none" 的行(训练集里匹配不到、无可靠来源)诚实排除,不进分母。
    stratum=train_set_optimistic(部署 artifact 训过全量 27175 化合物,此为训练集乐观估计,
    非泛化)。确定性:遍历顺序严格按 rows 原序,不引入 set/dict 无序。
    """
    y_true: list[float] = []
    y_pred: list[float | None] = []
    abstained: list[bool] = []
    cipro_log10: float | None = None
    for r in rows:
        smiles = (r.get("smiles") or "").strip()
        label_source = (r.get("label_source") or "").strip().lower()
        mic = r.get("mic_ug_ml")
        if not smiles or label_source in ("", "none") or mic in (None, ""):
            continue
        out = harness.run_query(_compound_query(smiles))
        pred = out["activity"]["log10_mic"] if out["activity"] else None
        y_true.append(math.log10(float(mic)))
        y_pred.append(pred)
        abstained.append(bool(out["abstained"]))
        if (r.get("name") or "").strip().lower() == "ciprofloxacin" and pred is not None:
            cipro_log10 = pred

    m = harness.regression_metrics(y_true, y_pred, abstained)
    cipro_low = bool(cipro_log10 is not None and cipro_log10 < 0)
    return {
        "stratum": "train_set_optimistic",
        "metrics": m,
        "anchors": {
            "ciprofloxacin_log10_lt_0": cipro_low,
        },
        # 面值 gate 只作 serving + 合理性哨兵(不作泛化门槛,保持 train_set_optimistic 语义);
        # 与 sir_face_validity 对称,供 T8 战役裁决统一消费各轨 gates。
        "gates": {
            "ciprofloxacin_anchor_low": cipro_low,
            "coverage_ge_0.70": m["coverage"] >= 0.70,
        },
        "note": ("部署模型见过训练化合物,训练集乐观估计;泛化见 compound_generalization()"),
    }


def compound_generalization() -> dict[str, Any]:
    """轨B 泛化:scaffold-OOF 留出(每化合物由未见其骨架的折预测,真留出非训练集)。

    真读 qsar_per_compound.parquet 用 harness.regression_metrics 复算(不写死数字)。
    门槛不随任务调整,fail 如实记录为发现。
    """
    df = pd.read_parquet(_QSAR_OOF_PATH)
    m = harness.regression_metrics(list(df["log10_mic_true"]), list(df["log10_mic_pred"]))
    r2, mae = m["r2"], m["mae"]
    return {
        "stratum": "held_out",
        # 相对路径(跨机器确定性,与 sir_generalization 同口径;绝对路径会污染报告)。
        "source": str(_QSAR_OOF_PATH.relative_to(_REPO_ROOT)),
        "n": len(df),
        "metrics": m,
        "gates": {
            "r2_ge_0.40": bool(r2 is not None and r2 >= COMPOUND_GEN_GATES["r2_ge_0.40"]),
            "mae_le_0.75": bool(mae is not None and mae <= COMPOUND_GEN_GATES["mae_le_0.75"]),
        },
        "note": ("留出泛化数字来自 scaffold-OOF(每化合物由未见其骨架的折预测),非训练集;"
                 "门槛不随任务调整,fail 如实记录为发现"),
    }


def build_compound_report(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """确定性组装 T1B 报告 payload,供 write_report 落盘、可一键复现。"""
    if rows is None:
        rows = harness.load_golden(
            _GOLDEN_COMPOUNDS_PATH,
            required=["name", "smiles", "mic_ug_ml", "label_source", "doi_or_source",
                      "in_training"],
        )
    return {
        "face_validity": compound_face_validity(rows),
        "generalization": compound_generalization(),
    }


# ===========================================================================
# T1C:抗菌肽活性(peptide_activity)预测正确性双轨。同 T1A/T1B 风格,两轨都诚实标 stratum。
#
# 轨A(peptide_face_validity):curated 已知 AMP 跑**部署平台**(PeptideActivityModel
#   artifact 在全量 774 条 DBAASP EC 肽上训过),验证服务链通 + 输出合理(锚点 Magainin-2→
#   MIC 落在可信范围),regression_metrics,显式标 stratum="train_set_optimistic",不作泛化门槛。
# 轨B(peptide_generalization):复用已有序列相似度连通分量-OOF 留出
#   (reports/antibacterial/mdr_gnb/science_v2/peptide_baseline/peptide_per_seq.parquet,每条肽由未见其相似簇的折
#   预测=真留出),真读 parquet 用 harness.regression_metrics 复算 R²(不写死数字)。
#   泛化门槛下在此轨,诚实放宽(对齐肽偏弱现状,不假装强)。不重训、不编数据。
# ===========================================================================

_GOLDEN_PEPTIDES_PATH = _REPO_ROOT / "data" / "mdr_gnb" / "golden" / "golden_peptides.csv"
_PEPTIDE_OOF_PATH = (_REPO_ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v2" / "peptide_baseline"
                     / "peptide_per_seq.parquet")

# 轨B 泛化门槛(诚实放宽,对齐肽偏弱现状;不随本任务调整;fail 如实记录为发现)。
PEPTIDE_GEN_GATES: dict[str, float] = {"r2_ge_0.20": 0.20, "mae_le_0.90": 0.90}

# golden_peptides.csv 全量来自 EC 训练 parquet,固定单一物种(见 build_golden_peptides.py)。
_PEPTIDE_SPECIES = "escherichia_coli"


def _peptide_query(sequence: str) -> dict[str, Any]:
    """构造肽活性平台查询(harness.run_query 的 raw)。drug 名用 sequence 占位(逐条唯一)。"""
    return {
        "species": _PEPTIDE_SPECIES,
        "sequence": sequence,
        "drug_panel": [{"drug": sequence, "drug_class": "antimicrobial_peptide"}],
        "requested_outputs": ["peptide_activity"],
    }


def peptide_face_validity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """轨A 面值:golden 已知 AMP 跑**部署平台** → regression_metrics + Magainin-2 锚点合理性。

    只对 label_source 有效(非 None/空/"none")且有 sequence、mic_um 的行评分——
    label_source="none" 的行(训练集里匹配不到、无可靠来源)诚实排除,不进分母。
    stratum=train_set_optimistic(部署 artifact 训过全量 774 条肽,此为训练集乐观估计,
    非泛化)。确定性:遍历顺序严格按 rows 原序,不引入 set/dict 无序。
    """
    y_true: list[float] = []
    y_pred: list[float | None] = []
    abstained: list[bool] = []
    magainin2_log10: float | None = None
    for r in rows:
        sequence = (r.get("sequence") or "").strip()
        label_source = (r.get("label_source") or "").strip().lower()
        mic = r.get("mic_um")
        if not sequence or label_source in ("", "none") or mic in (None, ""):
            continue
        out = harness.run_query(_peptide_query(sequence))
        pred = out["peptide_activity"]["log10_mic"] if out["peptide_activity"] else None
        y_true.append(math.log10(float(mic)))
        y_pred.append(pred)
        abstained.append(bool(out["abstained"]))
        if (r.get("name") or "").strip().lower() == "magainin_2" and pred is not None:
            magainin2_log10 = pred

    m = harness.regression_metrics(y_true, y_pred, abstained)
    magainin2_in_range = bool(
        magainin2_log10 is not None and 1 < magainin2_log10 < 2)
    return {
        "stratum": "train_set_optimistic",
        "metrics": m,
        "anchors": {
            "magainin2_log10_in_1_2": magainin2_in_range,
        },
        # 面值 gate 只作 serving + 合理性哨兵(不作泛化门槛,保持 train_set_optimistic 语义);
        # 与 sir_face_validity / compound_face_validity 对称,供 T8 战役裁决统一消费各轨 gates。
        "gates": {
            "magainin2_anchor_in_range": magainin2_in_range,
            "coverage_ge_0.70": m["coverage"] >= 0.70,
        },
        "note": ("部署模型见过训练肽,训练集乐观估计;泛化见 peptide_generalization()"),
    }


def peptide_generalization() -> dict[str, Any]:
    """轨B 泛化:序列相似度连通分量-OOF 留出(每条肽由未见其相似簇的折预测,真留出非训练集)。

    真读 peptide_per_seq.parquet 用 harness.regression_metrics 复算(不写死数字)。
    门槛诚实放宽(对齐肽偏弱现状);fail 如实记录为发现。
    """
    df = pd.read_parquet(_PEPTIDE_OOF_PATH)
    m = harness.regression_metrics(list(df["log10_mic_true"]), list(df["log10_mic_pred"]))
    r2, mae = m["r2"], m["mae"]
    return {
        "stratum": "held_out",
        # 相对路径(跨机器确定性,与 sir_generalization/compound_generalization 同口径;
        # 绝对路径会污染报告)。
        "source": str(_PEPTIDE_OOF_PATH.relative_to(_REPO_ROOT)),
        "n": len(df),
        "metrics": m,
        "gates": {
            "r2_ge_0.20": bool(r2 is not None and r2 >= PEPTIDE_GEN_GATES["r2_ge_0.20"]),
            "mae_le_0.90": bool(mae is not None and mae <= PEPTIDE_GEN_GATES["mae_le_0.90"]),
        },
        "note": ("留出泛化数字来自序列相似度连通分量-OOF(每条肽由未见其相似簇的折预测),"
                 "非训练集;门槛诚实放宽(对齐肽偏弱现状,不假装强);"
                 "fail 如实记录为发现"),
    }


def build_peptide_report(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """确定性组装 T1C 报告 payload,供 write_report 落盘、可一键复现。"""
    if rows is None:
        rows = harness.load_golden(
            _GOLDEN_PEPTIDES_PATH,
            required=["name", "sequence", "mic_um", "label_source", "doi_or_source",
                      "in_training"],
        )
    return {
        "face_validity": peptide_face_validity(rows),
        "generalization": peptide_generalization(),
    }


if __name__ == "__main__":
    payload = build_report()
    p = harness.write_report("t1a_sir", payload)
    print(f"t1a_sir 报告写入 {p}")
    fv, gen = payload["face_validity"], payload["generalization"]
    print(f"  轨A: acc={fv['metrics']['accuracy']:.4f} VME={fv['metrics']['very_major_error']} "
          f"cov={fv['metrics']['coverage']} anchors_all_R={fv['gates']['anchors_all_R']}")
    print(f"  轨B: n_strong={gen['n_strong']} medVME={gen['median_vme_fusion']} "
          f"medAUC={gen['median_auc_R']} gates={gen['gates']}")

    cpayload = build_compound_report()
    cp = harness.write_report("t1b_compounds", cpayload)
    print(f"t1b_compounds 报告写入 {cp}")
    cfv, cgen = cpayload["face_validity"], cpayload["generalization"]
    print(f"  轨A: n_scored={cfv['metrics']['n_scored']} r2={cfv['metrics']['r2']} "
          f"mae={cfv['metrics']['mae']} cov={cfv['metrics']['coverage']} "
          f"cipro_anchor={cfv['anchors']['ciprofloxacin_log10_lt_0']}")
    print(f"  轨B: n={cgen['n']} r2={cgen['metrics']['r2']:.4f} "
          f"mae={cgen['metrics']['mae']:.4f} gates={cgen['gates']}")

    ppayload = build_peptide_report()
    pp = harness.write_report("t1c_peptides", ppayload)
    print(f"t1c_peptides 报告写入 {pp}")
    pfv, pgen = ppayload["face_validity"], ppayload["generalization"]
    print(f"  轨A: n_scored={pfv['metrics']['n_scored']} r2={pfv['metrics']['r2']} "
          f"mae={pfv['metrics']['mae']} cov={pfv['metrics']['coverage']} "
          f"magainin2_anchor={pfv['anchors']['magainin2_log10_in_1_2']}")
    print(f"  轨B: n={pgen['n']} r2={pgen['metrics']['r2']:.4f} "
          f"mae={pgen['metrics']['mae']:.4f} gates={pgen['gates']}")
