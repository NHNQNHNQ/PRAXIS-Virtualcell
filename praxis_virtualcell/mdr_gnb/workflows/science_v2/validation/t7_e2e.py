"""T7:API 层与直调层科学结果一致(端到端契约)。

**测的是科学结果一致,不测 UI 像素**:同一 raw,`service.predict(raw)` 直调 vs 经 HTTP
`POST /predict`,科学结论字段逐字相等。

--- 两条路径的真实差异(实跑核对)-----------------------------------------------
api/app.py:66 的 `/predict`:`body: PredictRequest` → `raw = body.to_raw()` →
`service.predict(raw)`。直调:`service.predict(raw)` 直接吃调用方给的 raw。
故两条路径**只差一个 pydantic 往返**(schemas.py:26 `PredictRequest.to_raw()`),而该往返
**会规范化 raw**:
  · 缺 `amr_profile` → 补 `{}`;缺 `drug_class` → 补 `""`(键集变了 → raw 变了)
  · `smiles=""` 空串 → 被丢掉(`if self.smiles` 对空串为 False)
  · schema 未声明的字段 → pydantic 默认忽略
raw 一变,`service.canonical_task_id`(对 raw 做 sha256)算出的 task_id 就跟着变。
故本层的 CASES 每条都构造成 `to_raw()` 的**不动点**(`PredictRequest(**raw).to_raw() == raw`),
两条路径才是同一个 raw、逐字比对才有意义 —— 该性质由 test_cases_are_schema_fixed_points 显式断言,
不是靠嘴说。实跑结论:**7 条 CASES 全部是不动点,HTTP 与直调 task_id 逐条相等**。

注:既有 t2_ood/t3_honesty/t6_evidence 的查询构造器省略了 `amr_profile`(活性/肽查询用不到),
其 raw **不是**不动点。那不是产品缺陷 —— 真实前端发的请求必经 PredictRequest,`amr_profile`
恒被补齐;省略只发生在验证 harness 的直调侧。故本层不复用那些构造器的 raw,只复用其**常量**
(OOD_SMILES / OOD_PEPTIDES / NO_MODEL_SPECIES),自行补齐 4 键成不动点。

--- 历史缺陷:schema 曾剥离 smiles/sequence(本层钉死其不回退)-------------------
`smiles`/`sequence`/`compound` 现已在 schema(schemas.py:22-24),是线B 网站更新时修过的缺陷
("修 schema 剥离 smiles/sequence + prediction_available 漏认 peptide")。故 CASES **必须**含
真实 smiles 与 sequence(取自 golden),经 HTTP 验证二者真达后端、产出活性结论。

--- 判别力(本层命门,据实收敛)-------------------------------------------------
若 pydantic 往返无损,两条路径自然全等 → 逐字比对有沦为空测之虞。故设**两条负对照**
(NEGATIVE_CONTROLS),各剥掉 schema 的一个真实入参键,看逐字比对能否检出。因果干净:
两侧 raw 的**唯一**差异就是被剥的那个键,无混杂变量。实测(见报告 negative_controls):

  · `strip_smiles_sequence`(LegacyPredictRequest,忠实复刻**修复前**的历史缺陷版 schema):
    剥离后 ciprofloxacin/magainin_2 双双 fail-closed 弃权(output_kind sm_activity/
    peptide_activity → None)→ 检出 {sm_activity, peptide_activity}。
  · `strip_amr_profile`(AmrStrippingPredictRequest,SIR 真读 amr_profile):
    剥离后 SIR 锚点从 R 变为**硬弃权** → 检出 {sir}。这证明 schema 往返不能静默丢掉
    AMR 输入；缺失或无法投影到模型特征的 profile 不得被解释成敏感。

**边界(不夸大)**:
  · 已获实证的类:{sir, sm_activity, peptide_activity} —— 5 类里的 3 类。
  · **判别力未获实证**的类:{ood, no_model_species} —— 二者本就恒 fail-closed(前者 OOD 弃权,
    后者无训练 artifact),剥任何入参键都还是 fail-closed,故"剥字段"这一族负对照对它们
    无从发力。**注意措辞**:这是"未获实证",**不等于**"无判别力" —— 逐字比对仍钉着
    "HTTP 侧不得在直调弃权处凭空造出结论",只是本族负对照造不出那个反例。
    如实钉在 test_power_not_demonstrated_only_for_fail_closed_kinds。
  · 负对照走 schema 往返层(`via_schema`),非 HTTP 层:create_app 把 `PredictRequest` 硬编在
    路由签名上,无法注入替身 schema。因两条路径的差异**恰好就是**这个往返(app.py:66),
    在往返层证判别力即足以覆盖被测差异;HTTP 全栈由主测试 test_http_matches_direct
    真跑 TestClient 走。

--- 无模型物种的 fail-closed 形态(P0 关闭后)-----------------------------------
morganella_morganii(MANIFEST 训练=0)没有成功 predictor 时，核心层必须返回
`abstained=True`，并带机器理由 `no_successful_predictor`；`sir=None`、
`output_kind=None`、`prediction_available=False`。这不再依赖报告层把“空结果”兜底，故本层将
该类期望形态记作 "abstained"。

--- 前端 fixture(可再生)-------------------------------------------------------
`emit_frontend_fixtures()` 把**后端真跑**出来的完整响应落到
`praxis_vc_react/src/mdr/phase11.fixtures.ts`,供 phase11.e2e.test.tsx 断言"渲染层不丢/不造字段"。
fixture 非手写臆造。再生(与报告同一入口,一并重写):
    .venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.validation.t7_e2e
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from praxis_virtualcell.mdr_gnb.api import service
from praxis_virtualcell.mdr_gnb.api.app import create_app
from praxis_virtualcell.mdr_gnb.api.schemas import PredictRequest
from praxis_virtualcell.mdr_gnb.workflows.science_v2.validation import harness, t2_ood, t3_honesty

# t7_e2e.py: .../workflows/science_v2/validation/t7_e2e.py
# parents[0]=validation parents[1]=science_v2 parents[2]=workflows parents[3]=mdr_gnb
# parents[4]=praxis_virtualcell parents[5]=仓库根(与 harness.py/t6_evidence.py 同款核对法)
_REPO_ROOT = Path(__file__).resolve().parents[5]
_GOLDEN_COMPOUNDS_PATH = _REPO_ROOT / "data" / "mdr_gnb" / "golden" / "golden_compounds.csv"
_GOLDEN_PEPTIDES_PATH = _REPO_ROOT / "data" / "mdr_gnb" / "golden" / "golden_peptides.csv"

# 前端 fixture 落盘位置(相对仓库根记进报告,绝对路径破坏跨机器字节一致)
_FRONTEND_FIXTURE_REL = "praxis_vc_react/src/mdr/phase11.fixtures.ts"
FRONTEND_FIXTURE_PATH = _REPO_ROOT / _FRONTEND_FIXTURE_REL

# 计划书指定的科学结论字段(逐字比对对象)
SCIENCE_FIELDS: tuple[str, ...] = (
    "abstained", "output_kind", "sir", "activity", "peptide_activity", "mechanism",
)

_SPECIES = "escherichia_coli"


def _golden_smiles(name: str) -> str:
    """golden_compounds.csv 按化合物名查 canonical SMILES(查不到即 raise,不伪造结构)。"""
    rows = harness.load_golden(_GOLDEN_COMPOUNDS_PATH, required=["name", "smiles"])
    for row in rows:
        if row["name"].strip() == name:
            return row["smiles"].strip()
    raise ValueError(f"golden_compounds.csv 无化合物 {name!r},拒绝伪造 SMILES")


def _golden_sequence(name: str) -> str:
    """golden_peptides.csv 按肽名查序列(查不到即 raise,不伪造序列)。"""
    rows = harness.load_golden(_GOLDEN_PEPTIDES_PATH, required=["name", "sequence"])
    for row in rows:
        if row["name"].strip() == name:
            return row["sequence"].strip()
    raise ValueError(f"golden_peptides.csv 无肽 {name!r},拒绝伪造序列")


# ===========================================================================
# CASES:5 类各 ≥1,每条都是 to_raw() 不动点(4 键补齐 + drug_class 显式)
# ===========================================================================


def _sir_raw(species: str, amr_profile: dict[str, Any], drug: str,
             drug_class: str) -> dict[str, Any]:
    """SIR raw(不动点:4 键齐全,drug_class 显式)。"""
    return {
        "species": species,
        "drug_panel": [{"drug": drug, "drug_class": drug_class}],
        "requested_outputs": ["SIR"],
        "amr_profile": amr_profile,
    }


def _activity_raw(drug: str, smiles: str, species: str = _SPECIES) -> dict[str, Any]:
    """小分子活性 raw。**amr_profile 显式补 {}** —— 活性查询用不到它,但省略就不是不动点。"""
    return {
        "species": species,
        "drug_panel": [{"drug": drug, "drug_class": "novel_compound"}],
        "requested_outputs": ["activity"],
        "amr_profile": {},
        "smiles": smiles,
    }


def _peptide_raw(drug: str, sequence: str, species: str = _SPECIES) -> dict[str, Any]:
    """肽活性 raw(amr_profile 同上,显式补 {} 保不动点)。"""
    return {
        "species": species,
        "drug_panel": [{"drug": drug, "drug_class": "antimicrobial_peptide"}],
        "requested_outputs": ["peptide_activity"],
        "amr_profile": {},
        "sequence": sequence,
    }


def _build_case_specs() -> tuple[dict[str, Any], ...]:
    """固定语料(顺序固定 → 确定性)。魔法值一律复用既有模块常量 / golden,不复制粘贴。

    · SIR ×2:T1A 的两条强机制锚点(EC×blaCTX-M-15×ceftriaxone、KP×blaKPC-2×meropenem)
    · 小分子 ×1:golden_compounds 的 ciprofloxacin(真实 SMILES)
    · 肽 ×1:golden_peptides 的 magainin_2(真实序列)
    · OOD ×2:t2_ood 实跑坐实的真 OOD(甲烷 / polyA)
    · 无模型物种 ×1:t3_honesty.NO_MODEL_SPECIES[0](MANIFEST 训练=0)
    """
    return (
        {
            "case_id": "sir::escherichia_coli::blaCTX-M-15::ceftriaxone",
            "declared_kind": "sir",
            "raw": _sir_raw("escherichia_coli", {"blaCTX-M-15": True},
                            "ceftriaxone", "cephalosporins"),
        },
        {
            "case_id": "sir::klebsiella_pneumoniae::blaKPC-2::meropenem",
            "declared_kind": "sir",
            "raw": _sir_raw("klebsiella_pneumoniae", {"blaKPC-2": True},
                            "meropenem", "carbapenems"),
        },
        {
            "case_id": "sm_activity::ciprofloxacin",
            "declared_kind": "sm_activity",
            "raw": _activity_raw("ciprofloxacin", _golden_smiles("ciprofloxacin")),
        },
        {
            "case_id": "peptide_activity::magainin_2",
            "declared_kind": "peptide_activity",
            "raw": _peptide_raw("magainin_2", _golden_sequence("magainin_2")),
        },
        {
            "case_id": "ood::compound::甲烷",
            "declared_kind": "ood",
            # 复用 t2_ood 实跑坐实的真 OOD 结构(非魔法值)
            "raw": _activity_raw("甲烷", t2_ood.OOD_SMILES["甲烷"]),
        },
        {
            "case_id": "ood::peptide::polyA",
            "declared_kind": "ood",
            "raw": _peptide_raw("polyA", t2_ood.OOD_PEPTIDES["polyA"]),
        },
        {
            "case_id": f"no_model_species::{t3_honesty.NO_MODEL_SPECIES[0]}",
            "declared_kind": "no_model_species",
            "raw": _sir_raw(t3_honesty.NO_MODEL_SPECIES[0], {"blaKPC-2": True},
                            "meropenem", "carbapenems"),
        },
    )


CASE_SPECS: tuple[dict[str, Any], ...] = _build_case_specs()
CASES: tuple[dict[str, Any], ...] = tuple(spec["raw"] for spec in CASE_SPECS)

# 各声明类别**应呈**的输出形态(实跑核对得来,供 test_declared_kind_matches_observed_shape
# 反查语料声明是否撒谎)。无模型物种没有成功 predictor，必须核心 hard abstain。
EXPECTED_SHAPE: dict[str, str] = {
    "sir": "sir",
    "sm_activity": "sm_activity",
    "peptide_activity": "peptide_activity",
    "ood": "abstained",
    "no_model_species": "abstained",
}


# ===========================================================================
# 两条路径
# ===========================================================================


def make_client() -> TestClient:
    """纯内存 app(不给 db_url/cache)→ 适合 TestClient,不落库不缓存。"""
    return TestClient(create_app())


def direct(raw: dict[str, Any]) -> dict[str, Any]:
    """直调路径:service.predict(raw) 的 response(不经 pydantic 往返)。"""
    return service.predict(raw)["response"]


def via_http(raw: dict[str, Any], client: TestClient | None = None) -> dict[str, Any]:
    """HTTP 路径:POST /predict 的响应体(经 PredictRequest.to_raw() 规范化)。"""
    c = client if client is not None else make_client()
    return c.post("/predict", json=raw).json()


def schema_roundtrip(raw: dict[str, Any],
                     model: type[BaseModel] = PredictRequest) -> dict[str, Any]:
    """raw → schema → to_raw()。不动点判定与负对照共用此入口。"""
    return model(**raw).to_raw()  # type: ignore[attr-defined]


def observed_shape(resp: dict[str, Any]) -> str:
    """按**实际返回形态**归类(不按声明意图 —— 声明说了不算,实跑说了算;与 T6 同款)。"""
    r = resp["report"]
    if r["abstained"]:
        return "abstained"
    if r["activity"] is not None:
        return "sm_activity"
    if r["peptide_activity"] is not None:
        return "peptide_activity"
    if r["sir"] is not None:
        return "sir"
    return "no_result"


# ===========================================================================
# ★负对照:各剥掉 schema 的一个真实入参键,证明逐字比对真承重
# ===========================================================================


class _StripDrugEntry(BaseModel):
    drug: str
    drug_class: str = ""


class LegacyPredictRequest(BaseModel):
    """★负对照 1:忠实复刻**修复前**的 schema —— 无 compound/smiles/sequence 三字段。

    pydantic 默认忽略未声明字段 → to_raw() 静默丢掉 smiles/sequence,正是历史缺陷的形态。
    与现行 PredictRequest 的**唯一**差异就是这三个键(amr_profile 照留)→ 因果干净。
    仅供判别力证明,产品代码永不使用。
    """

    species: str
    drug_panel: list[_StripDrugEntry] = Field(default_factory=list)
    requested_outputs: list[str] = Field(default_factory=lambda: ["SIR"])
    amr_profile: dict[str, Any] = Field(default_factory=dict)

    def to_raw(self) -> dict[str, Any]:
        return {
            "species": self.species,
            "drug_panel": [{"drug": d.drug, "drug_class": d.drug_class}
                           for d in self.drug_panel],
            "requested_outputs": list(self.requested_outputs),
            "amr_profile": dict(self.amr_profile),
        }


class AmrStrippingPredictRequest(BaseModel):
    """★负对照 2:假想缺陷版 —— 剥掉 `amr_profile`(SIR 侧真读它的那个键)。

    与现行 PredictRequest 的**唯一**差异就是 amr_profile(compound/smiles/sequence 照留)
    → 因果干净。P0 关闭后，剥离使 SIR 锚点由 R 变成硬弃权：无法投影到模型特征的
    profile 不能被静默当作全零输入。证明 SIR 侧的逐字比对真有牙齿。
    仅供判别力证明,产品代码永不使用。
    """

    species: str
    drug_panel: list[_StripDrugEntry] = Field(default_factory=list)
    requested_outputs: list[str] = Field(default_factory=lambda: ["SIR"])
    compound: str | None = None
    smiles: str | None = None
    sequence: str | None = None

    def to_raw(self) -> dict[str, Any]:
        raw: dict[str, Any] = {
            "species": self.species,
            "drug_panel": [{"drug": d.drug, "drug_class": d.drug_class}
                           for d in self.drug_panel],
            "requested_outputs": list(self.requested_outputs),
        }
        if self.compound:
            raw["compound"] = self.compound
        if self.smiles:
            raw["smiles"] = self.smiles
        if self.sequence:
            raw["sequence"] = self.sequence
        return raw


# 负对照登记表(顺序固定 → 报告确定性)。key = 该对照剥掉的入参键。
NEGATIVE_CONTROLS: dict[str, type[BaseModel]] = {
    "strip_smiles_sequence": LegacyPredictRequest,
    "strip_amr_profile": AmrStrippingPredictRequest,
}


def via_schema(raw: dict[str, Any], model: type[BaseModel] = PredictRequest) -> dict[str, Any]:
    """经指定 schema 往返后再直调 —— 复刻 app.py:66 的 `raw = body.to_raw()` 一步。

    model=PredictRequest → 等价 HTTP 路径的 raw 处理;model=LegacyPredictRequest → 负对照。
    """
    return direct(schema_roundtrip(raw, model))


def _mismatched_fields(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    """两个 response 的科学字段差异清单(顺序按 SCIENCE_FIELDS,确定性)。"""
    return [k for k in SCIENCE_FIELDS if a["report"][k] != b["report"][k]]


def stripping_probe(model: type[BaseModel]) -> dict[str, Any]:
    """★判别力证明:把 schema 换成剥掉某个入参键的缺陷版,看逐字比对能否检出。

    按 declared_kind 取每类**首条** case(确定性),返回 {kind: {...}}。
    透出 sir 的前后取值 —— strip_amr_profile 下 SIR 由 R 变硬弃权要看得见。
    """
    out: dict[str, Any] = {}
    for spec in CASE_SPECS:
        kind = spec["declared_kind"]
        if kind in out:
            continue
        raw = spec["raw"]
        good = direct(raw)
        bad = via_schema(raw, model)
        out[kind] = {
            "case_id": spec["case_id"],
            "stripped_raw_keys": sorted(schema_roundtrip(raw, model)),
            "mismatched_fields": _mismatched_fields(good, bad),
            "direct_output_kind": good["report"]["output_kind"],
            "stripped_output_kind": bad["report"]["output_kind"],
            "direct_abstained": bool(good["report"]["abstained"]),
            "stripped_abstained": bool(bad["report"]["abstained"]),
            "direct_abstain_reasons": list(good["report"]["abstain_reasons"]),
            "stripped_abstain_reasons": list(bad["report"]["abstain_reasons"]),
            "direct_sir": good["report"]["sir"],
            "stripped_sir": bad["report"]["sir"],
        }
    return out


def legacy_stripping_probe() -> dict[str, Any]:
    """负对照 1:剥 smiles/sequence(历史缺陷复刻)。检出 {sm_activity, peptide_activity}。"""
    return stripping_probe(LegacyPredictRequest)


def amr_stripping_probe() -> dict[str, Any]:
    """负对照 2:剥 amr_profile。检出 {sir}(R→硬弃权)。"""
    return stripping_probe(AmrStrippingPredictRequest)


def negative_control_summary() -> dict[str, Any]:
    """汇总两条负对照,据实算出"判别力已获实证"的类别集合(顺序固定,确定性)。

    demonstrated_power_kinds       —— 至少被一条负对照检出的类(= 逐字比对对该类真有牙齿)。
    power_not_demonstrated_kinds   —— 两条都检不出的类。**措辞据实**:是"未获实证",
      不是"无判别力" —— {ood, no_model_species} 本就恒 fail-closed,"剥字段"这族负对照
      对它们无从发力,但逐字比对仍钉着"HTTP 不得在直调弃权处凭空造结论"。
    """
    probes = {name: stripping_probe(model) for name, model in NEGATIVE_CONTROLS.items()}
    all_kinds = sorted({spec["declared_kind"] for spec in CASE_SPECS})
    detected_by: dict[str, list[str]] = {}
    for kind in all_kinds:
        hits = [name for name, p in probes.items() if p[kind]["mismatched_fields"]]
        detected_by[kind] = hits
    return {
        "probes": probes,
        "detected_by_kind": detected_by,
        "demonstrated_power_kinds": [k for k in all_kinds if detected_by[k]],
        "power_not_demonstrated_kinds": [k for k in all_kinds if not detected_by[k]],
    }


# ===========================================================================
# 一致性套件
# ===========================================================================


def compare_case(spec: dict[str, Any], client: TestClient) -> dict[str, Any]:
    """单 case:HTTP vs 直调,科学字段 + task_id + prediction_available 逐字比对。"""
    raw = spec["raw"]
    http = via_http(raw, client)
    dir_ = direct(raw)
    mism = _mismatched_fields(http, dir_)
    return {
        "case_id": spec["case_id"],
        "declared_kind": spec["declared_kind"],
        "observed_shape": observed_shape(dir_),
        "schema_fixed_point": schema_roundtrip(raw) == raw,
        "task_id": dir_["task_id"],
        "task_id_match": http["task_id"] == dir_["task_id"],
        "prediction_available_match": (
            http["prediction_available"] == dir_["prediction_available"]),
        "prediction_available": dir_["prediction_available"],
        "mismatched_fields": mism,
        "match": not mism,
    }


def run_consistency_suite(client: TestClient | None = None) -> dict[str, Any]:
    """遍历 CASES,统计一致性(顺序按 CASE_SPECS 原序,确定性)。

    三类不一致各自统计:科学字段 / task_id / prediction_available。
    """
    c = client if client is not None else make_client()
    rows = [compare_case(spec, c) for spec in CASE_SPECS]

    mismatches = [r for r in rows if not r["match"]]
    task_id_mismatches = [r for r in rows if not r["task_id_match"]]
    pa_mismatches = [r for r in rows if not r["prediction_available_match"]]
    non_fixed_point = [r for r in rows if not r["schema_fixed_point"]]

    by_declared_kind: dict[str, int] = {}
    for r in rows:
        by_declared_kind[r["declared_kind"]] = by_declared_kind.get(r["declared_kind"], 0) + 1

    return {
        "n_case": len(rows),
        "n_mismatch": len(mismatches),
        "n_task_id_mismatch": len(task_id_mismatches),
        "n_prediction_available_mismatch": len(pa_mismatches),
        "n_non_fixed_point": len(non_fixed_point),
        "by_declared_kind": dict(sorted(by_declared_kind.items())),
        "mismatches": mismatches,
        "task_id_mismatches": task_id_mismatches,
        "cases": rows,
    }


# ===========================================================================
# 前端 fixture(后端真跑产出,可再生)
# ===========================================================================

_FIXTURE_HEADER = """\
// ⚠ 本文件由后端**真跑**产出,请勿手改。
// 再生:.venv/bin/python -m praxis_virtualcell.mdr_gnb.workflows.science_v2.validation.t7_e2e
// 来源:Phase11-T7(t7_e2e.emit_frontend_fixtures),内容 = POST /predict 的真实响应逐字快照。
// 用途:phase11.e2e.test.tsx 断言渲染层不丢字段/不造字段(渲染值一律由本 fixture 推导,
//       不写死字面量),故 fixture 变了断言跟着变 —— 验的是真实后端契约。
import type { CompoundActivityEvidence, PredictResponse } from "./types";

"""


def build_frontend_fixture_payload(client: TestClient | None = None) -> dict[str, Any]:
    """后端真跑:case_id → 完整 /predict 响应(HTTP 真实响应,非手写)。"""
    c = client if client is not None else make_client()
    return {spec["case_id"]: via_http(spec["raw"], c) for spec in CASE_SPECS}


def emit_frontend_fixtures(client: TestClient | None = None) -> Path:
    """把后端真实响应 + 模型级证据落成 TS fixture,供前端 vitest 用。

    **为何用 `as unknown as`(据实归因,实测 `tsc -b --force` 去掉断言后的真实报错)**:
    后端响应带若干前端 types.ts 未声明的字段(前端零消费,属正常的"响应字段多于前端所需",
    非缺陷)。tsconfig.app.json 的 include 覆盖 src/,直接写成带类型标注的对象字面量会触发
    TS2353 excess property check → 断 `npm run build`。实测报错分布:
      · `'"mic_range"' does not exist in type 'Report'`      —— **7 处,主因**
        (Report.mic_range 在 7 个 fixture 里**均为 null**,前端 types.ts:76-93 未声明)
      · `'"calibration_ece"' does not exist in type 'Evidence'` —— 3 处
        (3 个非空 evidence 各报 1 次;同一对象里 `t_star`/`n` 亦未声明,但 TS 每个字面量
         只报**第一个**多余属性,故仅 calibration_ece 现形)
    故经 `as unknown as` 断言。**代价要说清**:这样一来 tsc **不会**校验 fixture 与前端类型的
    一致性 —— 本文件不提供"契约漂移自动报错"的保障,契约由 phase11.e2e.test.tsx 的运行时断言守。
    (取舍:不改 types.ts —— 那是产品前端契约,不在本验证战役职责内。)
    确定性:sort_keys + 固定缩进,同输入逐字节相等。
    """
    c = client if client is not None else make_client()
    fixtures = build_frontend_fixture_payload(c)
    # 活性卡证据源(系统②·QSAR 验证层),前端 PredictionResult 的 compoundEvidence 入参
    compound_ev = service.models_summary()["compound_activity_evidence"]

    def _dump(obj: Any) -> str:
        return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2)

    body = (
        _FIXTURE_HEADER
        + "export const PHASE11_BACKEND_FIXTURES: Record<string, PredictResponse> =\n"
        + f"  {_dump(fixtures)} as unknown as Record<string, PredictResponse>;\n\n"
        + "// GET /models 的 compound_activity_evidence(活性卡证据源,系统②)\n"
        + "export const PHASE11_COMPOUND_EVIDENCE: CompoundActivityEvidence =\n"
        + f"  {_dump(compound_ev)} as unknown as CompoundActivityEvidence;\n"
    )
    FRONTEND_FIXTURE_PATH.write_text(body, encoding="utf-8")
    return FRONTEND_FIXTURE_PATH


# ===========================================================================
# 报告
# ===========================================================================


def _build_findings(suite: dict[str, Any]) -> list[dict[str, Any]]:
    """数据驱动生成顶层 findings(端到端不一致=产品缺陷)。全一致 → []。"""
    findings: list[dict[str, Any]] = []
    if suite["n_mismatch"]:
        findings.append({
            "id": "http_direct_science_mismatch",
            "severity": "red_line",
            "n_affected": suite["n_mismatch"],
            "detail": "经 HTTP 与直调的科学结论字段不一致(schema/序列化漏字段)",
            "cases": [m["case_id"] for m in suite["mismatches"]],
        })
    if suite["n_task_id_mismatch"]:
        findings.append({
            "id": "task_id_mismatch",
            "severity": "important",
            "n_affected": suite["n_task_id_mismatch"],
            "detail": "内容寻址 task_id 在两条路径下不等(to_raw() 规范化改写了 raw)",
            "cases": [m["case_id"] for m in suite["task_id_mismatches"]],
        })
    if suite["n_non_fixed_point"]:
        findings.append({
            "id": "case_not_schema_fixed_point",
            "severity": "important",
            "n_affected": suite["n_non_fixed_point"],
            "detail": "CASES 语料非 to_raw() 不动点,逐字比对前提不成立",
            "cases": [r["case_id"] for r in suite["cases"] if not r["schema_fixed_point"]],
        })
    return findings


def build_report() -> dict[str, Any]:
    """确定性组装 T7 报告 payload。路径用**相对仓库根**(绝对路径破坏跨机器字节一致)。"""
    client = make_client()
    suite = run_consistency_suite(client=client)
    neg = negative_control_summary()
    findings = _build_findings(suite)
    return {
        "suite": suite,
        "negative_controls": {
            **neg,
            "controls": {
                "strip_smiles_sequence": (
                    "LegacyPredictRequest:忠实复刻**修复前**的 schema(无 compound/smiles/"
                    "sequence)。剥离后 ciprofloxacin/magainin_2 双双 fail-closed 弃权 → "
                    "检出 {sm_activity, peptide_activity}。"
                ),
                "strip_amr_profile": (
                    "AmrStrippingPredictRequest:剥掉 SIR 真读的 amr_profile。剥离后两条 SIR "
                    "锚点从 R 变为硬弃权，证明缺失 profile 不会被静默解释成敏感 → 检出 {sir}。"
                ),
            },
            "note": (
                "两条负对照各剥掉 schema 的一个真实入参键,两侧 raw 的**唯一**差异就是被剥的"
                "那个键(因果干净,无混杂变量)。已获实证 3/5 类:{sir, sm_activity, "
                "peptide_activity}。未获实证 2 类:{ood, no_model_species} —— 二者本就恒 "
                "fail-closed,剥任何入参键都还是 fail-closed,故'剥字段'这族负对照对其无从发力。"
                "**措辞据实**:是'判别力未获实证',不等于'无判别力' —— 逐字比对仍钉着"
                "'HTTP 侧不得在直调弃权处凭空造出结论',只是本族负对照造不出那个反例。"
            ),
        },
        "paths": {
            "frontend_fixture": _FRONTEND_FIXTURE_REL,
            "frontend_test": "praxis_vc_react/src/mdr/phase11.e2e.test.tsx",
            "api_predict_endpoint": "praxis_virtualcell/mdr_gnb/api/app.py:64 (/predict)",
            "schema": "praxis_virtualcell/mdr_gnb/api/schemas.py:26 (PredictRequest.to_raw)",
        },
        "science_fields_compared": list(SCIENCE_FIELDS),
        "findings": findings,
        "n_findings": len(findings),
        "verdict": {
            "n_case": suite["n_case"],
            "n_mismatch": suite["n_mismatch"],
            "n_task_id_mismatch": suite["n_task_id_mismatch"],
            "task_id_identical": suite["n_task_id_mismatch"] == 0,
            "all_cases_schema_fixed_point": suite["n_non_fixed_point"] == 0,
            "e2e_science_consistent": (
                suite["n_mismatch"] == 0
                and suite["n_task_id_mismatch"] == 0
                and suite["n_prediction_available_mismatch"] == 0),
        },
        "note": (
            "两条路径只差一个 pydantic 往返(app.py:66 raw=body.to_raw())。CASES 每条均构造成 "
            "to_raw() 不动点(4 键补齐 + drug_class 显式),两侧才是同一个 raw、task_id 才可比 —— "
            "该前提由 test_cases_are_schema_fixed_points 显式断言。CASES 含真实 smiles/sequence,"
            "钉死 schema 剥离缺陷不回退。无模型物种(morganella_morganii)无成功 predictor 时，"
            "核心层必须 hard abstain 并报告 no_successful_predictor；不得以空而未弃权的形态兜底。"
        ),
    }


if __name__ == "__main__":
    payload = build_report()
    p = harness.write_report("t7_e2e", payload)
    fx = emit_frontend_fixtures()
    print(f"t7_e2e 报告写入 {p}")
    print(f"前端 fixture 写入 {fx.relative_to(_REPO_ROOT)}(后端真跑产出,勿手改)")
    s = payload["suite"]
    print(f"  case 数:{s['n_case']}  各类:{s['by_declared_kind']}")
    print(f"  科学字段不一致:{s['n_mismatch']}")
    print(f"  task_id 不一致:{s['n_task_id_mismatch']}")
    print(f"  prediction_available 不一致:{s['n_prediction_available_mismatch']}")
    print(f"  非不动点语料:{s['n_non_fixed_point']}")
    nc = payload["negative_controls"]
    print(f"  负对照 判别力已获实证:{nc['demonstrated_power_kinds']}")
    print(f"           未获实证(恒 fail-closed):{nc['power_not_demonstrated_kinds']}")
    for kind, hits in nc["detected_by_kind"].items():
        print(f"    · {kind:17s} ← {hits or '(本族负对照无从发力)'}")
    if payload["n_findings"]:
        print(f"  ⚠ findings({payload['n_findings']} 条):")
        for f in payload["findings"]:
            print(f"    - {f['id']}: {f['detail']}({f['n_affected']} 例)")
    print(f"  裁决 e2e_science_consistent={payload['verdict']['e2e_science_consistent']}")
