"""T6:证据双系统一致性(运行时 SIR evidence_tiers vs 验证层 QSAR E0-E5)。

平台有**两套互不相干**的证据体系,前端必须按 output_kind 各取各的,串用即误导用户。

--- 系统①:per-prediction(SIR 侧)(实跑核对)------------------------------------
service.predict(raw)["response"]["evidence"] ← service._evidence_for(species, drug),
读 coordinator.fusion.load_evidence_tiers(),按 (species, drug) 元组键。实测 132 个 combo,
字段含 tier(strong/practical/no_baseline/unevaluated)、evidence_level(E0-E5)、delta_vme 等。
语义 = "这个物种×这个药的 SIR 融合相对冻结规则基线的证据强度"。

--- 系统②:模型级(QSAR 验证层)(实跑核对)------------------------------------
service.models_summary()["compound_activity_evidence"] ← _sm_activity_evidence() 读
reports/antibacterial/mdr_gnb/science_v2/sm_activity_evidence/sm_activity_evidence.json,fail-soft(缺则 None)。
实测 evidence_level="E4"、species="escherichia_coli"、r2=0.5654、n_compounds=27175。
语义 = "化合物活性 QSAR 模型整体爬到证据阶梯哪一级",与具体某药无关。

--- 红线陷阱(实跑坐实)---------------------------------------------------------
('escherichia_coli','trimethoprim') 在 evidence_tiers 里**确实存在**(tier=no_baseline,
evidence_level=E3)。故拿 drug 名 "trimethoprim" 跑**活性**查询(output_kind=sm_activity,
MIC≈1.3665)时,_evidence_for("escherichia_coli","trimethoprim") 照样命中,把那条 SIR 的
E3 塞进 response["evidence"] —— 它就摆在活性查询的返回里,唾手可得。该 E3 是 **SIR combo
的证据**,与"化合物活性预测有多可信"毫无关系;活性卡若取它显示即误导(应显示系统② E4)。
实测 27 个 golden 化合物里有 **12 个**在 EC SIR evidence_tiers 里有同名 combo(trap 面很宽)。

--- 为什么比对必须带 source,只比 evidence_level 会瞎(实跑核对)-------------------
撞级样本:('escherichia_coli','ampicillin') 与 ('escherichia_coli','tetracycline') 的 SIR
证据恰是 **E4/strong**,与 QSAR 验证层的 **E4** 撞级。串用后"层级看着对"(E4==E4),来源却
已经错了。故本层比对 (evidence_level, source) 二元组,不只比层级 —— 见
level_collision_cases() 与 test_level_only_comparison_would_be_blind。

--- 判别力设计(本层的命门)-----------------------------------------------------
最大风险是把矩阵写成"拿 X 和 X 比"→ n_mismatch 恒 0 → 恒绿空测。故两侧走**两条访问路径**:
  · 应显示层级(expected):规则函数 expected_badge(),按观察到的输出形态决定"该查哪套系统",
    层级值**直接读源头 artifact**(load_evidence_tiers() / sm_activity_evidence.json),
    不碰 run_query 的返回。
  · 实际可得层级(observed):selector 复刻前端 PredictionResult.tsx 的取数逻辑,
    跑在**真实 service 返回**(run_query + models_summary)上。

**能力边界(据实收敛,勿夸大)**:两侧是"**同源 artifact,两条访问路径**",不是"独立计算"——
expected 侧直读 sm_activity_evidence.json,observed 侧经 service.py:51 读的是**同一个文件**;
SIR 侧同理(两侧最终都落到 load_evidence_tiers(),实测 50 个 SIR case 里 18 个同源)。故:
  · 能抓:跨系统串用(活性卡取 SIR 证据)、服务层取错 combo/键错、物种 gate 失效。
  · 抓不了:artifact 本身写错(两侧会一起错)——那不在 T6 职责内,由产出 artifact 的层负责。
判别力由 crossed_selector(故意让活性卡取系统①)+ 负对照测试证明,非空口。
另一处结构性局限:contract_selector 是 TSX 的**手写 Python 复刻件**,只复核数据面;若 TSX 改用
result.evidence 喂活性卡,本层恒绿(由 PredictionResult.test.tsx 的真组件测试兜底)。

--- 肽侧:无模型级证据 artifact(实跑核对)---------------------------------------
reports/antibacterial/mdr_gnb/science_v2/ 下只有 sm_activity_evidence/,**没有**肽侧 evidence artifact。故肽查询
无模型级徽章(前端 PredictionResult.tsx 肽分支亦无证据 pill)。这是诚实现状,如实记录,
不为"补齐"而造假证据。
"""
from __future__ import annotations

import json
import random
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from praxis_virtualcell.mdr_gnb.api import service
from praxis_virtualcell.mdr_gnb.coordinator.fusion import load_evidence_tiers
from praxis_virtualcell.mdr_gnb.workflows.science_v2.validation import harness, t3_honesty

# t6_evidence.py: .../workflows/science_v2/validation/t6_evidence.py
# parents[0]=validation parents[1]=science_v2 parents[2]=workflows parents[3]=mdr_gnb
# parents[4]=praxis_virtualcell parents[5]=仓库根(与 harness.py/t3_honesty.py 同款核对法)
_REPO_ROOT = Path(__file__).resolve().parents[5]
_GOLDEN_SIR_PATH = _REPO_ROOT / "data" / "mdr_gnb" / "golden" / "golden_set_sir.yaml"
_GOLDEN_COMPOUNDS_PATH = _REPO_ROOT / "data" / "mdr_gnb" / "golden" / "golden_compounds.csv"
_GOLDEN_PEPTIDES_PATH = _REPO_ROOT / "data" / "mdr_gnb" / "golden" / "golden_peptides.csv"
_SM_EVIDENCE_PATH = (_REPO_ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v2" / "sm_activity_evidence"
                     / "sm_activity_evidence.json")
# 肽侧模型级证据的**约定路径**(实测不存在 → 无徽章,诚实记录,不造假)
_PEPTIDE_EVIDENCE_PATH = (_REPO_ROOT / "reports" / "antibacterial" / "mdr_gnb" / "science_v2" / "peptide_activity_evidence"
                          / "peptide_activity_evidence.json")

# 证据来源标识(比对的第二维;只比 evidence_level 会被 E4 撞级骗过)
SOURCE_SIR_TIERS = "sir_evidence_tiers"
SOURCE_COMPOUND_QSAR = "compound_activity_evidence"

_SPECIES = "escherichia_coli"
_SIR_SAMPLE_SEED = 20260715  # 预注册固定 seed(抽样确定性;跑前定,不看结果再改)
_SIR_SAMPLE_N = 50

# 从 t3_honesty 复用真实 SMILES 解析(golden 优先 → 内建真实结构;查不到 raise 而非伪造)。
# 计划书草稿里的 trimethoprim SMILES 是错的(C14H18N4O 二甲基单甲氧),真身是 C14H18N4O3
# 三甲氧 COc1cc(Cc2cnc(N)nc2N)cc(OC)c1OC —— 故一律走 golden,绝不硬编计划书那个错结构。
resolve_smiles = t3_honesty.resolve_smiles


# ===========================================================================
# 两套系统的**源头直读**(expected 侧用,刻意绕开 service 层)
# ===========================================================================


def sir_tier_evidence(species: str, drug: str) -> dict[str, Any] | None:
    """系统①源头直读:(species, drug) → SIR 证据分层(无收录返 None)。"""
    v = load_evidence_tiers().get((species, drug))
    return dict(v) if v is not None else None


def compound_model_level_evidence() -> dict[str, Any] | None:
    """系统②源头直读:化合物活性 QSAR 验证层证据 artifact(缺则 None)。"""
    if not _SM_EVIDENCE_PATH.exists():
        return None
    return json.loads(_SM_EVIDENCE_PATH.read_text(encoding="utf-8"))


def peptide_model_level_evidence() -> dict[str, Any] | None:
    """肽侧模型级证据 artifact —— 实测不存在,恒 None(诚实:肽无模型级徽章,不造假)。"""
    if not _PEPTIDE_EVIDENCE_PATH.exists():
        return None
    return json.loads(_PEPTIDE_EVIDENCE_PATH.read_text(encoding="utf-8"))


def level_collision_cases() -> dict[str, dict[str, Any]]:
    """撞级样本:SIR 证据层级恰好 == QSAR 层级的 golden 化合物(证明只比层级会瞎)。

    确定性:按 golden_compounds.csv 原序遍历。
    """
    qsar = compound_model_level_evidence() or {}
    qsar_level = qsar.get("evidence_level")
    rows = harness.load_golden(_GOLDEN_COMPOUNDS_PATH, required=["name", "smiles"])
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = row["name"].strip()
        sir_ev = sir_tier_evidence(_SPECIES, name)
        if sir_ev is None or sir_ev.get("evidence_level") != qsar_level:
            continue
        out[name] = {
            "sir_evidence_level": sir_ev.get("evidence_level"),
            "sir_tier": sir_ev.get("tier"),
            "qsar_evidence_level": qsar_level,
            "note": "SIR 层级与 QSAR 层级撞级,仅比 evidence_level 无法检出串用,必须比 source",
        }
    return out


# ===========================================================================
# 查询组装
# ===========================================================================


def _sir_query(species: str, amr_profile: dict[str, Any], drug: str,
               drug_class: str) -> dict[str, Any]:
    return {
        "species": species,
        "amr_profile": amr_profile,
        "drug_panel": [{"drug": drug, "drug_class": drug_class}],
        "requested_outputs": ["SIR"],
    }


def _activity_query(drug: str, smiles: str, species: str = _SPECIES) -> dict[str, Any]:
    return {
        "species": species,
        "smiles": smiles,
        "drug_panel": [{"drug": drug, "drug_class": "novel_compound"}],
        "requested_outputs": ["activity"],
    }


def _peptide_query(sequence: str, species: str = _SPECIES) -> dict[str, Any]:
    return {
        "species": species,
        "sequence": sequence,
        "drug_panel": [{"drug": sequence, "drug_class": "antimicrobial_peptide"}],
        "requested_outputs": ["peptide_activity"],
    }


# ===========================================================================
# T6 主探针:活性查询下双系统不串
# ===========================================================================


def activity_evidence_source(drug: str, smiles: str | None = None, *,
                             selector: Callable[..., dict[str, Any]] | None = None
                             ) -> dict[str, Any]:
    """跑一次活性查询,把两套系统的证据并排摊开,断言前端契约的数据面。

    返回:
      per_prediction_evidence  —— 系统①(SIR 侧),即 response["evidence"]。**陷阱**:
        活性查询下它照样可能非 None(trimethoprim 命中 EC×trimethoprim 的 E3/no_baseline)。
      model_level_evidence     —— 系统②(QSAR 验证层 E4)。
      activity_card_evidence   —— 前端活性卡**实际**取到的(selector 在真数据上选出)。
      card_took_sir_evidence   —— **承重**:活性卡是否取了系统① 的证据(True=串用事故)。
        比的是 selector **动态选出的** card["source"] 与系统① 的 source,不是两个硬编字面量
        (那样恒 True,是个只会给虚假安慰的空字段)。selector=crossed_selector 时此值翻 True,
        故可证承重——见 test_card_took_sir_evidence_flips_under_crossed_selector。

    selector 缺省(None)=产品契约 contract_selector(它定义在本函数之后,故用 None 哨兵而非
    默认实参——默认实参在 def 时求值,直接引用会 NameError);测试可注入 crossed_selector。
    """
    sel = selector if selector is not None else contract_selector
    smi = smiles if smiles is not None else resolve_smiles(drug)
    res = harness.run_query(_activity_query(drug, smi))

    per = res["evidence"]
    per_out = None
    if per is not None:
        per_out = {
            "tier": per.get("tier"),
            "evidence_level": per.get("evidence_level"),
            "source": SOURCE_SIR_TIERS,
            "note": "SIR combo 证据,与化合物活性可信度无关;活性卡取用即误导",
        }

    model = service.models_summary()["compound_activity_evidence"]
    model_out = None
    if model is not None:
        model_out = {
            "evidence_level": model.get("evidence_level"),
            "species": model.get("species"),
            "r2": model.get("r2"),
            "source": SOURCE_COMPOUND_QSAR,
        }

    card = sel(res, model, _SPECIES)
    return {
        "drug": drug,
        "smiles": smi,
        "output_kind": res["output_kind"],
        "abstained": bool(res["abstained"]),
        "per_prediction_evidence": per_out,
        "model_level_evidence": model_out,
        "activity_card_evidence": card,
        # 承重:card["source"] 由 selector 在真实返回上动态选出,与系统① 的 source 比。
        # 契约正确 → False;契约被改成串用(crossed_selector)→ True。
        "card_took_sir_evidence": bool(card["source"] == SOURCE_SIR_TIERS),
    }


# ===========================================================================
# 矩阵:应显示层级(规则,独立) vs 实际可得层级(前端取数模拟)
# ===========================================================================


def observed_case_kind(res: dict[str, Any]) -> str:
    """按**实际返回形态**归类(不按声明意图 —— 声明说了不算,实跑说了算)。"""
    if res["abstained"]:
        return "abstained"
    if res["activity"] is not None:
        return "sm_activity"
    if res["peptide_activity"] is not None:
        return "peptide_activity"
    if res["sir"] is not None:
        return "sir"
    return "no_result"


def expected_badge(res: dict[str, Any], species: str, drug: str) -> dict[str, Any]:
    """**应显示层级**:规则函数,按输出形态决定该查哪套系统,层级值直接读源头 artifact。

    刻意**不碰** run_query 的 evidence 字段 —— 与 observed 侧走不同代码路径,才有判别力。
    规则(= 前端契约的规范表述):
      · 弃权 / 无结果 → 无徽章(铁律:弃权不出任何裁决,自然也不出证据)
      · SIR    → 系统①,查 (species, drug) 的 per-combo tier
      · 活性   → 系统②,QSAR 模型级证据,且**物种匹配**才显示(防未来多物种串用 EC 的 E4)
      · 肽     → 无模型级徽章(肽侧无 evidence artifact,诚实现状)
    """
    kind = observed_case_kind(res)
    if kind in ("abstained", "no_result"):
        return {"evidence_level": None, "source": None}
    if kind == "sir":
        ev = sir_tier_evidence(species, drug)
        if ev is None:
            return {"evidence_level": None, "source": None}
        return {"evidence_level": ev.get("evidence_level"), "source": SOURCE_SIR_TIERS}
    if kind == "sm_activity":
        ev = compound_model_level_evidence()
        if ev is None or ev.get("species") != species:
            return {"evidence_level": None, "source": None}
        return {"evidence_level": ev.get("evidence_level"), "source": SOURCE_COMPOUND_QSAR}
    # peptide_activity:无模型级徽章
    return {"evidence_level": None, "source": None}


def contract_selector(res: dict[str, Any], models_ev: dict[str, Any] | None,
                      species: str) -> dict[str, Any]:
    """**实际可得层级**:复刻前端 PredictionResult.tsx 的证据取数逻辑,跑在真实 service 返回上。

    对应源码(praxis_vc_react/src/mdr/pages/PredictionResult.tsx):
      :41 弃权分支 → 不渲染任何证据
      :69 活性分支 → :72 evOk = !!compoundEvidence && compoundEvidence.species === result.species
                     :84/:106 仅 evOk 时显示 compoundEvidence.evidence_level(系统②)
      肽分支       → 无证据 pill
      SIR 分支     → :37 E = result.evidence?.evidence_level(系统①);:210 显示
    """
    if res["abstained"]:
        return {"evidence_level": None, "source": None}
    if res["activity"] is not None:
        ev_ok = models_ev is not None and models_ev.get("species") == species
        if not ev_ok:
            return {"evidence_level": None, "source": None}
        return {"evidence_level": models_ev.get("evidence_level"),
                "source": SOURCE_COMPOUND_QSAR}
    if res["peptide_activity"] is not None:
        return {"evidence_level": None, "source": None}
    if res["sir"] is not None:
        ev = res["evidence"]
        if ev is None:
            return {"evidence_level": None, "source": None}
        return {"evidence_level": ev.get("evidence_level"), "source": SOURCE_SIR_TIERS}
    return {"evidence_level": None, "source": None}


def crossed_selector(res: dict[str, Any], models_ev: dict[str, Any] | None,
                     species: str) -> dict[str, Any]:
    """★负对照专用:**故意串用** —— 活性卡错拿系统① 的 SIR evidence 当活性证据。

    这正是 T6 要防的事故形态(把 EC×trimethoprim 的 E3/no_baseline 当成活性证据显示)。
    build_matrix(selector=crossed_selector) 必须检出 n_mismatch>0,否则矩阵是空测。
    仅供测试注入,产品代码永不使用。
    """
    if res["abstained"]:
        return {"evidence_level": None, "source": None}
    if res["activity"] is not None:
        ev = res["evidence"]  # ← 串用:活性卡取了 SIR 侧证据
        if ev is None:
            return {"evidence_level": None, "source": None}
        return {"evidence_level": ev.get("evidence_level"), "source": SOURCE_SIR_TIERS}
    return contract_selector(res, models_ev, species)


def _sir_cases() -> list[dict[str, Any]]:
    """golden_set_sir.yaml 固定 seed 抽样(确定性:抽完按原索引排序,顺序恒定)。"""
    rows = yaml.safe_load(_GOLDEN_SIR_PATH.read_text(encoding="utf-8"))
    n = min(_SIR_SAMPLE_N, len(rows))
    idx = sorted(random.Random(_SIR_SAMPLE_SEED).sample(range(len(rows)), n))
    cases = []
    for i in idx:
        r = rows[i]
        cases.append({
            "case_id": f"sir::{r['isolate_id']}::{r['drug']}",
            "declared_kind": "sir",
            "species": r["species"],
            "drug": r["drug"],
            "raw": _sir_query(r["species"], r["amr_profile"], r["drug"], r["drug_class"]),
        })
    return cases


def _activity_cases() -> list[dict[str, Any]]:
    """全部 27 个 golden 化合物(含 12 个在 EC SIR tiers 里有同名 combo 的 trap 样本)。"""
    rows = harness.load_golden(_GOLDEN_COMPOUNDS_PATH, required=["name", "smiles"])
    return [{
        "case_id": f"activity::{r['name'].strip()}",
        "declared_kind": "sm_activity",
        "species": _SPECIES,
        "drug": r["name"].strip(),
        "raw": _activity_query(r["name"].strip(), r["smiles"].strip()),
    } for r in rows]


def _peptide_cases() -> list[dict[str, Any]]:
    """全部 28 个 golden 肽(drug 名用 sequence 占位,与 T1C 同款)。"""
    rows = harness.load_golden(_GOLDEN_PEPTIDES_PATH, required=["name", "sequence"])
    return [{
        "case_id": f"peptide::{r['name'].strip()}",
        "declared_kind": "peptide_activity",
        "species": _SPECIES,
        "drug": r["sequence"].strip(),
        "raw": _peptide_query(r["sequence"].strip()),
    } for r in rows]


def _abstain_cases() -> list[dict[str, Any]]:
    """弃权类:真 OOD 小分子/肽(T2 已实跑坐实 abstained=True)+ 无模型物种(T3A fail-closed)。"""
    cases: list[dict[str, Any]] = []
    for name, smi in (("甲烷", "C"), ("乙烷", "CC"), ("苯", "c1ccccc1")):
        cases.append({
            "case_id": f"abstain_ood_compound::{name}",
            "declared_kind": "abstained",
            "species": _SPECIES,
            "drug": smi,
            "raw": _activity_query(smi, smi),
        })
    for name, seq in (("polyA", "A" * 18), ("polyG", "G" * 16)):
        cases.append({
            "case_id": f"abstain_ood_peptide::{name}",
            "declared_kind": "abstained",
            "species": _SPECIES,
            "drug": seq,
            "raw": _peptide_query(seq),
        })
    for sp in ("morganella_morganii", "proteus_mirabilis"):
        cases.append({
            "case_id": f"abstain_no_model_species::{sp}",
            "declared_kind": "abstained",
            "species": sp,
            "drug": "meropenem",
            "raw": _sir_query(sp, {"blaKPC": True}, "meropenem", "carbapenems"),
        })
    return cases


def build_cases() -> list[dict[str, Any]]:
    """混合 case 集(确定性:SIR 抽样固定 seed → 活性 → 肽 → 弃权,顺序恒定)。"""
    return [*_sir_cases(), *_activity_cases(), *_peptide_cases(), *_abstain_cases()]


def build_matrix(*, selector: Callable[..., dict[str, Any]] = contract_selector
                 ) -> dict[str, Any]:
    """遍历混合 case:应显示层级(规则,直读 artifact) vs 实际可得层级(前端取数模拟)。

    mismatch = 二者的 (evidence_level, source) 不等 → 证据串用/取错事故。
    selector 缺省 = 产品契约(contract_selector);测试可注入 crossed_selector 做负对照,
    证明本矩阵**真有判别力**(串用了会红),而非恒 0 的自我安慰。
    """
    models_ev = service.models_summary()["compound_activity_evidence"]
    rows: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    by_case_kind: dict[str, int] = {}

    for case in build_cases():
        res = harness.run_query(case["raw"])
        kind = observed_case_kind(res)
        by_case_kind[kind] = by_case_kind.get(kind, 0) + 1

        exp = expected_badge(res, case["species"], case["drug"])
        act = selector(res, models_ev, case["species"])
        ok = (exp["evidence_level"] == act["evidence_level"]
              and exp["source"] == act["source"])

        row = {
            "case_id": case["case_id"],
            "declared_kind": case["declared_kind"],
            "case_kind": kind,
            "species": case["species"],
            "drug": case["drug"],
            "expected": exp,
            "actual": act,
            "match": ok,
        }
        rows.append(row)
        if not ok:
            mismatches.append(row)

    return {
        "n_case": len(rows),
        "n_mismatch": len(mismatches),
        "by_case_kind": dict(sorted(by_case_kind.items())),
        "mismatches": mismatches,
        "cases": rows,
    }


# ===========================================================================
# 报告
# ===========================================================================


def _build_findings(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    """数据驱动生成顶层 findings(证据串用=红线事故)。无 mismatch → []。"""
    if not matrix["n_mismatch"]:
        return []
    return [{
        "id": "evidence_cross_use",
        "severity": "red_line",
        "n_affected": matrix["n_mismatch"],
        "detail": "显示层级 != 实际应显示层级,证据双系统串用",
        "cases": [m["case_id"] for m in matrix["mismatches"]],
    }]


def build_report() -> dict[str, Any]:
    """确定性组装 T6 报告 payload。路径用**相对仓库根**(绝对路径破坏跨机器字节一致)。"""
    matrix = build_matrix()
    probe = activity_evidence_source("trimethoprim")
    findings = _build_findings(matrix)
    return {
        "matrix": matrix,
        "trap_probe_trimethoprim": probe,
        "level_collision_cases": level_collision_cases(),
        "systems": {
            "per_prediction_sir": {
                "source_id": SOURCE_SIR_TIERS,
                "path": "data/mdr_gnb/(evidence_tiers via coordinator.fusion.load_evidence_tiers)",
                "n_combos": len(load_evidence_tiers()),
                "keyed_by": "(species, drug)",
            },
            "model_level_qsar": {
                "source_id": SOURCE_COMPOUND_QSAR,
                "path": "reports/antibacterial/mdr_gnb/science_v2/sm_activity_evidence/sm_activity_evidence.json",
                "evidence_level": (compound_model_level_evidence() or {}).get("evidence_level"),
                "species": (compound_model_level_evidence() or {}).get("species"),
            },
            "model_level_peptide": {
                "path": "reports/antibacterial/mdr_gnb/science_v2/peptide_activity_evidence/"
                        "peptide_activity_evidence.json",
                "exists": _PEPTIDE_EVIDENCE_PATH.exists(),
                "note": "肽侧无模型级证据 artifact → 无徽章(诚实现状,未造假证据)",
            },
        },
        "sampling": {"sir_seed": _SIR_SAMPLE_SEED, "sir_n": _SIR_SAMPLE_N,
                     "note": "预注册固定 seed,抽样确定性"},
        "findings": findings,
        "n_findings": len(findings),
        "verdict": {
            "n_case": matrix["n_case"],
            "n_mismatch": matrix["n_mismatch"],
            "evidence_systems_consistent": matrix["n_mismatch"] == 0,
        },
        "note": (
            "两套证据系统:①per-prediction SIR evidence_tiers(132 combo,按 species×drug)"
            "②模型级 QSAR 验证层(E4,EC,scaffold-split CV)。陷阱:EC×trimethoprim 在①里有"
            "E3/no_baseline,活性查询照样返回它,活性卡取用即误导(应取② E4)。"
            "比对带 source 维:ampicillin/tetracycline 的 SIR 证据恰是 E4/strong,与 QSAR E4 "
            "撞级,只比 evidence_level 检不出串用。判别力由 crossed_selector 负对照证明。"
            "肽侧无模型级证据 artifact,无徽章(诚实现状)。"
        ),
    }


if __name__ == "__main__":
    payload = build_report()
    p = harness.write_report("t6_evidence", payload)
    print(f"t6_evidence 报告写入 {p}")
    m = payload["matrix"]
    print(f"  矩阵 case 数:{m['n_case']}")
    print(f"  各类计数:{m['by_case_kind']}")
    print(f"  mismatch(证据串用):{m['n_mismatch']}")
    print(f"  撞级样本(只比层级会瞎):{list(payload['level_collision_cases'])}")
    if payload["n_findings"]:
        print(f"  ⚠ 红线 findings({payload['n_findings']} 条):")
        for f in payload["findings"]:
            print(f"    - {f['id']}: {f['detail']}({f['n_affected']} 例)")
    print(f"  裁决 evidence_systems_consistent={payload['verdict']['evidence_systems_consistent']}")
