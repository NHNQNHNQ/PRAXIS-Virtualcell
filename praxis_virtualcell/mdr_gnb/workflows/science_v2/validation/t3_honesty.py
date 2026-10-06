"""T3:诚实性验证。平台特色卖点验证:该弃权时弃权,该说"候选"时不越权说"已证实"。

--- T3A:无模型物种(实跑核对)---------------------------------------------------
data/mdr_gnb/models/<species>/MANIFEST.txt 载明各物种 genotype_to_sir 训练 artifact 数;
morganella_morganii / proteus_mirabilis / enterobacter_cloacae 三者均"训练=0"
(目录里只有 .gitkeep,无 .joblib),route_mdr 拿不到候选、无训练 artifact 兜底
→ 平台必须 core hard-abstain(abstained=True、sir=None、prediction_available=False，
reason 含 no_successful_predictor),绝不能编 R/S。

--- T3B:无机制支持(非代谢靶药)(实跑核对)-------------------------------------
GemFbaPredictor(gem_fba.py)只对 METABOLIC_TARGET_DRUGS(trimethoprim/sulfamethoxazole/
fosfomycin 等叶酸/细胞壁前体合成靶)跑 FBA;非代谢靶(meropenem 碳青霉烯/colistin 多黏菌素
膜活性)不在此表 → predict() 第一步即 abstained=True,mechanism_fusion.fuse_mechanism 据此
返回 {"available": False, "reason": "非代谢靶抗生素...", "mechanism_claim": None}。

要让 mechanism 段真正触发(而非因整体查询弃权导致 mechanism=None),drug 的 SMILES 必须落在
训练化学空间内(非 OOD,见 run_mdr_query.py 里 `not abstain` 才跑 fuse_mechanism 的判据)。
实跑核对:meropenem/colistin 用真实 PubChem canonical SMILES(见 _EXTRA_SMILES,来源 CID
441130/5311054,仅 connectivity 无立体化学——FBA 机制判定只按 drug 名字符串匹配代谢靶反应表,
不读 SMILES 结构,不影响判定)时 max_tanimoto 落在阈值内、不弃权,mechanism 段正常触发。
故无需退而求其次换用 ciprofloxacin。

--- T3C:G3 机理门(实跑核对)---------------------------------------------------
trimethoprim 是代谢靶药,FBA 真跑 iML1515 阻断 DHFR(growth_inhibition=1.0),但
run_g3_gate.ANCHORS 只覆盖 β-内酰胺机制两条锚点(EC×ceftriaxone、KP×meropenem),未覆盖
代谢靶药 → mechanism_fusion._default_g3_status 对 trimethoprim 返回 "not_evaluated" →
claim_allowed=False → mechanism_claim 恒 None(候选机制,不作已证实解释),即使 FBA 算出的
growth 抑制看起来"很确定"也不允许声称已证实——这是 critic 不变量#7
(mechanism_claim_without_g3)守的红线,此处从查询侧独立复核。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from praxis_virtualcell.mdr_gnb.workflows.science_v2.validation import harness

# t3_honesty.py: .../workflows/science_v2/validation/t3_honesty.py
# parents[0]=validation parents[1]=science_v2 parents[2]=workflows parents[3]=mdr_gnb
# parents[4]=praxis_virtualcell parents[5]=仓库根(与 harness.py 同款核对法)
_REPO_ROOT = Path(__file__).resolve().parents[5]
_GOLDEN_COMPOUNDS_PATH = _REPO_ROOT / "data" / "mdr_gnb" / "golden" / "golden_compounds.csv"

# ===========================================================================
# T3A:无模型物种 —— SIR 必须 fail-closed 弃权
# ===========================================================================

# 实跑核对(data/mdr_gnb/models/<sp>/MANIFEST.txt "训练=0"):三物种均 0 个 SIR 训练 artifact。
NO_MODEL_SPECIES: tuple[str, ...] = (
    "morganella_morganii", "proteus_mirabilis", "enterobacter_cloacae",
)

# 用真实存在的药(其它物种确有训练模型),纯粹考察"这三个无模型物种"本身是否弃权,
# 不引入"药本身也查无 artifact"的混淆变量。
_NO_MODEL_PROBE_DRUG = "meropenem"
_NO_MODEL_PROBE_DRUG_CLASS = "carbapenems"


def _sir_query(species: str, drug: str = _NO_MODEL_PROBE_DRUG,
              drug_class: str = _NO_MODEL_PROBE_DRUG_CLASS,
              amr_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "species": species,
        "amr_profile": amr_profile or {},
        "drug_panel": [{"drug": drug, "drug_class": drug_class}],
        "requested_outputs": ["SIR"],
    }


def sir_no_model(species: str) -> dict[str, Any]:
    """对无训练 artifact 的物种跑一次 SIR 查询,返回 harness.run_query 扁平 dict。"""
    return harness.run_query(_sir_query(species))


# ===========================================================================
# T3B/T3C:机制段 —— 非代谢靶 available=False;代谢靶候选 mechanism_claim 恒 None
# ===========================================================================

NON_METABOLIC_DRUGS: tuple[str, ...] = ("meropenem", "colistin")
METABOLIC_CANDIDATE_DRUG = "trimethoprim"

# golden_compounds.csv 里没有的药,给真实 canonical SMILES(公开事实,来自 PubChem)。
# 仅 connectivity(无立体化学标注),FBA 机制判定只按 drug 名字符串匹配 gem_fba.py 的
# METABOLIC_TARGET_DRUGS 表,不读 SMILES 结构 —— 不影响 T3B/T3C 的判定正确性。
_EXTRA_SMILES: dict[str, str] = {
    "meropenem": "CC(O)C1C(=O)N2C(C(=O)O)=C(SC3CNC(C(=O)N(C)C)C3)C(C)C12",  # PubChem CID 441130
    "colistin": (
        "CCC(C)CCCC(=O)NC(CCN)C(=O)NC(C(=O)NC(CCN)C(=O)NC1CCNC(=O)C(C(C)O)"
        "NC(=O)C(CCN)NC(=O)C(CCN)NC(=O)C(CC(C)C)NC(=O)C(CC(C)C)NC(=O)C(CCN)NC1=O)C(C)O"
    ),  # PubChem CID 5311054
}


def _lookup_golden_smiles(drug: str) -> str | None:
    """从 golden_compounds.csv(T1B 已核对分子式)按药名查 canonical SMILES,查不到返 None。"""
    rows = harness.load_golden(_GOLDEN_COMPOUNDS_PATH, required=["name", "smiles"])
    key = drug.strip().lower()
    for row in rows:
        if row["name"].strip().lower() == key:
            return row["smiles"]
    return None


def smiles_source(drug: str) -> str:
    """该药 SMILES 的来源说明(供报告透出,可核查)。"""
    if _lookup_golden_smiles(drug) is not None:
        return ("data/mdr_gnb/golden/golden_compounds.csv"
                "(T1B 已核对分子式,label_source=chembl_train)")
    if drug.strip().lower() in _EXTRA_SMILES:
        return "PubChem canonical SMILES(公开事实,内建于 t3_honesty._EXTRA_SMILES)"
    raise ValueError(f"drug={drug!r} 无已知 SMILES 来源")


def resolve_smiles(drug: str) -> str:
    """drug 名 → canonical SMILES。先查 golden,没有则查内建真实结构表;

    都没有 → 明确 raise(不静默拿错误/占位结构糊弄机制验证)。
    """
    smi = _lookup_golden_smiles(drug)
    if smi is not None:
        return smi
    smi = _EXTRA_SMILES.get(drug.strip().lower())
    if smi is not None:
        return smi
    raise ValueError(
        f"drug={drug!r} 既不在 golden_compounds.csv 也不在内建 _EXTRA_SMILES,"
        f"拒绝伪造 SMILES,请补充真实结构后再验证机制段"
    )


_MECHANISM_SPECIES = "escherichia_coli"


def _activity_query(drug: str, smiles: str) -> dict[str, Any]:
    return {
        "species": _MECHANISM_SPECIES,
        "smiles": smiles,
        "drug_panel": [{"drug": drug, "drug_class": "novel_compound"}],
        "requested_outputs": ["activity"],
    }


def mechanism_of(drug: str, smiles: str | None = None) -> dict[str, Any] | None:
    """跑一次小分子活性查询,返回 report.mechanism 段(dict 或 None)。

    smiles 缺省时按 drug 名解析(golden 优先,内建真实结构兜底);找不到时 resolve_smiles
    会 raise,不会静默拿错结构。若查询本身弃权(如 OOD),mechanism 段随之为 None——
    如实透出,不伪装成 available=False(那是"机制不可用"的诚实语义,与"整条查询没跑起来"不同)。
    """
    smi = smiles if smiles is not None else resolve_smiles(drug)
    res = harness.run_query(_activity_query(drug, smi))
    return res["mechanism"]


# ===========================================================================
# 汇总套件(供报告 + 战役裁决消费)
# ===========================================================================


def run_honesty_suite() -> dict[str, Any]:
    """跑 T3A/T3B/T3C 全部子项,统计违规(红线:任一子项不诚实)。

    violations 三类:
      - no_model_species_fabricated_sir:无模型物种竟出了 R/S 或 prediction_available=True。
      - non_metabolic_drug_fabricated_mechanism:非代谢靶药 mechanism 竟 available=True
        或 mechanism_claim 非 None(伪造机制)。
      - g3_gate_claim_without_pass:代谢靶候选药(G3 未过)mechanism_claim 竟非 None,
        或 g3_gate.claim_allowed 竟为 True(越权声称已证实)。
    确定性:遍历顺序严格按元组/常量定义原序。
    """
    violations: list[dict[str, Any]] = []

    no_model: dict[str, Any] = {}
    for sp in NO_MODEL_SPECIES:
        r = sir_no_model(sp)
        entry = {"sir": r["sir"], "prediction_available": r["prediction_available"],
                 "abstained": r["abstained"]}
        no_model[sp] = entry
        if (not entry["abstained"]
                or entry["sir"] is not None
                or entry["prediction_available"]):
            violations.append({
                "category": "no_model_species_fabricated_sir",
                "species": sp, "detail": entry,
            })

    non_metabolic: dict[str, Any] = {}
    for drug in NON_METABOLIC_DRUGS:
        m = mechanism_of(drug)
        non_metabolic[drug] = m
        if m is None or m.get("available") is not False or m.get("mechanism_claim") is not None:
            violations.append({
                "category": "non_metabolic_drug_fabricated_mechanism",
                "drug": drug, "detail": m,
            })

    g3_result = mechanism_of(METABOLIC_CANDIDATE_DRUG)
    g3_candidate = {METABOLIC_CANDIDATE_DRUG: g3_result}
    claim_allowed = (g3_result or {}).get("g3_gate", {}).get("claim_allowed") if g3_result else None
    if (g3_result is None
            or g3_result.get("available") is not True
            or g3_result.get("mechanism_claim") is not None
            or claim_allowed is not False):
        violations.append({
            "category": "g3_gate_claim_without_pass",
            "drug": METABOLIC_CANDIDATE_DRUG, "detail": g3_result,
        })

    return {
        "no_model": no_model,
        "non_metabolic": non_metabolic,
        "g3_candidate": g3_candidate,
        "violations": violations,
    }


def build_report() -> dict[str, Any]:
    """确定性组装 T3 报告 payload,供 harness.write_report 落盘。"""
    suite = run_honesty_suite()
    smiles_used = {
        drug: {"smiles": resolve_smiles(drug), "source": smiles_source(drug)}
        for drug in (*NON_METABOLIC_DRUGS, METABOLIC_CANDIDATE_DRUG)
    }
    return {
        **suite,
        "no_model_probe_drug": _NO_MODEL_PROBE_DRUG,
        "smiles_used": smiles_used,
        "verdict": {
            "n_violations": len(suite["violations"]),
            "honest": len(suite["violations"]) == 0,
        },
        "note": (
            "T3A:无模型物种(morganella_morganii/proteus_mirabilis/enterobacter_cloacae,"
            "MANIFEST 训练=0)必须 sir=None、prediction_available=False,不伪造 R/S;"
            "T3B:非代谢靶药(meropenem/colistin,真实 PubChem canonical SMILES,非 OOD)"
            "mechanism.available 必须 False,不伪造机制;"
            "T3C:代谢靶候选药(trimethoprim)FBA 真阻断 DHFR 但 G3 门(仅覆盖 β-内酰胺两锚点)"
            "未评估该药,mechanism_claim 必须恒 None(候选,不越权声称已证实)。"
        ),
    }


if __name__ == "__main__":
    payload = build_report()
    p = harness.write_report("t3_honesty", payload)
    print(f"t3_honesty 报告写入 {p}")
    print(f"  T3A 无模型物种:{list(payload['no_model'])}")
    print(f"  T3B 非代谢靶药:{list(payload['non_metabolic'])}")
    print(f"  T3C 代谢靶候选:{list(payload['g3_candidate'])}")
    print(f"  违规数:{payload['verdict']['n_violations']}")
    print(f"  裁决 honest={payload['verdict']['honest']}")
