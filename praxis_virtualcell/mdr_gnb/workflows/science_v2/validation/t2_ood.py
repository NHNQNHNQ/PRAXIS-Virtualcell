"""T2:OOD(超出训练分布)输入必须 fail-closed 弃权,绝不出具体 MIC/SIR。

平台核心卖点验证:无需真实标签,只断言系统在"看不懂"的输入前诚实弃权,不胡编数字。

--- 小分子/肽 OOD(实跑探明,见 test_t2_ood.py 顶部注释同款说明)---------------------
sm_activity_model / peptide_activity_model 内置 OOD 判据:对训练集最大 Tanimoto(化合物)
/ 最大 k-mer Jaccard(肽)低于阈值(0.30)→ is_ood=True → fail-closed abstain
(见 predictors/default_registry.py _sm_activity_predict / _peptide_activity_predict)。

实跑核对:
  - 甲烷/乙烷/苯:结构过简单,离 ChEMBL 27175 训练化学空间远 → 真 OOD,abstain。
  - 咖啡因(max_tanimoto≈0.57)/ 聚乙烯片段 C16(max_tanimoto≈0.62):**不是**真 OOD——
    高于阈值,训练集里有相近骨架(训练集覆盖广),平台合理给出 MIC,非 bug。诚实排除出
    must-abstain 集,放进 NEAR_TRAINING_DIST_SMILES 单独记录(测试断言其"不弃权"而非"弃权")。
  - polyA/polyG/polyP 三条均聚肽:序列复杂度过低,离 DBAASP 774 条训练肽序列空间远 → 真
    OOD,全部 abstain。

--- SIR 侧(核心输入充分性契约)---------------------------------------------------
genotype_to_sir 的 AMR 输入不是“未检出即敏感”的证据。每个被选中的 SIR artifact 必须在
amr_profile 中找到至少一个值为真的、可映射到该 artifact 特征词表的 AMR 特征；空 profile 或
纯词表外 profile 都不能被转换成全零向量后当作 S（非 R）预测。它们必须 core hard-abstain，
并带机器原因 `amr_profile_no_recognized_features`。

另一类 fail-closed 是路由后没有任何成功预测器（未知物种、乱格式、或已知物种但该药没有
artifact）：报告必须 `abstained=True`、`sir=None`、`prediction_available=False`，并带
`no_successful_predictor`。T2 将这两类分别留档，避免以后把“输入不足”误报成“已预测敏感”。
"""
from __future__ import annotations

from typing import Any

from praxis_virtualcell.mdr_gnb.workflows.science_v2.validation import harness

# ===========================================================================
# 小分子 OOD
# ===========================================================================

_COMPOUND_SPECIES = "escherichia_coli"

# 真 OOD(实跑确认 is_ood=True → abstain,MIC=None)
OOD_SMILES: dict[str, str] = {
    "甲烷": "C",
    "乙烷": "CC",
    "苯": "c1ccccc1",
}
# 近训练分布(实跑确认 max_tanimoto 高于 OOD 阈值 0.30,平台正常给出 MIC,非 bug)
NEAR_TRAINING_DIST_SMILES: dict[str, str] = {
    "咖啡因": "Cn1cnc2c1c(=O)n(C)c(=O)n2C",
    "聚乙烯片段": "CCCCCCCCCCCCCCCC",
}


def _compound_query(smiles: str) -> dict[str, Any]:
    return {
        "species": _COMPOUND_SPECIES,
        "smiles": smiles,
        "drug_panel": [{"drug": smiles, "drug_class": "novel_compound"}],
        "requested_outputs": ["activity"],
    }


def check_compound_ood(smiles: str) -> dict[str, Any]:
    """跑一条小分子 SMILES 的活性查询,返回 harness.run_query 扁平 dict。"""
    return harness.run_query(_compound_query(smiles))


# ===========================================================================
# 肽 OOD
# ===========================================================================

_PEPTIDE_SPECIES = "escherichia_coli"

# 真 OOD(实跑确认三条均 is_ood=True → abstain)
OOD_PEPTIDES: dict[str, str] = {
    "polyA": "A" * 18,
    "polyG": "G" * 16,
    "polyP": "P" * 16,
}


def _peptide_query(sequence: str) -> dict[str, Any]:
    return {
        "species": _PEPTIDE_SPECIES,
        "sequence": sequence,
        "drug_panel": [{"drug": sequence, "drug_class": "antimicrobial_peptide"}],
        "requested_outputs": ["peptide_activity"],
    }


def check_peptide_ood(sequence: str) -> dict[str, Any]:
    """跑一条肽序列的活性查询,返回 harness.run_query 扁平 dict。"""
    return harness.run_query(_peptide_query(sequence))


# ===========================================================================
# SIR 乱格式/未知物种(实跑确认应 fail-closed)
# ===========================================================================


def _sir_query(species: str, amr_profile: dict, drug: str, drug_class: str) -> dict[str, Any]:
    return {
        "species": species,
        "amr_profile": amr_profile,
        "drug_panel": [{"drug": drug, "drug_class": drug_class}],
        "requested_outputs": ["SIR"],
    }


# 确定应 fail-closed 的 SIR 案例(实跑核对:sir=None、prediction_available=False)。
SIR_MALFORMED_QUERIES: dict[str, dict[str, Any]] = {
    "未知物种": _sir_query("martian_bug", {"blaKPC": True}, "meropenem", "carbapenems"),
    "全空乱格式": _sir_query("", {}, "", ""),
    "已知物种_药无训练artifact": _sir_query(
        "escherichia_coli", {"blaKPC": True}, "totally_fake_drug_zzz", "carbapenems"),
}


def sir_malformed_cases() -> list[dict[str, Any]]:
    """跑 SIR_MALFORMED_QUERIES,返回 harness.run_query 结果列表(顺序固定,确定性)。"""
    return [harness.run_query(q) for q in SIR_MALFORMED_QUERIES.values()]


# 已知物种但输入为空/无关:不可把全零特征向量解释成“敏感”,必须 fail-closed。
SIR_INSUFFICIENT_PROFILE_QUERIES: dict[str, dict[str, Any]] = {
    "EC空基因型": _sir_query("escherichia_coli", {}, "meropenem", "carbapenems"),
    "EC只有无关基因": _sir_query(
        "escherichia_coli", {"irrelevant_gene_xyz": True}, "meropenem", "carbapenems"),
}


def sir_insufficient_profile_cases() -> list[dict[str, Any]]:
    """跑输入不足 SIR 案例；必须带 amr_profile_no_recognized_features 弃权。"""
    return [harness.run_query(q) for q in SIR_INSUFFICIENT_PROFILE_QUERIES.values()]


# ===========================================================================
# 汇总套件(供报告 + T8 战役裁决消费)
# ===========================================================================


def run_ood_suite() -> dict[str, Any]:
    """跑全部真 OOD 化合物 + 真 OOD 肽,统计弃权/泄漏(未弃权却出了具体 MIC)。

    泄漏 = 红线:任一真 OOD 输入出了具体 MIC 即严重发现,标进 leaks。
    同时把近训练分布的化合物结果也跑一遍并列出(供报告诚实说明"这不是泄漏,是训练集覆盖")。
    确定性:遍历顺序严格按 dict 定义原序。
    """
    compound_results = []
    for name, smi in OOD_SMILES.items():
        res = check_compound_ood(smi)
        compound_results.append({
            "name": name, "smiles": smi,
            "abstained": bool(res["abstained"]), "activity": res["activity"],
        })
    peptide_results = []
    for name, seq in OOD_PEPTIDES.items():
        res = check_peptide_ood(seq)
        peptide_results.append({
            "name": name, "sequence": seq,
            "abstained": bool(res["abstained"]), "peptide_activity": res["peptide_activity"],
        })
    near_training_results = []
    for name, smi in NEAR_TRAINING_DIST_SMILES.items():
        res = check_compound_ood(smi)
        near_training_results.append({
            "name": name, "smiles": smi,
            "abstained": bool(res["abstained"]), "activity": res["activity"],
        })

    compound_leaks = [r for r in compound_results
                      if not r["abstained"] and r["activity"] is not None]
    peptide_leaks = [r for r in peptide_results
                     if not r["abstained"] and r["peptide_activity"] is not None]
    leaks = compound_leaks + peptide_leaks

    n_compounds = len(compound_results)
    n_peptides = len(peptide_results)
    n_compounds_abstained = sum(1 for r in compound_results if r["abstained"])
    n_peptides_abstained = sum(1 for r in peptide_results if r["abstained"])

    return {
        "n_compounds": n_compounds,
        "n_compounds_abstained": n_compounds_abstained,
        "n_peptides": n_peptides,
        "n_peptides_abstained": n_peptides_abstained,
        "n_abstained": n_compounds_abstained + n_peptides_abstained,
        "n_leaked": len(leaks),
        "leaks": leaks,
        "compound_results": compound_results,
        "peptide_results": peptide_results,
        "near_training_distribution": near_training_results,
    }


def build_report() -> dict[str, Any]:
    """确定性组装 T2 报告 payload,供 write_report 落盘、可一键复现。"""
    suite = run_ood_suite()
    sir_malformed = [{"name": name, **harness.run_query(q)}
                     for name, q in SIR_MALFORMED_QUERIES.items()]
    sir_insufficient = [{"name": name, **harness.run_query(q)}
                        for name, q in SIR_INSUFFICIENT_PROFILE_QUERIES.items()]
    no_predictor_violations = [
        r for r in sir_malformed
        if (not r["abstained"]
            or r["sir"] is not None
            or r["prediction_available"]
            or "no_successful_predictor" not in r["abstain_reasons"])
    ]
    insufficient_profile_violations = [
        r for r in sir_insufficient
        if (not r["abstained"]
            or r["sir"] is not None
            or r["prediction_available"]
            or "amr_profile_no_recognized_features" not in r["abstain_reasons"])
    ]
    sir_leaks = no_predictor_violations + insufficient_profile_violations
    return {
        "small_molecule_peptide_ood": suite,
        "sir_malformed_cases": sir_malformed,
        "sir_insufficient_profile_cases": sir_insufficient,
        "sir_leaks": sir_leaks,
        "verdict": {
            "n_total_leaks": suite["n_leaked"] + len(sir_leaks),
            "fail_closed_verified": (suite["n_leaked"] == 0 and len(sir_leaks) == 0),
        },
        "note": (
            "咖啡因/聚乙烯片段(C16)经实跑证实近训练分布(max_tanimoto>OOD阈值0.30),"
            "平台合理给出 MIC,非泄漏,详见 near_training_distribution;"
            "EC 空基因型/无关基因不是敏感性证据，必须以 "
            "amr_profile_no_recognized_features 弃权，详见 sir_insufficient_profile_cases。"
        ),
    }


if __name__ == "__main__":
    payload = build_report()
    p = harness.write_report("t2_ood", payload)
    print(f"t2_ood 报告写入 {p}")
    suite = payload["small_molecule_peptide_ood"]
    print(f"  化合物:{suite['n_compounds']} 个,弃权 {suite['n_compounds_abstained']} 个")
    print(f"  肽:{suite['n_peptides']} 个,弃权 {suite['n_peptides_abstained']} 个")
    print(f"  泄漏(未弃权却出 MIC):{suite['n_leaked']} 个")
    print(f"  SIR 乱格式泄漏:{len(payload['sir_leaks'])} 个")
    print(f"  裁决 fail_closed_verified={payload['verdict']['fail_closed_verified']}")
