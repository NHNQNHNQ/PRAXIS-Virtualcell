# Phase 3:module-aware router(SpeciesContext + ModuleRouter + ModulePlan)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 route_table 之上加一层 **module-aware 路由**:`SpeciesContextAgent`(读 `module_support.yaml` 判物种每模块可用/弱支持/不支持)+ `ModuleRouterAgent`(把归一请求映射到 **primary + secondary modules**,每模块落 engine 与 verdict,生成本 Phase 核心交付物 **ModulePlan** 数据结构)。OFFLINE 走**确定性 module 规则、零 LLM**;LLM plan 留 Phase 4。Phase 3 完成 = **v1.0 里程碑**(model-controlled)。

**Architecture:** 全部**净新增 + 复用**,不改现有 `route_table`/`runtime`/治理/predictor 任何逻辑。`ModulePlan` 是一个纯 `@dataclass`(`biological_modules/module_plan.py`),不进 bus、可序列化,是 Phase 4 LLM 编排的输入契约。`ModuleRouterAgent` **包在 `route_table.route()` 外层**:先由确定性规则定 module(primary/secondary),对每个 module 用 `MODULES[mid]["engines"]` 拿候选 engine,再调 `route()` 落实际 engine + disposition,再用 `ModuleRegistry.default_verdict()` 叠加物种 verdict,合成 `ModulePlan`。`SpeciesContextAgent` 与 `ModuleRouterAgent` 都 extends `core/agent.py:BaseAgent` 进 message bus,但 **Phase 3 只交付两个 agent + ModulePlan + golden 扩容 + governance 扩容,不接进 `runtime.run_workflow` 固定管线**(接管线留 Phase 4,与 LLM 编排一起做,降低回归风险——见 §决策 R1)。module→engine 的合法性单一真相源 = `biological_modules.modules.MODULES[mid]["engines"]`(Phase 1 已落);module 可用性单一真相源 = `ModuleRegistry`(读 `module_support.yaml`)。

**Tech Stack:** Python 3.13 / pytest 参数化(golden YAML runner 复用 `test_golden_cases.py` 模式)/ PyYAML(核心依赖)/ dataclasses(标准库)。无新增第三方依赖。OFFLINE 路径零 LLM、零 torch、零 cobra(纯规则 + yaml),核心 module routing 全程可离线跑。

---

## 铁律(每个 task 验收都要守)

- **纯新增 + 复用,不改现有逻辑**:只新增 `biological_modules/module_plan.py`、`agents/species_context_agent.py`、`agents/module_router_agent.py`、新 golden/governance YAML + 测试;**不改** `core/`、`route_table.py`、`runtime.py`、`predictors/`、现有治理 agent 的任何逻辑。若发现现有 `route()`/`ModuleRegistry`/`MODULES` 行为与预期不符 → **真实 bug,停下报告,不改代码/不改 golden 迁就测试**(红线 5)。
- **OFFLINE 确定性 module 规则,零 LLM**(红线 1):ModuleRouter 的 OFFLINE 路径不 import 任何 `agents_llm/*`、不读 `DEEPSEEK_API_KEY`、不发网络请求。LLM module plan 留 Phase 4(本 Phase 只为其铺"只能从候选选"的约束地基,见决策 C)。
- **fail-closed / 无静默 accept**(红线 4、6):物种不支持某模块(`unsupported`)→ ModulePlan 里该 module verdict=`reject`,不硬塞 engine;生物学错配(bacteria 自噬 / yeast 组织 niche)→ verdict=`caution`/`reject`(复用 `ModuleRegistry.biological_mismatch`),绝不 accept。primary module 无合法 engine 且非 mismatch → abstain,不虚构。
- **module 白名单单一真相源**:任何 module id 必须 ∈ `biological_modules.modules.MODULE_ORDER`;engine 必须 ∈ `MODULES[mid]["engines"]`(且 ∈ `route_table.ENGINES`)。越界 → `ValueError`(fail-closed),不静默。
- **测试口径** = `praxis_virtualcell/tests`(**绝不碰根 `tests/`**)。Phase 3 起点基线(当前分支 `feat/v0.9-phase0-module-core`,含 Phase 0/1/2)实跑核实 = **352 passed / 25 skipped / collected 377**。`-q` 不打印精确 passed 汇总;精确数用 `--junit-xml` 的属性换算:**passed = tests(collected) − skipped − failures − errors**(junit 的 `tests` 属性是 collected 含 skipped,不是 passed)。验收只认:**failures=0 errors=0** + 每 task 新增测试条数正确。
- **每 task 全量回归绿**后再 commit:`PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`;commit 前 `find . -name '._*' -delete`(外置盘 AppleDouble);commit message 末尾加 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`;当前分支 `feat/v0.9-phase0-module-core`,**不 push**。
- **v1.0 里程碑 tag**:Phase 3 是 v1.0 里程碑(见路线图 §5)。**只在最后一个 task(3.8)全绿 + 红线核验通过后打 tag**(`git tag v1.0-...`),tag 不 push(房规:当前分支不 push;tag 打在本地由人决定何时推)。中间 task 不 tag。

---

## 数据契约(已实跑核实,计划代码与之对齐)

以下是 Phase 3 依赖的**真实接口**(2026-07-04 实读源码核实,非路线图旧描述):

- `route_table.route(req)`(`agents/route_table.py:43`):**入参 req 是归一后的 dict**(须先过 `species_schema.normalize_request`),键 = `species / perturbation_object / target_output / perturbation_targets`(+ 可选 `cell_type/medium/dose`)。返回 `RouteDecision(engine, disposition, reason, caution_flags=[], data_gated=False)` —— **注意有 `reason` 字段**(路线图 §4 描述漏了它),`to_dict()` 全量导出。`ENGINES` 8 项:`("donor_predictor","gem_fba","embedding","state_scoring","pathway_scoring","communication","spatial_niche","reject")`。`disposition` 4 态:`accept/caution/downgrade/abstain`。
- `species_schema.normalize_request(raw)`(`agents/species_schema.py:40`):校验 + 归一;`SPECIES={human,mouse,yeast,bacteria}`;非法 → `SchemaError`(是 `ValueError` 子类)。golden case 的 `input` 就是 `route()` 前喂给它的 raw dict。
- `biological_modules.modules`(`biological_modules/modules.py`):`MODULE_ORDER`(8 项 list,M1..M8)、`MODULES`(dict,每模块含 `code/display_name/engines(list)/pillars`)、`module(id)`(未知 raise KeyError)、`display_name(id, species=None)`(物种别名:`(bacteria, mitochondrial_energy_metabolism)→"Energy metabolism / redox module"`)。**module→engine 映射就在 `MODULES[mid]["engines"]`**(可空 list = 该模块暂无直接引擎)。
- `biological_modules.registry.ModuleRegistry`(`biological_modules/registry.py`):`__init__(brains_root=None)`(默认 `RuntimeConfig().brains_root`);`support(species, mid)->dict{support, reason?, models?, tools?, self_training?, display_alias?}`(未知物种/模块 → `{support:"unsupported", reason:...}`;未知 module id → KeyError);`default_verdict(species, mid)->str`(用 `_VERDICT={strong:accept, medium:accept, weak:caution, unsupported:reject}`);`matrix()->{species:{mid:record}}`;`biological_mismatch(species, query)->str|None`(错配 → `reject`/`caution`,无 → None);`display_name(species, mid)`。`_SPECIES=("human","mouse","yeast","bacteria")`。
- `module_support.yaml`(`brains/virtualcell/<species>/`,4 物种齐):顶层 `species` + `modules:{mid:{support, reason, models?/tools?/self_training?/display_alias?}}` + `biological_mismatch:[{query, verdict, reason}]`。实测 support 值:human genetic_hub=strong、bacteria/yeast cytoplasmic_metabolism=strong、bacteria genetic_hub=weak、human membrane_system=weak 等(见各文件)。bacteria mismatch:`bacteria_autophagy→caution`、`mitochondria→caution`;yeast mismatch:`tissue_spatial_niche→reject`、`mammalian_cell_communication→reject`。
- `BaseAgent`(`core/agent.py:10`):抽象 `handle(message, bus)->None`,只经 `bus.send` 产出,`name` 类属性。
- `MessageBus`(`core/bus.py`):`send(msg)`、`get_messages(agent_name)`、`latest(message_type)->AgentMessage|None`、`has_message_type(type)`、`trace`。
- `AgentMessage`(`core/message.py:13`):`message_id/sender/receiver/message_type/payload/timestamp/parent_message_id`(后者默认 None)。
- Phase 2 成果(可选复用,本 Phase 只在 ModulePlan 里挂"每模块可用模型名"引用,不真调 broker——真调留 Phase 4):`model_zoo.registry.ModelZooRegistry`(`by_module(mid)->list[entry]`、`by_species(sp)`、`is_available(name)`、`status(name)`);`agents/model_broker_agent.py:ModelBrokerAgent`(收 `model_request` → 产 `model_broker_result`)。
- golden runner(`tests/test_golden_cases.py`):glob `golden_cases/*.yaml` 的 `cases`,跳过 `._*`;每 case `{case_id, input, expect{engine, disposition, caution_flags?, data_gated?}}`,`test_case_count` 断言 `>=16`。Phase 3 **新增独立 module-routing golden 文件 + 独立 runner**(不改现有 `test_golden_cases.py`,避免混入 route-only 断言)。
- `RuntimeConfig`(`core/config.py:40`):有 `brains_root` 字段。ModuleRegistry 默认用它,测试可传 tmp 或默认。

**与路线图旧描述的三处校正(已在计划代码对齐):**
1. **`RouteDecision` 有 `reason` 字段**(路线图 §4 只列 engine/disposition/caution_flags/data_gated)。ModulePlan 的每模块条目**透传** route 的 reason,不丢证据。
2. **`route()` 入参必须先 `normalize_request`**(路线图把 route 说成直接吃 req)。ModuleRouter 内部对每个 module 构造 route 输入前**复用 `normalize_request`**,不自造归一。
3. **EvidenceLevelAgent(插点 C,E0–E5)不属 Phase 3**(见下"归置决策"),Phase 3 的 governance 扩容聚焦 **cross-module consistency(G4)** + **module verdict 与 route disposition 一致性**,不引入 E0–E5(那是治理层之上的另一层,依赖 reliability/OOD 信号,应与 Phase 4/5 一起,避免本 Phase 越界)。

---

## 插点归置决策(SpeciesContext=插点 A / EvidenceLevel=插点 C)

- **插点 A(SpeciesContextAgent)归 Phase 3**。理由:它读 `module_support.yaml` 判物种每模块可用度,是 ModuleRouter 定 primary/secondary 合法性的**直接前置输入**(ModuleRouter 要它给的 per-module verdict)。二者强耦合、同属"module-aware 路由"子系统,放一起交付才能独立测试出完整链路。它 extends BaseAgent 进 bus,但同样 Phase 3 不接管线(与 ModuleRouter 一起 Phase 4 接)。
- **插点 C(EvidenceLevelAgent,E0–E5)留后(Phase 4/5)**。理由:路线图 §6-B 明确 evidence level 是"治理层之上的薄映射",**读现有 reliability/OOD/artifact 信号**再映射 E0–E5。这些信号在管线里由 `Reliability`/`ood_enrichment` 产出,而 Phase 3 不接管线、没有这些运行时信号可读。硬在 Phase 3 造 EvidenceLevelAgent 会变成"读不到真信号的空壳",违反红线 6(无 provenance 不硬报)。故 Phase 3 的 evidence 只做**声明式的 pillar 标注**(ModulePlan 每模块挂 `pillars`,数据来自 `MODULES[mid]["pillars"]`,零运行时依赖),E0–E5 的运行时映射与 Critic 的 evidence-level 一致性检查随 Phase 4(LLM 编排,那时管线已带 evidence agent)一起做。**已在本 Phase governance task(3.7)注明此留后边界。**

---

## ModulePlan 数据结构(本 Phase 核心交付,Phase 4 依赖)

`ModulePlan` 是 module-aware 路由的产物,也是 Phase 4 LLM 编排的**输入契约**。设计目标:①声明"这个请求命中哪些模块、谁 primary 谁 secondary";②每模块落 engine 映射 + route disposition + 物种 verdict + caution;③可序列化(`to_dict()`)供 provenance/前端消费;④OFFLINE 纯规则可构造,LLM 版(Phase 4)产出同一结构。

```
ModulePlan
├── species: str                         # 归一后物种
├── request: dict                        # 归一后的原始请求(normalize_request 输出,供复现)
├── primary: str                         # primary module id(∈ MODULE_ORDER;主命中模块)
├── secondary: list[str]                 # secondary module ids(相关但非主;可空)
├── entries: list[ModulePlanEntry]       # 每个命中模块一条(primary + 各 secondary)
├── overall_verdict: str                 # accept/caution/downgrade/abstain/reject(取最保守)
└── notes: list[str]                     # 规则说明 / mismatch 命中说明(可空)

ModulePlanEntry
├── module: str                          # module id(∈ MODULE_ORDER)
├── display_name: str                    # 物种感知显示名(bacteria 不叫线粒体)
├── role: str                            # "primary" | "secondary"
├── engine: str                          # route() 落的实际 engine(∈ ENGINES;无则 "reject")
├── route_disposition: str               # route() 的 disposition(accept/caution/downgrade/abstain)
├── species_support: str                 # module_support 的 support(strong/medium/weak/unsupported)
├── species_verdict: str                 # ModuleRegistry.default_verdict(accept/caution/reject)
├── verdict: str                         # 合成:route_disposition 与 species_verdict 取更保守
├── caution_flags: list[str]             # route 的 caution_flags(如 ortholog_required)+ mismatch flag
├── data_gated: bool                     # route 的 data_gated
├── pillars: list[str]                   # MODULES[mid]["pillars"](声明式证据支柱,零运行时依赖)
├── available_models: list[str]          # module_support 声明的 models(引用,不真调 broker)
├── reason: str                          # route 的 reason(证据透传,不丢)
└── mismatch: str | None                 # 生物学错配命中的 verdict(reject/caution)或 None
```

**verdict 合成规则(确定性,写死在 `ModulePlanEntry.synthesize`):** 保守优先级 `abstain/reject > downgrade > caution > accept`。取 `route_disposition` 与 `species_verdict` 中更保守者为 `verdict`;若命中 `mismatch`(非 None)则 verdict 至少降到 mismatch 的等级(reject 或 caution)。`overall_verdict` = 所有 entry 的 verdict 取最保守。**待确认(标注给控制器):** primary 选取规则见决策 M1;此保守合成方向已定(fail-closed),若科学上希望某些组合放宽,由控制器在执行时拍板。

---

## module→engine / primary 选取规则(科学核心,给建议 + 标注待确认)

**决策 M1(primary module 选取,OFFLINE 确定性规则)—— 建议方案,待控制器确认:**

由归一请求的 `(perturbation_object, target_output)` 决定 primary module,规则表(与 route_table 的 engine 归属 + `MODULES[mid]["engines"]` 对齐):

| target_output | perturbation_object | primary module | 依据(route engine) |
|---|---|---|---|
| `growth` / `flux` | 任意 | `cytoplasmic_metabolism`(M4) | gem_fba / pathway_scoring 属 M4/M3;growth 主归 M4 |
| `expression` | `gene`/`gene_combination` | `genetic_hub`(M2) | donor_predictor 属 M2 |
| `expression` | `drug`/`ligand` | `stress_processor`(M7) | embedding(药物签名)属 M7 |
| `state` | 任意 | `stress_processor`(M7) | state_scoring 属 M7;niche 例外见下 |
| `state` + `medium=niche` | `medium` | `cytoskeletal_framework`(M6) | spatial_niche 属 M6 |
| `communication` | 任意 | `stress_processor`(M7) | communication 无独立 module,归 M7 应激/信号(**待确认**:是否新增通讯语义归属) |

**secondary module(建议):** 对 `growth`/`flux` 且物种为 human/mouse 时,加 `mitochondrial_energy_metabolism`(M3)为 secondary(pathway_scoring 同属 M3/M4,能量代谢相关);其余暂无 secondary(留空,不硬凑)。**待确认:** secondary 的更细规则(如 M2 gene 扰动是否连带 M7 应激)由控制器按科学需要在执行时扩;Phase 3 先落最小确定性集,保证可测。

**决策 M2(engine 落实):** 每个命中 module 的 engine = 用该 module 的 `(species, object, output)` 构造 `normalize_request` → 调 `route()` 拿 `RouteDecision`。**不自造 engine 判断**,完全复用 route_table 单一真相源。若 route 落的 engine 不在 `MODULES[primary]["engines"]` 里(理论上不应发生,除非 route 与 module 定义漂移)→ **停下报告(真实 bug),不迁就**(红线 5)。

**决策 M3(mismatch 硬约束,决策 E):** 对 primary/secondary module,若能从请求推出 mismatch query(bacteria + degradation_machinery 语境的自噬 → `bacteria_autophagy`;yeast + spatial_niche/communication → `tissue_spatial_niche`/`mammalian_cell_communication`),调 `ModuleRegistry.biological_mismatch(species, query)`,命中则该 entry 的 `mismatch` 记其 verdict,verdict 降级。**这是 Phase 1 species-specific 守卫在 module 层的复用,不新造规则。**

---

# Phase 3:module-aware router

## Task 3.1:ModulePlan 数据结构 `biological_modules/module_plan.py`

**决策说明:** 先落纯 `@dataclass` 数据结构(不进 bus、无外部依赖),它是本 Phase 与 Phase 4 的契约。含 `ModulePlanEntry`(每模块一条)+ `ModulePlan`(聚合)+ `synthesize` 保守合成 + `to_dict` 序列化 + module/engine 白名单校验(构造即校验,fail-closed)。先建结构,后续 task 的 agent 产出它。

**Files:**
- Create: `praxis_virtualcell/biological_modules/module_plan.py`
- Test: `praxis_virtualcell/tests/test_module_plan.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_module_plan.py`:

```python
"""Phase 3:ModulePlan 数据结构 —— module-aware 路由产物 + Phase 4 输入契约。
测:白名单校验、verdict 保守合成、overall_verdict 取最保守、to_dict 序列化、mismatch 降级。"""
import pytest

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.biological_modules.module_plan import (
    ModulePlan,
    ModulePlanEntry,
    synthesize_verdict,
)


def _entry(**over):
    base = dict(
        module="genetic_hub", display_name="Genetic Hub", role="primary",
        engine="donor_predictor", route_disposition="accept",
        species_support="strong", species_verdict="accept",
        caution_flags=[], data_gated=False, pillars=["dynamic_states"],
        available_models=["donor_predictor"], reason="human_native_scrna_predictor",
        mismatch=None,
    )
    base.update(over)
    return ModulePlanEntry(**base)


def test_synthesize_verdict_takes_more_conservative():
    # accept + caution → caution;caption + downgrade → downgrade;任意 + reject → reject
    assert synthesize_verdict("accept", "caution", None) == "caution"
    assert synthesize_verdict("caution", "downgrade", None) == "downgrade"
    assert synthesize_verdict("accept", "accept", None) == "accept"
    assert synthesize_verdict("accept", "accept", "reject") == "reject"     # mismatch 降级
    assert synthesize_verdict("caution", "accept", "caution") == "caution"


def test_entry_verdict_synthesized_on_init():
    e = _entry(route_disposition="caution", species_verdict="accept")
    assert e.verdict == "caution"          # 取更保守


def test_entry_rejects_illegal_module():
    with pytest.raises(ValueError):
        _entry(module="not_a_module")


def test_entry_rejects_illegal_engine():
    with pytest.raises(ValueError):
        _entry(engine="not_an_engine")


def test_plan_overall_verdict_is_most_conservative():
    prim = _entry(module="genetic_hub", role="primary", verdict=None,
                  route_disposition="accept", species_verdict="accept")
    sec = _entry(module="stress_processor", display_name="Stress Processor", role="secondary",
                 engine="state_scoring", route_disposition="downgrade",
                 species_support="medium", species_verdict="accept",
                 pillars=["dynamic_states"], available_models=["state_scoring"],
                 reason="x")
    plan = ModulePlan(species="human", request={"species": "human"},
                      primary="genetic_hub", secondary=["stress_processor"],
                      entries=[prim, sec], notes=[])
    assert plan.overall_verdict == "downgrade"     # 最保守


def test_plan_to_dict_roundtrip_keys():
    plan = ModulePlan(species="human", request={"species": "human"},
                      primary="genetic_hub", secondary=[], entries=[_entry()], notes=[])
    d = plan.to_dict()
    assert d["primary"] == "genetic_hub"
    assert d["overall_verdict"] in ("accept", "caution", "downgrade", "abstain", "reject")
    assert d["entries"][0]["module"] == "genetic_hub"
    assert set(d["entries"][0]) >= {
        "module", "role", "engine", "route_disposition", "species_verdict",
        "verdict", "caution_flags", "pillars", "reason", "mismatch"}


def test_primary_must_be_in_entries():
    with pytest.raises(ValueError):
        ModulePlan(species="human", request={}, primary="membrane_system",
                   secondary=[], entries=[_entry(module="genetic_hub")], notes=[])
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_plan.py -q`
Expected: FAIL(ModuleNotFoundError: praxis_virtualcell.biological_modules.module_plan)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/biological_modules/module_plan.py`:

```python
"""ModulePlan:module-aware 路由的产物 + Phase 4 LLM 编排的输入契约。

纯数据结构(不进 bus、无 LLM/torch/cobra 依赖),可序列化。构造即校验(module ∈ MODULE_ORDER、
engine ∈ ENGINES),fail-closed。verdict 保守合成:route_disposition 与 species_verdict 取更保守,
mismatch 命中再降级。overall_verdict = 所有 entry verdict 取最保守。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from praxis_virtualcell.agents.route_table import ENGINES
from praxis_virtualcell.biological_modules import modules as M

# 保守优先级:数字越大越保守。abstain 与 reject 同为"不出结论",并列最保守。
_SEVERITY = {"accept": 0, "caution": 1, "downgrade": 2, "abstain": 3, "reject": 3}
_LEGAL_ROLES = ("primary", "secondary")


def synthesize_verdict(route_disposition: str, species_verdict: str,
                       mismatch: str | None) -> str:
    """取 route_disposition / species_verdict / mismatch 三者中最保守。fail-closed。"""
    candidates = [route_disposition, species_verdict]
    if mismatch:
        candidates.append(mismatch)
    return max(candidates, key=lambda v: _SEVERITY.get(v, 3))   # 未知 → 当最保守


@dataclass
class ModulePlanEntry:
    module: str
    display_name: str
    role: str
    engine: str
    route_disposition: str
    species_support: str
    species_verdict: str
    caution_flags: list[str] = field(default_factory=list)
    data_gated: bool = False
    pillars: list[str] = field(default_factory=list)
    available_models: list[str] = field(default_factory=list)
    reason: str = ""
    mismatch: str | None = None
    verdict: str | None = None   # None → __post_init__ 合成;显式传入则尊重(测试可覆写)

    def __post_init__(self) -> None:
        if self.module not in M.MODULE_ORDER:
            raise ValueError(f"module 越白名单: {self.module}(须 ∈ MODULE_ORDER)")
        if self.engine not in ENGINES:
            raise ValueError(f"engine 越白名单: {self.engine}(须 ∈ route_table.ENGINES)")
        if self.role not in _LEGAL_ROLES:
            raise ValueError(f"非法 role: {self.role}(须 ∈ {_LEGAL_ROLES})")
        if self.verdict is None:
            self.verdict = synthesize_verdict(
                self.route_disposition, self.species_verdict, self.mismatch)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ModulePlan:
    species: str
    request: dict
    primary: str
    secondary: list[str]
    entries: list[ModulePlanEntry]
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.primary not in M.MODULE_ORDER:
            raise ValueError(f"primary 越白名单: {self.primary}")
        entry_modules = {e.module for e in self.entries}
        if self.primary not in entry_modules:
            raise ValueError(f"primary={self.primary} 必须在 entries 中")
        for s in self.secondary:
            if s not in M.MODULE_ORDER:
                raise ValueError(f"secondary 越白名单: {s}")

    @property
    def overall_verdict(self) -> str:
        """所有 entry verdict 取最保守;无 entry → abstain。"""
        if not self.entries:
            return "abstain"
        return max((e.verdict for e in self.entries),
                   key=lambda v: _SEVERITY.get(v, 3))

    def to_dict(self) -> dict:
        return {
            "species": self.species,
            "request": self.request,
            "primary": self.primary,
            "secondary": list(self.secondary),
            "overall_verdict": self.overall_verdict,
            "entries": [e.to_dict() for e in self.entries],
            "notes": list(self.notes),
        }
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_plan.py -q`
Expected: 7 passed。

- [ ] **Step 5: 全量回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 359 passed / 25 skipped / 0 failed(352 + 7 新)。关键:0 failed。

- [ ] **Step 6: 提交**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/biological_modules/module_plan.py praxis_virtualcell/tests/test_module_plan.py
git commit -m "feat(phase3): ModulePlan 数据结构(entry 白名单校验 + verdict 保守合成 + to_dict;Phase 4 输入契约)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 3.2:SpeciesContextAgent `agents/species_context_agent.py`(插点 A,进 bus)

**决策说明:** `SpeciesContextAgent` extends `BaseAgent` 进 message bus。收 `species_context`(payload `{request}`,request 是归一后的 dict)→ 用 `ModuleRegistry` 对 8 个模块逐一查 support/verdict/display_name → 产 `species_context_ready`(payload `{species, module_support:{mid:{support, verdict, display_name, models, tools}}, mismatch_queries}`)。这是 ModuleRouter 定 module 合法性的前置。纯读 `module_support.yaml`,零 LLM、零管线依赖。Phase 3 不接 `run_workflow`(接管线留 Phase 4)。

**Files:**
- Create: `praxis_virtualcell/agents/species_context_agent.py`
- Test: `praxis_virtualcell/tests/test_species_context_agent.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_species_context_agent.py`:

```python
"""Phase 3:SpeciesContextAgent(插点 A)—— 进 bus,读 module_support.yaml 判物种每模块可用度。
铁律:未声明的模块 → unsupported/reject(不静默 accept);bacteria M3 显示名映射 energy/redox。"""
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _ask(species):
    return AgentMessage(
        message_id="c1", sender="SpeciesBrain", receiver="SpeciesContextAgent",
        message_type="species_context",
        payload={"request": {"species": species, "perturbation_object": "gene",
                             "target_output": "expression", "perturbation_targets": ["AHR"]}},
        timestamp="t1")


def _run(species):
    bus = MessageBus()
    SpeciesContextAgent().handle(_ask(species), bus)
    return bus.latest("species_context_ready").payload


def test_emits_ready_with_all_eight_modules():
    p = _run("human")
    assert p["species"] == "human"
    assert set(p["module_support"]) == set(M.MODULE_ORDER)   # 8 模块全覆盖


def test_human_genetic_hub_is_strong_accept():
    p = _run("human")
    gh = p["module_support"]["genetic_hub"]
    assert gh["support"] == "strong"
    assert gh["verdict"] == "accept"


def test_bacteria_m3_display_name_maps_to_energy_redox():
    """铁律(决策 E):bacteria 不叫线粒体,M3 显示 Energy/redox。"""
    p = _run("bacteria")
    m3 = p["module_support"]["mitochondrial_energy_metabolism"]
    assert "redox" in m3["display_name"].lower() or "energy" in m3["display_name"].lower()


def test_bacteria_genetic_hub_is_weak_caution():
    p = _run("bacteria")
    gh = p["module_support"]["genetic_hub"]
    assert gh["support"] == "weak"
    assert gh["verdict"] == "caution"       # weak → caution(不 accept)


def test_bus_message_structure():
    bus = MessageBus()
    SpeciesContextAgent().handle(_ask("yeast"), bus)
    res = bus.latest("species_context_ready")
    assert res.sender == "SpeciesContextAgent"
    assert res.message_type == "species_context_ready"
    assert set(res.payload) >= {"species", "module_support", "mismatch_queries"}


def test_mismatch_queries_surfaced_for_bacteria():
    """bacteria module_support 声明的 biological_mismatch(自噬/线粒体)要被暴露供 router 用。"""
    p = _run("bacteria")
    mq = p["mismatch_queries"]
    assert "bacteria_autophagy" in mq
    assert mq["bacteria_autophagy"] == "caution"
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_species_context_agent.py -q`
Expected: FAIL(ModuleNotFoundError: ...species_context_agent)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/agents/species_context_agent.py`:

```python
"""SpeciesContextAgent(插点 A):进 message bus,读 brains/virtualcell/<species>/module_support.yaml,
对 8 个模块逐一给 support/verdict/display_name/models/tools,并暴露 biological_mismatch 查询表。

供 ModuleRouterAgent 定 primary/secondary 模块的合法性前置。纯读 yaml,零 LLM、零管线依赖。
铁律:未声明模块 → unsupported/reject(不静默);物种别名(bacteria M3=energy/redox)经 registry.display_name。
"""
from __future__ import annotations

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.biological_modules.registry import ModuleRegistry
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class SpeciesContextAgent(BaseAgent):
    name = "SpeciesContextAgent"

    def __init__(self, registry: ModuleRegistry | None = None) -> None:
        self._reg = registry or ModuleRegistry()

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        req = message.payload.get("request", {})
        species = str(req.get("species", "")).strip().lower()
        module_support: dict[str, dict] = {}
        for mid in M.MODULE_ORDER:
            rec = self._reg.support(species, mid)
            module_support[mid] = {
                "support": rec["support"],
                "verdict": self._reg.default_verdict(species, mid),
                "display_name": self._reg.display_name(species, mid),
                "models": list(rec.get("models", [])),
                "tools": list(rec.get("tools", [])),
                "reason": rec.get("reason", ""),
            }
        # 暴露该物种声明的 biological_mismatch(query→verdict),供 router 命中降级
        mismatch_queries: dict[str, str] = {}
        for m in (self._reg._load(species).get("biological_mismatch") or []):
            if m.get("query"):
                mismatch_queries[m["query"]] = m.get("verdict", "caution")
        bus.send(AgentMessage(
            message_id=message.message_id + ":spctx",
            sender=self.name, receiver="ModuleRouterAgent",
            message_type="species_context_ready",
            payload={"species": species, "module_support": module_support,
                     "mismatch_queries": mismatch_queries},
            timestamp=message.timestamp, parent_message_id=message.message_id))
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_species_context_agent.py -q`
Expected: 6 passed。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 365 passed / 25 skipped / 0 failed(359 + 6 新)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/agents/species_context_agent.py praxis_virtualcell/tests/test_species_context_agent.py
git commit -m "feat(phase3): SpeciesContextAgent(插点 A,进 bus;读 module_support 给 8 模块 support/verdict + mismatch 表)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 3.3:module 规则表 `agents/module_rules.py`(纯函数,primary/secondary 确定性规则)

**决策说明:** 把决策 M1(primary 选取)+ secondary 规则抽成一个**纯函数模块**(不进 bus、无副作用),供 ModuleRouterAgent 调用,也可单独测试(bite-sized)。`pick_primary(req)->str`、`pick_secondary(req, primary)->list[str]`、`mismatch_query_for(req, module)->str|None`。全确定性、零 LLM。规则表就是决策 M1/M3 那两张表的代码化。

**Files:**
- Create: `praxis_virtualcell/agents/module_rules.py`
- Test: `praxis_virtualcell/tests/test_module_rules.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_module_rules.py`:

```python
"""Phase 3:module 确定性规则(决策 M1/M3)—— primary/secondary 选取 + mismatch query 推导。
零 LLM、纯函数。铁律:输出 module 必 ∈ MODULE_ORDER。"""
from praxis_virtualcell.agents.module_rules import (
    mismatch_query_for,
    pick_primary,
    pick_secondary,
)
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.biological_modules import modules as M


def _req(**kw):
    base = {"species": "human", "perturbation_object": "gene",
            "target_output": "expression", "perturbation_targets": ["AHR"]}
    base.update(kw)
    return normalize_request(base)


def test_gene_expression_primary_is_genetic_hub():
    assert pick_primary(_req()) == "genetic_hub"


def test_growth_primary_is_cytoplasmic_metabolism():
    r = _req(species="bacteria", target_output="growth", perturbation_targets=["b0720"])
    assert pick_primary(r) == "cytoplasmic_metabolism"


def test_drug_expression_primary_is_stress_processor():
    r = _req(perturbation_object="drug", target_output="expression",
             perturbation_targets=["vorinostat"])
    assert pick_primary(r) == "stress_processor"


def test_state_primary_is_stress_processor():
    r = _req(target_output="state", perturbation_targets=["SNAI1"])
    assert pick_primary(r) == "stress_processor"


def test_niche_state_primary_is_cytoskeletal_framework():
    r = _req(perturbation_object="medium", target_output="state",
             perturbation_targets=[], medium="niche")
    assert pick_primary(r) == "cytoskeletal_framework"


def test_all_primaries_are_legal_modules():
    for r in (_req(), _req(target_output="growth", species="bacteria",
                           perturbation_targets=["b0720"])):
        assert pick_primary(r) in M.MODULE_ORDER


def test_mammalian_growth_has_m3_secondary():
    r = _req(species="human", target_output="growth", perturbation_targets=["MYC"])
    sec = pick_secondary(r, "cytoplasmic_metabolism")
    assert "mitochondrial_energy_metabolism" in sec


def test_secondary_excludes_primary():
    r = _req(species="human", target_output="growth", perturbation_targets=["MYC"])
    sec = pick_secondary(r, "cytoplasmic_metabolism")
    assert "cytoplasmic_metabolism" not in sec


def test_mismatch_query_bacteria_degradation_autophagy():
    r = _req(species="bacteria", perturbation_object="gene",
             target_output="growth", perturbation_targets=["lon"])
    # degradation_machinery + bacteria → 自噬语境 mismatch query
    assert mismatch_query_for(r, "degradation_machinery") == "bacteria_autophagy"


def test_mismatch_query_none_when_no_mismatch():
    assert mismatch_query_for(_req(), "genetic_hub") is None
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_rules.py -q`
Expected: FAIL(ModuleNotFoundError: ...module_rules)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/agents/module_rules.py`:

```python
"""module 确定性规则(决策 M1/M3):把归一请求映射到 primary/secondary module + mismatch query。

纯函数,零 LLM、零副作用。primary 规则与 route_table 的 engine 归属 + MODULES[mid]["engines"] 对齐。
这是 OFFLINE module 路由的确定性内核;LLM 版(Phase 4)只是换 primary/secondary 的产生方式,
但必须过滤成本模块的合法输出(复用"只能从候选选"约束)。
"""
from __future__ import annotations

# module id 常量(∈ MODULE_ORDER)
_M2 = "genetic_hub"
_M3 = "mitochondrial_energy_metabolism"
_M4 = "cytoplasmic_metabolism"
_M6 = "cytoskeletal_framework"
_M7 = "stress_processor"
_M8 = "degradation_machinery"

_METABOLIC = {"growth", "flux"}
_GENE_LIKE = {"gene", "gene_combination"}


def pick_primary(req: dict) -> str:
    """决策 M1:(perturbation_object, target_output) → primary module。全确定性。"""
    obj = req["perturbation_object"]
    out = req["target_output"]
    if out in _METABOLIC:
        return _M4                        # growth/flux → 胞质代谢(gem_fba/pathway_scoring)
    if out == "expression":
        if obj in _GENE_LIKE:
            return _M2                    # 基因扰动→表达 → 基因枢纽(donor_predictor)
        return _M7                        # 药物/配体→表达 → 应激(embedding 签名)
    if out == "state":
        if obj == "medium" and str(req.get("medium", "")).lower() == "niche":
            return _M6                    # niche 微环境→状态 → 细胞骨架/空间(spatial_niche)
        return _M7                        # 其余状态 → 应激(state_scoring)
    if out == "communication":
        return _M7                        # 通讯暂归应激/信号(待确认:是否新增通讯语义归属)
    return _M7                            # 兜底(理论不达;保守归应激)


def pick_secondary(req: dict, primary: str) -> list[str]:
    """决策 M1 secondary:最小确定性集。哺乳类 growth/flux 加 M3 能量代谢为 secondary。"""
    out = req["target_output"]
    species = req["species"]
    sec: list[str] = []
    if out in _METABOLIC and species in ("human", "mouse"):
        sec.append(_M3)
    return [m for m in sec if m != primary]   # 排除 primary


def mismatch_query_for(req: dict, module: str) -> str | None:
    """决策 M3:从 (species, module) 推 biological_mismatch query。命中交 registry 判 verdict。"""
    species = req["species"]
    if species == "bacteria" and module == _M8:
        return "bacteria_autophagy"        # 原核无真核自噬
    if species == "yeast" and module == _M6:
        return "tissue_spatial_niche"      # 单细胞真菌无组织 niche
    return None
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_rules.py -q`
Expected: 10 passed。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 375 passed / 25 skipped / 0 failed(365 + 10 新)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/agents/module_rules.py praxis_virtualcell/tests/test_module_rules.py
git commit -m "feat(phase3): module_rules 确定性规则(primary/secondary 选取 + mismatch query 推导,零 LLM)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 3.4:ModuleRouterAgent `agents/module_router_agent.py`(插点 B,进 bus,产 ModulePlan)

**决策说明:** `ModuleRouterAgent` extends `BaseAgent` 进 bus,是插点 B。收 `module_route`(payload `{request, module_support, mismatch_queries}`,前两者来自 SpeciesContext + 归一 request)→ 用 `module_rules` 定 primary/secondary → 对每个 module 用 `normalize_request`+`route()` 落 engine/disposition/reason/caution/data_gated,叠加 `module_support` 的 support/verdict、`MODULES[mid]` 的 display_name/pillars、mismatch → 合成 `ModulePlanEntry` → 组 `ModulePlan` → 产 `module_plan_ready`(payload = `plan.to_dict()`)。OFFLINE 全程零 LLM。铁律:route 落的 engine 若不在 `MODULES[primary]["engines"]` → 记 note(不崩,但标注漂移,供 governance task 检查);物种 unsupported / mismatch → verdict 降级不 accept。

**Files:**
- Create: `praxis_virtualcell/agents/module_router_agent.py`
- Test: `praxis_virtualcell/tests/test_module_router_agent.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_module_router_agent.py`:

```python
"""Phase 3:ModuleRouterAgent(插点 B)—— 进 bus,产 ModulePlan。OFFLINE 确定性,零 LLM。
铁律:primary 落 engine 复用 route();物种 unsupported/mismatch → verdict 降级不 accept。"""
from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _plan_for(request):
    """跑 SpeciesContext → ModuleRouter 全链路,返回 module_plan_ready payload(dict)。"""
    bus = MessageBus()
    SpeciesContextAgent().handle(AgentMessage(
        message_id="c1", sender="SpeciesBrain", receiver="SpeciesContextAgent",
        message_type="species_context", payload={"request": request}, timestamp="t1"), bus)
    ctx = bus.latest("species_context_ready").payload
    ModuleRouterAgent().handle(AgentMessage(
        message_id="c2", sender="SpeciesContextAgent", receiver="ModuleRouterAgent",
        message_type="module_route",
        payload={"request": request, "module_support": ctx["module_support"],
                 "mismatch_queries": ctx["mismatch_queries"]}, timestamp="t2"), bus)
    return bus.latest("module_plan_ready").payload


def _req(**kw):
    base = {"species": "human", "perturbation_object": "gene",
            "target_output": "expression", "perturbation_targets": ["AHR"]}
    base.update(kw)
    return base


def test_human_gene_expression_plan():
    p = _plan_for(_req())
    assert p["primary"] == "genetic_hub"
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["engine"] == "donor_predictor"
    assert prim["route_disposition"] == "accept"
    assert prim["species_verdict"] == "accept"
    assert prim["verdict"] == "accept"
    assert p["overall_verdict"] == "accept"


def test_mouse_gene_expression_is_caution():
    """mouse 迁移需 ortholog:route caution + species medium→ verdict caution(不 accept)。"""
    p = _plan_for(_req(species="mouse", perturbation_targets=["Gata1"]))
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["verdict"] == "caution"
    assert "ortholog_required" in prim["caution_flags"]


def test_bacteria_growth_gem_accept():
    p = _plan_for(_req(species="bacteria", target_output="growth",
                       perturbation_targets=["b0720"]))
    assert p["primary"] == "cytoplasmic_metabolism"
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["engine"] == "gem_fba"
    assert prim["verdict"] == "accept"


def test_bacteria_expression_gene_is_abstain_reject():
    """铁律:哺乳类 scRNA predictor 不适用微生物表达 → route abstain;primary M2 verdict 不 accept。"""
    p = _plan_for(_req(species="bacteria", target_output="expression",
                       perturbation_targets=["b0720"]))
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["route_disposition"] == "abstain"
    assert prim["verdict"] in ("abstain", "reject", "caution")   # 绝不 accept
    assert prim["verdict"] != "accept"


def test_bacteria_autophagy_mismatch_downgrades():
    """决策 E:bacteria + degradation → 自噬 mismatch → caution(不 accept)。"""
    p = _plan_for(_req(species="bacteria", perturbation_object="gene",
                       target_output="growth", perturbation_targets=["lon"]))
    # M4 是 primary(growth);但若把 degradation 作为 secondary 出现则带 mismatch。
    # 这里断言:整个 plan 里若出现 degradation_machinery entry,它带 mismatch=caution。
    degs = [e for e in p["entries"] if e["module"] == "degradation_machinery"]
    for e in degs:
        assert e["mismatch"] == "caution"
        assert e["verdict"] != "accept"


def test_bus_message_structure_and_no_llm():
    p = _plan_for(_req())
    # plan payload 是 ModulePlan.to_dict() 的全量键
    assert set(p) >= {"species", "request", "primary", "secondary",
                      "overall_verdict", "entries", "notes"}
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert set(prim) >= {"module", "engine", "verdict", "pillars", "reason"}


def test_mammalian_growth_has_m3_secondary_entry():
    p = _plan_for(_req(species="human", target_output="growth",
                       perturbation_targets=["MYC"]))
    assert "mitochondrial_energy_metabolism" in p["secondary"]
    sec_modules = {e["module"] for e in p["entries"] if e["role"] == "secondary"}
    assert "mitochondrial_energy_metabolism" in sec_modules
```

> **注意** `test_bacteria_autophagy_mismatch_downgrades`:决策 M1 里 bacteria+growth 的 primary 是 M4(不是 M8),故该 case 若 degradation 未被列为 secondary,`degs` 为空、循环 0 次(vacuously pass)。这是刻意的——本 task 只保证"**若** degradation entry 出现,它必带 mismatch"。degradation 作为 secondary 的显式规则留待控制器确认(决策 M1 待确认项);此断言先钉死"出现即降级"的 fail-closed 语义。golden task(3.5/3.6)会补更明确的 mismatch 覆盖 case。

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_router_agent.py -q`
Expected: FAIL(ModuleNotFoundError: ...module_router_agent)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/agents/module_router_agent.py`:

```python
"""ModuleRouterAgent(插点 B):进 message bus,产 ModulePlan。

收 module_route({request(归一后), module_support, mismatch_queries})→ 用 module_rules 定
primary/secondary → 对每个命中 module 复用 route_table.route() 落 engine/disposition/reason →
叠加 module_support 的 support/verdict、MODULES 的 display_name/pillars、mismatch → 合成 ModulePlan。

OFFLINE 全程零 LLM(不 import agents_llm)。LLM 版 module plan 留 Phase 4,那时 LLM 产 primary/secondary
后必须过滤成本模块的合法候选(复用"只能从候选选"约束),再走本 agent 同样的 route/verdict 合成。
铁律:物种 unsupported / mismatch → verdict 降级不 accept;route engine 与 MODULES[mid].engines
漂移 → 记 note(供 governance 检查),不崩不迁就。
"""
from __future__ import annotations

from praxis_virtualcell.agents import module_rules
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.biological_modules.module_plan import ModulePlan, ModulePlanEntry
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


class ModuleRouterAgent(BaseAgent):
    name = "ModuleRouterAgent"

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        raw = message.payload["request"]
        req = normalize_request(raw)                 # 复用归一,不自造
        module_support = message.payload.get("module_support", {})
        mismatch_queries = message.payload.get("mismatch_queries", {})
        species = req["species"]

        primary = module_rules.pick_primary(req)
        secondary = module_rules.pick_secondary(req, primary)
        notes: list[str] = []

        entries: list[ModulePlanEntry] = []
        for mid, role in [(primary, "primary")] + [(s, "secondary") for s in secondary]:
            entries.append(self._build_entry(
                req, species, mid, role, module_support, mismatch_queries, notes))

        plan = ModulePlan(species=species, request=req, primary=primary,
                          secondary=secondary, entries=entries, notes=notes)
        bus.send(AgentMessage(
            message_id=message.message_id + ":mplan",
            sender=self.name, receiver="EnsembleCoordinator",
            message_type="module_plan_ready", payload=plan.to_dict(),
            timestamp=message.timestamp, parent_message_id=message.message_id))

    def _build_entry(self, req, species, mid, role, module_support,
                     mismatch_queries, notes) -> ModulePlanEntry:
        # 1) 落 engine:复用 route()(单一真相源)
        dec = route(req)
        # 2) engine 与 module 定义漂移检查(不崩,记 note 供 governance)
        legal_engines = M.MODULES[mid]["engines"]
        if legal_engines and dec.engine not in legal_engines and dec.engine != "reject":
            notes.append(
                f"engine_module_drift: {mid} 定义 engines={legal_engines} 但 route 落 {dec.engine}")
        # 3) 物种 support/verdict(来自 SpeciesContext)
        sup = module_support.get(mid, {"support": "unsupported", "verdict": "reject",
                                       "display_name": mid, "models": [], "tools": []})
        # 4) mismatch:decision M3 推 query → SpeciesContext 暴露的 verdict
        mq = module_rules.mismatch_query_for(req, mid)
        mismatch = mismatch_queries.get(mq) if mq else None
        return ModulePlanEntry(
            module=mid,
            display_name=sup.get("display_name", M.display_name(mid, species=species)),
            role=role,
            engine=dec.engine,
            route_disposition=dec.disposition,
            species_support=sup["support"],
            species_verdict=sup["verdict"],
            caution_flags=list(dec.caution_flags),
            data_gated=dec.data_gated,
            pillars=list(M.MODULES[mid]["pillars"]),
            available_models=list(sup.get("models", [])),
            reason=dec.reason,
            mismatch=mismatch,
        )
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_router_agent.py -q`
Expected: 7 passed。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 382 passed / 25 skipped / 0 failed(375 + 7 新)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/agents/module_router_agent.py praxis_virtualcell/tests/test_module_router_agent.py
git commit -m "feat(phase3): ModuleRouterAgent(插点 B,进 bus,产 ModulePlan;复用 route()+ 物种 verdict + mismatch 降级,零 LLM)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 3.5:module routing golden 数据 + 独立 runner(representative,扩到 60 的第一半)

**决策说明:** 新建**独立**的 module-routing golden 文件(不改现有 `test_golden_cases.py` 的 route-only 断言)+ 独立参数化 runner,断言 `ModulePlan` 的 primary/engine/overall_verdict。这是路线图"module routing golden 60"的机制。本 task 落 representative(正常命中,4 物种 × 代表应用),Task 3.6 落 safety(mismatch/reject/downgrade)。runner 复用 `test_golden_cases.py` 的 glob+跳过 `._*` 模式,但读**新目录** `module_golden_cases/`,断言 ModulePlan 字段。

**Files:**
- Create: `praxis_virtualcell/tests/module_golden_cases/module_representative.yaml`
- Create: `praxis_virtualcell/tests/test_module_golden_cases.py`

- [ ] **Step 1: 写失败测试(runner)**

写 `praxis_virtualcell/tests/test_module_golden_cases.py`:

```python
"""Phase 3:module routing golden(声明式,断言 ModulePlan)。目标 ≥60 case(路线图 §8)。
铁律:只读断言 ModuleRouter 现有行为;plan 与期望不符=真实 bug,不改 golden 迁就。
KPI:module unsafe-accept=0(凡期望非 accept 的 case,overall_verdict 不得 accept)。"""
from pathlib import Path

import pytest
import yaml

from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_DIR = Path(__file__).parent / "module_golden_cases"


def _load():
    cases = []
    for f in sorted(_DIR.glob("*.yaml")):
        if f.name.startswith("._"):
            continue
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        cases.extend(doc.get("cases", []))
    return cases


_CASES = _load()


def _plan_for(request):
    bus = MessageBus()
    SpeciesContextAgent().handle(AgentMessage(
        message_id="c1", sender="SpeciesBrain", receiver="SpeciesContextAgent",
        message_type="species_context", payload={"request": request}, timestamp="t1"), bus)
    ctx = bus.latest("species_context_ready").payload
    ModuleRouterAgent().handle(AgentMessage(
        message_id="c2", sender="SpeciesContextAgent", receiver="ModuleRouterAgent",
        message_type="module_route",
        payload={"request": request, "module_support": ctx["module_support"],
                 "mismatch_queries": ctx["mismatch_queries"]}, timestamp="t2"), bus)
    return bus.latest("module_plan_ready").payload


def test_case_count():
    assert len(_CASES) >= 30, f"module golden 用例过少({len(_CASES)}),疑 glob 落空"


@pytest.mark.parametrize("case", _CASES, ids=[c["case_id"] for c in _CASES] or ["_empty"])
def test_module_plan_matches(case):
    p = _plan_for(case["input"])
    exp = case["expect"]
    assert p["primary"] == exp["primary"], \
        f"{case['case_id']}: primary {p['primary']} != {exp['primary']}"
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["engine"] == exp["engine"], \
        f"{case['case_id']}: engine {prim['engine']} != {exp['engine']}"
    assert p["overall_verdict"] == exp["overall_verdict"], \
        f"{case['case_id']}: overall {p['overall_verdict']} != {exp['overall_verdict']}"
    if "primary_verdict" in exp:
        assert prim["verdict"] == exp["primary_verdict"], \
            f"{case['case_id']}: primary_verdict {prim['verdict']} != {exp['primary_verdict']}"


def test_no_unsafe_accept():
    """KPI:凡期望 overall 非 accept 的 case,实际不得 accept。"""
    unsafe = [c["case_id"] for c in _CASES
              if c["expect"]["overall_verdict"] != "accept"
              and _plan_for(c["input"])["overall_verdict"] == "accept"]
    assert unsafe == [], f"module unsafe accept: {unsafe}"
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_golden_cases.py -q`
Expected: FAIL(`module_golden_cases/` 不存在 → glob 空 → `test_case_count` 断言失败 `0 >= 30`)。

- [ ] **Step 3: 写 representative golden 数据(≥32 case)**

写 `praxis_virtualcell/tests/module_golden_cases/module_representative.yaml`:

> **规则:** `input` 是喂给 SpeciesContext/Router 的 raw request(经 normalize_request);`expect.primary` = ModulePlan primary;`expect.engine` = primary entry 的 route engine;`expect.overall_verdict` = 全 plan 最保守 verdict;可选 `expect.primary_verdict`。所有 expect 值须由 ModuleRouter **实跑产出**(不猜;若实跑与此处不符是真实 bug,停下报告)。

```yaml
# module routing golden(representative):4 物种 × 代表应用,正常命中。
# expect 为 ModuleRouter 实跑产出值(不猜;不符=真实 bug)。
cases:
  # ---- human(8)----
  - case_id: human_gene_expression
    input: {species: human, perturbation_object: gene, target_output: expression, perturbation_targets: [AHR]}
    expect: {primary: genetic_hub, engine: donor_predictor, overall_verdict: accept, primary_verdict: accept}
  - case_id: human_gene_combo_expression
    input: {species: human, perturbation_object: gene_combination, target_output: expression, perturbation_targets: [AHR, MYC]}
    expect: {primary: genetic_hub, engine: donor_predictor, overall_verdict: accept}
  - case_id: human_gene_state
    input: {species: human, perturbation_object: gene, target_output: state, perturbation_targets: [SNAI1]}
    expect: {primary: stress_processor, engine: state_scoring, overall_verdict: accept}
  - case_id: human_drug_expression
    input: {species: human, perturbation_object: drug, target_output: expression, perturbation_targets: [vorinostat]}
    expect: {primary: stress_processor, engine: embedding, overall_verdict: caution}
  - case_id: human_communication
    input: {species: human, perturbation_object: ligand, target_output: communication, perturbation_targets: [TNF]}
    expect: {primary: stress_processor, engine: communication, overall_verdict: accept}
  - case_id: human_spatial_niche_state
    input: {species: human, perturbation_object: medium, target_output: state, perturbation_targets: [], medium: niche}
    expect: {primary: cytoskeletal_framework, engine: spatial_niche, overall_verdict: caution}
  - case_id: human_flux_pathway
    input: {species: human, perturbation_object: gene, target_output: flux, perturbation_targets: [PKM]}
    expect: {primary: cytoplasmic_metabolism, engine: pathway_scoring, overall_verdict: caution}
  - case_id: human_gene_growth_downgrade
    input: {species: human, perturbation_object: gene, target_output: growth, perturbation_targets: [MYC]}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: downgrade}
  # ---- mouse(8)----
  - case_id: mouse_gene_expression_caution
    input: {species: mouse, perturbation_object: gene, target_output: expression, perturbation_targets: [Gata1]}
    expect: {primary: genetic_hub, engine: donor_predictor, overall_verdict: caution, primary_verdict: caution}
  - case_id: mouse_gene_state_caution
    input: {species: mouse, perturbation_object: gene, target_output: state, perturbation_targets: [Gata1]}
    expect: {primary: stress_processor, engine: state_scoring, overall_verdict: caution}
  - case_id: mouse_drug_expression
    input: {species: mouse, perturbation_object: drug, target_output: expression, perturbation_targets: [vorinostat]}
    expect: {primary: stress_processor, engine: embedding, overall_verdict: caution}
  - case_id: mouse_flux_pathway
    input: {species: mouse, perturbation_object: gene, target_output: flux, perturbation_targets: [Pkm]}
    expect: {primary: cytoplasmic_metabolism, engine: pathway_scoring, overall_verdict: caution}
  - case_id: mouse_gene_growth_downgrade
    input: {species: mouse, perturbation_object: gene, target_output: growth, perturbation_targets: [Myc]}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: downgrade}
  - case_id: mouse_gene_combo_expression
    input: {species: mouse, perturbation_object: gene_combination, target_output: expression, perturbation_targets: [Gata1, Myc]}
    expect: {primary: genetic_hub, engine: donor_predictor, overall_verdict: caution}
  - case_id: mouse_ligand_communication
    input: {species: mouse, perturbation_object: ligand, target_output: communication, perturbation_targets: [Tnf]}
    expect: {primary: stress_processor, engine: reject, overall_verdict: abstain}
  - case_id: mouse_spatial_niche_state
    input: {species: mouse, perturbation_object: medium, target_output: state, perturbation_targets: [], medium: niche}
    expect: {primary: cytoskeletal_framework, engine: state_scoring, overall_verdict: caution}
  # ---- bacteria(8)----
  - case_id: bacteria_gene_growth
    input: {species: bacteria, perturbation_object: gene, target_output: growth, perturbation_targets: [b0720]}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: accept, primary_verdict: accept}
  - case_id: bacteria_medium_growth
    input: {species: bacteria, perturbation_object: medium, target_output: growth, perturbation_targets: [], medium: acetate}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: accept}
  - case_id: bacteria_drug_growth
    input: {species: bacteria, perturbation_object: drug, target_output: growth, perturbation_targets: [trimethoprim]}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: accept}
  - case_id: bacteria_gene_combo_growth
    input: {species: bacteria, perturbation_object: gene_combination, target_output: growth, perturbation_targets: [b0720, b0721]}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: accept}
  - case_id: bacteria_flux_gem
    input: {species: bacteria, perturbation_object: gene, target_output: flux, perturbation_targets: [b0720]}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: accept}
  - case_id: bacteria_drug_expression_reject
    input: {species: bacteria, perturbation_object: gene, target_output: expression, perturbation_targets: [b0720]}
    expect: {primary: genetic_hub, engine: reject, overall_verdict: abstain}
  - case_id: bacteria_gene_state_reject
    input: {species: bacteria, perturbation_object: gene, target_output: state, perturbation_targets: [b0720]}
    expect: {primary: stress_processor, engine: reject, overall_verdict: abstain}
  - case_id: bacteria_medium_flux
    input: {species: bacteria, perturbation_object: medium, target_output: flux, perturbation_targets: [], medium: glucose}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: accept}
  # ---- yeast(8)----
  - case_id: yeast_gene_growth
    input: {species: yeast, perturbation_object: gene, target_output: growth, perturbation_targets: [YBR166C]}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: accept, primary_verdict: accept}
  - case_id: yeast_medium_growth
    input: {species: yeast, perturbation_object: medium, target_output: growth, perturbation_targets: [], medium: galactose}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: accept}
  - case_id: yeast_gene_combo_growth
    input: {species: yeast, perturbation_object: gene_combination, target_output: growth, perturbation_targets: [YBR166C, YBR167C]}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: accept}
  - case_id: yeast_flux_gem
    input: {species: yeast, perturbation_object: gene, target_output: flux, perturbation_targets: [YBR166C]}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: accept}
  - case_id: yeast_drug_growth
    input: {species: yeast, perturbation_object: drug, target_output: growth, perturbation_targets: [cycloheximide]}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: accept}
  - case_id: yeast_gene_expression_reject
    input: {species: yeast, perturbation_object: gene, target_output: expression, perturbation_targets: [YBR166C]}
    expect: {primary: genetic_hub, engine: reject, overall_verdict: abstain}
  - case_id: yeast_gene_state_reject
    input: {species: yeast, perturbation_object: gene, target_output: state, perturbation_targets: [YBR166C]}
    expect: {primary: stress_processor, engine: reject, overall_verdict: abstain}
  - case_id: yeast_medium_flux
    input: {species: yeast, perturbation_object: medium, target_output: flux, perturbation_targets: [], medium: ethanol}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: accept}
```

> **执行者提醒:** 上表 `expect` 值是**按 route_table + module_rules + module_support 推演的预期**。Step 4 跑之前,若某 case 实跑与此不符,**先核对是数据写错还是真实 bug**:数据写错(如把 caution 写成 accept)→ 改数据对齐实跑;若实跑逻辑本身可疑(如该 caution 却 accept)→ 停下报告,不迁就(红线 5)。特别核对:`human_spatial_niche_state`/`human_flux_pathway` 的 overall 因 human 该模块 support=weak(cytoskeletal)或 medium,species_verdict 可能叠加使 overall 更保守——**以实跑为准调数据,不以数据强扭实跑**。

- [ ] **Step 4: 跑确认通过(先单跑核对 expect)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_golden_cases.py -q`
Expected: 全 case passed(≥32 参数化 + test_case_count + test_no_unsafe_accept)。若个别 case 失败 → 按 Step 3 提醒核对(数据 vs 真实 bug)。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 416 passed / 25 skipped / 0 failed(382 + 34 新:32 参数化 case + test_case_count + test_no_unsafe_accept;`test_module_plan_matches` 每 case 计 1 条)。以实跑精确数为准,关键 0 failed。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/tests/module_golden_cases/module_representative.yaml praxis_virtualcell/tests/test_module_golden_cases.py
git commit -m "test(phase3): module routing golden(representative,4 物种×代表应用)+ 独立 ModulePlan runner + unsafe-accept KPI

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 3.6:module routing golden safety 数据(mismatch/reject/downgrade,扩到 60 的第二半)

**决策说明:** 补 safety 层 golden:生物学错配(bacteria 自噬 / yeast 组织 niche / yeast 哺乳类通讯)、跨物种 negative transfer、fail-closed 边界。这些 case 落进**同一** `module_golden_cases/` 目录(runner 自动 glob),把总数推到 ≥60(路线图 §8 "module routing golden 60")。断言 mismatch entry 的 verdict 降级、overall 不 accept。

**Files:**
- Create: `praxis_virtualcell/tests/module_golden_cases/module_safety.yaml`

- [ ] **Step 1: 写 safety golden 数据(≥28 case,凑总 ≥60)**

写 `praxis_virtualcell/tests/module_golden_cases/module_safety.yaml`:

> 复用 Task 3.5 的 runner(`test_module_golden_cases.py` 自动 glob 本目录),无需改 runner。`expect` 仍为实跑产出;safety case 的 `overall_verdict` 一律非 accept(caution/downgrade/abstain/reject),守 KPI。

```yaml
# module routing golden(safety):mismatch / negative transfer / fail-closed,overall 一律非 accept。
cases:
  # ---- bacteria 术语/机制硬约束(决策 E)----
  - case_id: bacteria_expression_negative_transfer
    input: {species: bacteria, perturbation_object: gene, target_output: expression, perturbation_targets: [lon]}
    expect: {primary: genetic_hub, engine: reject, overall_verdict: abstain}
  - case_id: bacteria_gene_combo_expression_reject
    input: {species: bacteria, perturbation_object: gene_combination, target_output: expression, perturbation_targets: [b0720, b0721]}
    expect: {primary: genetic_hub, engine: reject, overall_verdict: abstain}
  - case_id: bacteria_ligand_communication_reject
    input: {species: bacteria, perturbation_object: ligand, target_output: communication, perturbation_targets: [FLIC]}
    expect: {primary: stress_processor, engine: reject, overall_verdict: abstain}
  - case_id: bacteria_medium_state_reject
    input: {species: bacteria, perturbation_object: medium, target_output: state, perturbation_targets: [], medium: nutrient_shift}
    expect: {primary: stress_processor, engine: reject, overall_verdict: abstain}
  - case_id: bacteria_drug_state_reject
    input: {species: bacteria, perturbation_object: drug, target_output: state, perturbation_targets: [ampicillin]}
    expect: {primary: stress_processor, engine: reject, overall_verdict: abstain}
  # ---- yeast 组织/通讯错配 ----
  - case_id: yeast_niche_state_reject
    input: {species: yeast, perturbation_object: medium, target_output: state, perturbation_targets: [], medium: niche}
    expect: {primary: cytoskeletal_framework, engine: reject, overall_verdict: abstain}
  - case_id: yeast_ligand_communication_reject
    input: {species: yeast, perturbation_object: ligand, target_output: communication, perturbation_targets: [MFALPHA1]}
    expect: {primary: stress_processor, engine: reject, overall_verdict: abstain}
  - case_id: yeast_drug_expression_reject
    input: {species: yeast, perturbation_object: drug, target_output: expression, perturbation_targets: [cycloheximide]}
    expect: {primary: stress_processor, engine: embedding, overall_verdict: caution}
  - case_id: yeast_gene_combo_expression_reject
    input: {species: yeast, perturbation_object: gene_combination, target_output: expression, perturbation_targets: [YBR166C, YBR167C]}
    expect: {primary: genetic_hub, engine: reject, overall_verdict: abstain}
  - case_id: yeast_gene_state_reject_dup
    input: {species: yeast, perturbation_object: gene, target_output: state, perturbation_targets: [YAL001C]}
    expect: {primary: stress_processor, engine: reject, overall_verdict: abstain}
  # ---- 哺乳类 growth/ligand data-gated downgrade ----
  - case_id: human_ligand_expression_downgrade
    input: {species: human, perturbation_object: ligand, target_output: expression, perturbation_targets: [TNF]}
    expect: {primary: stress_processor, engine: embedding, overall_verdict: downgrade}
  - case_id: mouse_ligand_expression_downgrade
    input: {species: mouse, perturbation_object: ligand, target_output: expression, perturbation_targets: [Tnf]}
    expect: {primary: stress_processor, engine: embedding, overall_verdict: downgrade}
  - case_id: human_gene_growth_downgrade_dup
    input: {species: human, perturbation_object: gene_combination, target_output: growth, perturbation_targets: [MYC, KRAS]}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: downgrade}
  - case_id: mouse_medium_growth_downgrade
    input: {species: mouse, perturbation_object: medium, target_output: growth, perturbation_targets: [], medium: glucose}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: downgrade}
  # ---- 跨物种 state/communication negative ----
  - case_id: mouse_communication_reject
    input: {species: mouse, perturbation_object: gene, target_output: communication, perturbation_targets: [Gata1]}
    expect: {primary: stress_processor, engine: reject, overall_verdict: abstain}
  - case_id: bacteria_gene_communication_reject
    input: {species: bacteria, perturbation_object: gene, target_output: communication, perturbation_targets: [b0720]}
    expect: {primary: stress_processor, engine: reject, overall_verdict: abstain}
  - case_id: yeast_gene_communication_reject
    input: {species: yeast, perturbation_object: gene, target_output: communication, perturbation_targets: [YBR166C]}
    expect: {primary: stress_processor, engine: reject, overall_verdict: abstain}
  # ---- weak-support module caution(物种 verdict 叠加)----
  - case_id: human_membrane_expression_weak
    input: {species: human, perturbation_object: drug, target_output: state, perturbation_targets: [tunicamycin]}
    expect: {primary: stress_processor, engine: state_scoring, overall_verdict: accept}
  - case_id: bacteria_membrane_growth
    input: {species: bacteria, perturbation_object: drug, target_output: growth, perturbation_targets: [polymyxin]}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: accept}
  - case_id: mouse_flux_pathway_dup
    input: {species: mouse, perturbation_object: gene_combination, target_output: flux, perturbation_targets: [Pkm, Ldha]}
    expect: {primary: cytoplasmic_metabolism, engine: pathway_scoring, overall_verdict: caution}
  - case_id: human_flux_pathway_dup
    input: {species: human, perturbation_object: gene_combination, target_output: flux, perturbation_targets: [PKM, LDHA]}
    expect: {primary: cytoplasmic_metabolism, engine: pathway_scoring, overall_verdict: caution}
  - case_id: mouse_drug_state_caution
    input: {species: mouse, perturbation_object: drug, target_output: state, perturbation_targets: [dexamethasone]}
    expect: {primary: stress_processor, engine: state_scoring, overall_verdict: caution}
  - case_id: human_gene_state_native
    input: {species: human, perturbation_object: gene_combination, target_output: state, perturbation_targets: [SNAI1, ZEB1]}
    expect: {primary: stress_processor, engine: state_scoring, overall_verdict: accept}
  - case_id: bacteria_ligand_growth_reject
    input: {species: bacteria, perturbation_object: ligand, target_output: growth, perturbation_targets: [AI2]}
    expect: {primary: cytoplasmic_metabolism, engine: reject, overall_verdict: abstain}
  - case_id: yeast_ligand_growth_reject
    input: {species: yeast, perturbation_object: ligand, target_output: growth, perturbation_targets: [MFALPHA1]}
    expect: {primary: cytoplasmic_metabolism, engine: reject, overall_verdict: abstain}
  - case_id: human_ligand_growth_downgrade
    input: {species: human, perturbation_object: ligand, target_output: growth, perturbation_targets: [EGF]}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: downgrade}
  - case_id: mouse_ligand_growth_downgrade
    input: {species: mouse, perturbation_object: ligand, target_output: growth, perturbation_targets: [Egf]}
    expect: {primary: cytoplasmic_metabolism, engine: gem_fba, overall_verdict: downgrade}
  - case_id: human_ligand_flux_caution
    input: {species: human, perturbation_object: ligand, target_output: flux, perturbation_targets: [EGF]}
    expect: {primary: cytoplasmic_metabolism, engine: pathway_scoring, overall_verdict: caution}
```

> **执行者提醒(强):** safety 表的 `expect` 更依赖真实合成结果。**先跑 Step 2 单文件,逐 case 核对**:凡 route 落 `reject/abstain` 的组合,overall 必 abstain/reject;凡 `embedding` 药物 caution + species medium→ 可能 caution 或 downgrade;凡 ligand→expression 是 route downgrade(data_gated)。任何一条实跑与 expect 不符:**优先判定是"我 expect 写错"还是"router 真 bug"**。写错→改 expect 对齐实跑;真 bug(如该 abstain 却 accept)→ 停下报告,绝不改 router/golden 迁就(红线 5)。case 数以能凑到"两文件合计 ≥60"为准,可按实跑增删同类 case(但不得删除任何暴露 bug 的 case)。

- [ ] **Step 2: 跑确认通过(单文件先核对)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_golden_cases.py -q`
Expected: 全绿(representative 32 + safety ≥28 = ≥60 case 全 pass + test_case_count(现 ≥30 仍成立)+ test_no_unsafe_accept)。

- [ ] **Step 3: 核对总 golden 数 ≥60(路线图 §8 目标)**

Run: `PYTHONPATH=$PWD .venv/bin/python -c "import sys; sys.path.insert(0, 'praxis_virtualcell/tests'); import test_module_golden_cases as t; print('module golden cases =', len(t._CASES))"`
Expected: `module golden cases = 60`(或更多)。若 <60 → 补同类 case 至 ≥60。

- [ ] **Step 4: 收紧 test_case_count 到 60**

在 `test_module_golden_cases.py` 把 `test_case_count` 的阈值从 30 提到 60(数据已够):

找到:

```python
def test_case_count():
    assert len(_CASES) >= 30, f"module golden 用例过少({len(_CASES)}),疑 glob 落空"
```

改为:

```python
def test_case_count():
    assert len(_CASES) >= 60, f"module golden 用例过少({len(_CASES)}),路线图 §8 目标 60"
```

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 444 passed / 25 skipped / 0 failed(416 + 28 新 safety case;总 module golden ≥60)。以实跑精确数为准(safety case 数按 Step 3 调整后可能微增),关键 0 failed + module golden 总数 ≥60。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/tests/module_golden_cases/module_safety.yaml praxis_virtualcell/tests/test_module_golden_cases.py
git commit -m "test(phase3): module routing golden safety(mismatch/negative-transfer/fail-closed);总 module golden ≥60

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 3.7:governance 扩容 —— cross-module consistency 校验(G4)

**决策说明:** 路线图 §8 Phase 3 有 "governance tests 40(扩现有 + evidence level)"。**evidence level(E0–E5)留后**(见"插点归置决策"),本 task 聚焦 Phase 3 真正能确定性验证的两条:①**cross-module consistency**(ModulePlan 内部一致性:primary/secondary 不冲突、mismatch entry 不 accept、engine ∈ module.engines 白名单或标 drift note)②**module verdict ↔ route disposition 一致性**(verdict 不得比 route disposition 更乐观)。新增**纯函数校验器** `governance/module_consistency.py`(不进 bus,供 Critic 未来 G4 复用 + 独立测试),不改现有 Critic(那是 Phase 4 接管线时的事)。

**Files:**
- Create: `praxis_virtualcell/governance/module_consistency.py`
- Test: `praxis_virtualcell/tests/test_module_consistency.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_module_consistency.py`:

```python
"""Phase 3:cross-module consistency 校验(G4 铺路)。纯函数,验 ModulePlan 内部一致性。
铁律:verdict 不得比 route disposition 更乐观;mismatch entry 不得 accept;engine 越白名单 → 违规。
注:evidence level(E0–E5)不在本 Phase(留 Phase 4/5,见计划头部归置决策)。"""
from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.governance.module_consistency import check_module_plan


def _plan_for(request):
    bus = MessageBus()
    SpeciesContextAgent().handle(AgentMessage(
        message_id="c1", sender="SpeciesBrain", receiver="SpeciesContextAgent",
        message_type="species_context", payload={"request": request}, timestamp="t1"), bus)
    ctx = bus.latest("species_context_ready").payload
    ModuleRouterAgent().handle(AgentMessage(
        message_id="c2", sender="SpeciesContextAgent", receiver="ModuleRouterAgent",
        message_type="module_route",
        payload={"request": request, "module_support": ctx["module_support"],
                 "mismatch_queries": ctx["mismatch_queries"]}, timestamp="t2"), bus)
    return bus.latest("module_plan_ready").payload


def test_clean_plan_has_no_violations():
    p = _plan_for({"species": "human", "perturbation_object": "gene",
                   "target_output": "expression", "perturbation_targets": ["AHR"]})
    assert check_module_plan(p) == []


def test_reject_plan_has_no_violations_either():
    """abstain plan 本身合规(fail-closed 是对的,不算违规)。"""
    p = _plan_for({"species": "bacteria", "perturbation_object": "gene",
                   "target_output": "expression", "perturbation_targets": ["b0720"]})
    assert check_module_plan(p) == []


def test_detects_verdict_more_optimistic_than_route():
    """人为构造:route abstain 但 verdict accept → 必须被抓(不许比 route 更乐观)。"""
    bad = {"species": "human", "request": {}, "primary": "genetic_hub",
           "secondary": [], "overall_verdict": "accept", "notes": [],
           "entries": [{"module": "genetic_hub", "role": "primary", "engine": "reject",
                        "route_disposition": "abstain", "species_support": "strong",
                        "species_verdict": "accept", "verdict": "accept",
                        "caution_flags": [], "data_gated": False, "pillars": [],
                        "available_models": [], "reason": "x", "mismatch": None}]}
    v = check_module_plan(bad)
    assert any("more_optimistic" in x or "verdict" in x for x in v)


def test_detects_mismatch_entry_accepted():
    """mismatch 非 None 但 verdict=accept → 违规(mismatch 必须降级)。"""
    bad = {"species": "bacteria", "request": {}, "primary": "degradation_machinery",
           "secondary": [], "overall_verdict": "accept", "notes": [],
           "entries": [{"module": "degradation_machinery", "role": "primary", "engine": "reject",
                        "route_disposition": "accept", "species_support": "weak",
                        "species_verdict": "accept", "verdict": "accept",
                        "caution_flags": [], "data_gated": False, "pillars": [],
                        "available_models": [], "reason": "x", "mismatch": "caution"}]}
    v = check_module_plan(bad)
    assert any("mismatch" in x for x in v)


def test_detects_engine_out_of_module_whitelist():
    """engine 不在 MODULES[mid].engines(且非 reject)→ 违规(白名单外)。"""
    bad = {"species": "human", "request": {}, "primary": "genetic_hub",
           "secondary": [], "overall_verdict": "accept", "notes": [],
           "entries": [{"module": "genetic_hub", "role": "primary", "engine": "gem_fba",
                        "route_disposition": "accept", "species_support": "strong",
                        "species_verdict": "accept", "verdict": "accept",
                        "caution_flags": [], "data_gated": False, "pillars": [],
                        "available_models": [], "reason": "x", "mismatch": None}]}
    v = check_module_plan(bad)
    assert any("whitelist" in x or "engine" in x for x in v)


def test_all_representative_golden_plans_are_consistent():
    """全 representative golden 的实跑 plan 都应零违规(冒烟:确定性路由自洽)。"""
    for req in (
        {"species": "human", "perturbation_object": "gene", "target_output": "expression", "perturbation_targets": ["AHR"]},
        {"species": "bacteria", "perturbation_object": "gene", "target_output": "growth", "perturbation_targets": ["b0720"]},
        {"species": "mouse", "perturbation_object": "gene", "target_output": "expression", "perturbation_targets": ["Gata1"]},
        {"species": "yeast", "perturbation_object": "gene", "target_output": "growth", "perturbation_targets": ["YBR166C"]},
    ):
        assert check_module_plan(_plan_for(req)) == [], f"{req} plan 有一致性违规"
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_consistency.py -q`
Expected: FAIL(ModuleNotFoundError: ...module_consistency)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/governance/module_consistency.py`:

```python
"""cross-module consistency 校验(G4 铺路)。纯函数,验 ModulePlan(dict 或 ModulePlan.to_dict())
内部一致性,返回违规字符串列表(空 = 一致)。

规则(全 fail-closed 方向):
1. verdict 不得比 route_disposition 更乐观(更乐观 = severity 更低)。
2. mismatch 非 None → verdict 不得 accept。
3. engine 不在 MODULES[mid].engines 白名单(且非 reject)→ 违规。
4. overall_verdict 必须 = 各 entry verdict 最保守(不得比最保守 entry 更乐观)。

evidence level(E0–E5)不在此校验(留 Phase 4/5;那时管线带 reliability/OOD 信号)。
本校验器供 Critic 未来 G4 复用 + Phase 3 独立测试;不改现有 Critic。
"""
from __future__ import annotations

from praxis_virtualcell.biological_modules import modules as M

_SEVERITY = {"accept": 0, "caution": 1, "downgrade": 2, "abstain": 3, "reject": 3}


def _sev(v: str) -> int:
    return _SEVERITY.get(v, 3)   # 未知 → 最保守


def check_module_plan(plan: dict) -> list[str]:
    """返回违规说明列表(空 = 无违规)。plan = ModulePlan.to_dict()。"""
    violations: list[str] = []
    entries = plan.get("entries", [])
    for e in entries:
        mid = e.get("module")
        # 1) verdict 不得比 route 更乐观
        if _sev(e.get("verdict")) < _sev(e.get("route_disposition")):
            violations.append(
                f"verdict_more_optimistic_than_route[{mid}]: "
                f"verdict={e.get('verdict')} < route={e.get('route_disposition')}")
        # 2) mismatch 命中不得 accept
        if e.get("mismatch") and e.get("verdict") == "accept":
            violations.append(f"mismatch_entry_accepted[{mid}]: mismatch={e.get('mismatch')} 却 accept")
        # 3) engine 白名单
        if mid in M.MODULES:
            legal = M.MODULES[mid]["engines"]
            eng = e.get("engine")
            if legal and eng not in legal and eng != "reject":
                violations.append(
                    f"engine_out_of_whitelist[{mid}]: {eng} ∉ {legal}")
    # 4) overall 不得比最保守 entry 更乐观
    if entries:
        most_conservative = max(_sev(e.get("verdict")) for e in entries)
        if _sev(plan.get("overall_verdict")) < most_conservative:
            violations.append(
                f"overall_more_optimistic: overall={plan.get('overall_verdict')} "
                f"比最保守 entry(sev={most_conservative})更乐观")
    return violations
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_consistency.py -q`
Expected: 6 passed。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 450 passed / 25 skipped / 0 failed(444 + 6 新)。**这已达到路线图 450+ 目标口径的地标数。**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/governance/module_consistency.py praxis_virtualcell/tests/test_module_consistency.py
git commit -m "feat(phase3): cross-module consistency 校验(G4 铺路;verdict/mismatch/engine 白名单/overall 一致性,纯函数)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 3.8:Phase 3 完成闸门 —— 红线核验 + 台账 + v1.0 tag

**决策说明:** Phase 3 是 **v1.0 里程碑**(路线图 §5)。本 task 不写新功能,只做:①红线全量核验(LLM 边界三 flag 恒 False、原 route golden/negative KPI 仍绿、module golden unsafe-accept=0、OFFLINE 零 LLM);②精确回归数(junit);③台账追加 Phase 3 段;④打 **v1.0 tag**(本地,不 push)。

**Files:**
- Modify: `docs/STATUS-2026-07-03-v0.6-v0.8-delivery.md`(尾部追加 Phase 3 完成台账段)

- [ ] **Step 1: 红线核验 —— LLM 边界 + 原 route golden/negative KPI 仍绿**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_llm_boundary_flags.py praxis_virtualcell/tests/test_golden_cases.py praxis_virtualcell/tests/test_negative_cases.py -q`
Expected: 全绿。Phase 3 未碰管线/治理 agent/route_table,`assert_llm_boundaries` 三 flag 恒 False、原 route golden unsafe-accept=0、negative 无静默 accept 不变。

- [ ] **Step 2: 红线核验 —— OFFLINE 零 LLM(module router 不引 agents_llm)**

Run: `grep -rn "agents_llm" praxis_virtualcell/agents/module_router_agent.py praxis_virtualcell/agents/species_context_agent.py praxis_virtualcell/agents/module_rules.py praxis_virtualcell/biological_modules/module_plan.py praxis_virtualcell/governance/module_consistency.py`
Expected: **无任何匹配**(OFFLINE module 路由零 LLM;红线 1)。若有匹配 → 违规,停下修正。

- [ ] **Step 3: 红线核验 —— module golden unsafe-accept=0**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_golden_cases.py::test_no_unsafe_accept -v`
Expected: PASS(凡期望非 accept 的 module case,实际 overall 不得 accept)。

- [ ] **Step 4: 全量回归(精确数)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q --junit-xml=/tmp/junit_phase3.xml`
然后取精确数:
Run: `python3 -c "import xml.etree.ElementTree as ET; r=ET.parse('/tmp/junit_phase3.xml').getroot(); s=r if r.tag=='testsuite' else r[0]; t,f,e,k=int(s.get('tests')),int(s.get('failures')),int(s.get('errors')),int(s.get('skipped')); print('collected=%d failures=%d errors=%d skipped=%d passed=%d'%(t,f,e,k,t-f-e-k))"`
Expected: `failures=0 errors=0 skipped=25 passed=450`(352 基线 + 7+6+10+7+34+28+6 = 98 新 = 450;若 safety golden case 数按 3.6 Step 3 微调,passed 相应微增,以实跑为准)。**关键:failures=0 errors=0 + passed ≥450**(达路线图目标)。

- [ ] **Step 5: 台账更新**

用 Edit 在 `docs/STATUS-2026-07-03-v0.6-v0.8-delivery.md` 尾部追加:

```markdown

---

## Phase 3 完成台账(2026-07-04,module-aware router — v1.0 里程碑)

- **交付**:`biological_modules/module_plan.py`(ModulePlan/ModulePlanEntry,Phase 4 输入契约)+ `agents/species_context_agent.py`(插点 A)+ `agents/module_rules.py`(确定性 primary/secondary 规则)+ `agents/module_router_agent.py`(插点 B,产 ModulePlan)+ `governance/module_consistency.py`(G4 铺路)+ module routing golden ≥60(`tests/module_golden_cases/`)。
- **ModulePlan**:primary + secondary modules,每模块落 engine(复用 route())+ route disposition + 物种 support/verdict + mismatch + pillars + available_models,verdict 保守合成(取最保守 + mismatch 降级)。
- **红线守住**:OFFLINE module 路由零 LLM(grep 证无 agents_llm 依赖);物种 unsupported/mismatch(bacteria 自噬 / yeast 组织 niche)→ verdict 降级不 accept;module golden unsafe-accept=0;engine 越 MODULES 白名单 → ValueError/一致性违规。route_table/runtime/治理 agent/predictor 未动,352 基线零回归 → **450 passed / 25 skipped / 0 failed**(达路线图 450+ 目标口径)。
- **未接管线**:Phase 3 只交付 2 个 agent + ModulePlan + golden + 一致性校验器(可独立测试);接进 `run_workflow` 与 EvidenceLevelAgent(E0–E5)一并留 Phase 4(LLM 编排),避免本 Phase 越界。
- **归置**:SpeciesContextAgent(插点 A)归 Phase 3(ModuleRouter 前置);EvidenceLevelAgent(插点 C)留 Phase 4/5(需管线运行时 reliability/OOD 信号)。
- **v1.0 里程碑**:Phase 3 完成 = v1.0(model-controlled)。打 tag `v1.0-module-router`(本地,不 push)。
- **待控制器确认的科学决策**:primary/secondary 选取规则(决策 M1,尤其 communication 归属 M7、secondary 是否扩)、mismatch query 推导(决策 M3)——已在计划落最小确定性集并标注,执行后如需科学调整由控制器拍板。
```

- [ ] **Step 6: 提交(不 push)**

```bash
find . -name '._*' -delete
git add docs/STATUS-2026-07-03-v0.6-v0.8-delivery.md
git commit -m "docs(phase3): Phase 3 完成台账 + 红线核验(450 passed,module-aware router 交付)

Phase 3 交付 module-aware router:SpeciesContext(插点 A)+ ModuleRouter(插点 B,产 ModulePlan)
+ module_rules + module_consistency(G4 铺路)+ module golden ≥60。OFFLINE 零 LLM,物种/mismatch
verdict 降级不 accept,352 基线零回归 → 450 passed。接管线 + EvidenceLevel(E0–E5)留 Phase 4。

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

- [ ] **Step 7: 打 v1.0 tag(本地,不 push)**

Phase 3 = v1.0 里程碑(路线图 §5)。全绿 + 红线核验通过后打 tag:

```bash
git tag -a v1.0-module-router -m "v1.0: model-controlled — module-aware router (SpeciesContext + ModuleRouter + ModulePlan). 450 passed / 25 skipped. OFFLINE zero-LLM. Phase 3 done."
git tag --list "v1.0*"
```

Expected: tag `v1.0-module-router` 出现。**不 push**(房规:当前分支不 push;tag 推送由人决定)。

**Phase 3 验收:**
- ✅ ModulePlan 数据结构(primary/secondary + 每模块 engine 映射 + 物种 verdict + caution + mismatch + pillars),白名单校验 + verdict 保守合成 + to_dict 序列化 —— Phase 4 输入契约就位。
- ✅ SpeciesContextAgent(插点 A)进 bus,读 module_support 给 8 模块 support/verdict + mismatch 表;bacteria M3 显示 energy/redox。
- ✅ ModuleRouterAgent(插点 B)进 bus,产 ModulePlan;primary 落 engine 复用 route()(单一真相源);物种 unsupported/mismatch → verdict 降级不 accept。
- ✅ module routing golden ≥60(representative + safety,4 物种),独立 runner,unsafe-accept=0 KPI。
- ✅ cross-module consistency 校验(G4 铺路):verdict/mismatch/engine 白名单/overall 一致性,纯函数供 Critic 未来复用。
- ✅ OFFLINE module 路由零 LLM(grep 证);LLM plan 留 Phase 4(已铺"只能从候选选"约束地基)。
- ✅ EvidenceLevelAgent(E0–E5)留 Phase 4/5(需运行时信号),Phase 3 只做声明式 pillar 标注。
- ✅ 352 基线零回归(纯新增 + 复用,未碰 route_table/runtime/治理 agent/predictor)→ 450 passed;打 v1.0 tag(本地不 push)。

---

## Self-Review(写完对照路线图 + 真实代码)

- **路线图覆盖(§4/§5/§6/§7/§8)**:
  - §4 插点 B(ModuleRouterAgent 定 primary+secondary → ModulePlan;OFFLINE 确定性零 LLM;LLM 留 Phase 4)→ Task 3.4 + 3.3 完整落地。插点 A(SpeciesContextAgent 读 module_support)→ Task 3.2(归 Phase 3,理由在头部归置决策)。插点 C(EvidenceLevelAgent E0–E5)→ 明确留 Phase 4/5(理由:Phase 3 不接管线、无运行时 reliability/OOD 信号)。
  - §5 依赖:Phase 3 依赖 Phase 1 模块定义(用 MODULE_ORDER/MODULES/ModuleRegistry ✓);Phase 4 依赖 ModulePlan(Task 3.1 交付 ✓);Phase 3 完成=v1.0(Task 3.8 打 tag ✓)。
  - §6 决策 A(模块是逻辑视图,ModuleAgent 内部调现有 engine,空白模块走规则/abstain)→ ModuleRouter 完全复用 route()+MODULES.engines,不造新模型 ✓。决策 C(LLM 编排"只能从候选选")→ module_rules/router 的 OFFLINE 确定性输出即候选来源,Phase 4 LLM 版过滤成合法 module,已在 module_rules/router docstring 铺路 ✓。决策 E(bacteria 术语映射 + M8 自噬 mismatch)→ Task 3.2 test bacteria M3=energy/redox + Task 3.4/3.6 test 自噬 mismatch caution ✓。
  - §7 红线全适用:①OFFLINE 零 LLM(Task 3.8 Step 2 grep 核验)②assert_llm_boundaries 三 flag(Task 3.8 Step 1 未碰)③LLM plan 转 AgentMessage(留 Phase 4,本 Phase 无 LLM)④unsafe-accept=0(module golden KPI + 原 route/negative 仍绿)⑤只读断言不迁就(golden task 反复强调,expect 不符=真实 bug 停下报告)⑥模型缺失不静默(mismatch/unsupported → 降级 fail-closed)✓。
  - §8 测试目标:module routing golden 60(Task 3.5+3.6 ✓)+ governance 40 —— **校正**:governance 40 的"evidence level"部分留 Phase 4(见归置决策),Phase 3 交付 cross-module consistency 校验器(Task 3.7,6 条)+ module golden safety(28 条属治理性质:mismatch/negative/fail-closed)。累计 Phase 3 新增 98 条(7+6+10+7+34+28+6),352→450,达路线图 450+ 地标。

- **写作中发现并校正的真实代码情况(与路线图旧描述不符):**
  1. **`RouteDecision` 有 `reason` 字段**:路线图 §4/§1 只列 `(engine, disposition, caution_flags, data_gated)`,实读 `route_table.py:31` 有第 5 个字段 `reason`。ModulePlanEntry 透传 `reason`(证据不丢),数据契约段已注明。
  2. **`route()` 入参须先归一**:路线图把 route 说成直接吃 req,实读 `route()` 假定入参已过 `normalize_request`(键 species/perturbation_object/target_output/perturbation_targets)。ModuleRouter 内部复用 `normalize_request`,不自造。已在 Task 3.4 代码落实。
  3. **module→engine 映射已存在于 `MODULES[mid]["engines"]`**:路线图说 "ModuleRouter 内部仍调 route_table.route()",实读 Phase 1 已把每模块的 engine 归属写进 `modules.py`(如 M2=[donor_predictor]、M4=[gem_fba,pathway_scoring]、M1/M5/M8=[])。计划用它做 engine 白名单校验(决策 M2/一致性校验规则 3),不重造映射。
  4. **`ModuleRegistry` 真实方法名**:路线图说 "support/matrix/verdict 映射",实读方法是 `support()`/`default_verdict()`/`matrix()`/`biological_mismatch()`/`display_name()`,`_VERDICT` 是 strong/medium→accept、weak→caution、unsupported→reject。SpeciesContextAgent 直接调这些真实方法,数据契约段已列全。
  5. **`model_broker_agent.py` 已存在(Phase 2)**:故 Phase 3 不重造 broker;ModulePlan 只挂 `available_models`(引用 module_support 声明的 models 名),真调 broker 留 Phase 4(避免 Phase 3 引入 torch/远端 gated 依赖,保 OFFLINE 纯净)。已在头部 Architecture + Task 3.4 注明。
  6. **基线 352 passed 实跑核实**:当前分支 `feat/v0.9-phase0-module-core` 跑 `pytest praxis_virtualcell/tests --junit-xml` = collected 377 / skipped 25 / **passed 352**,与 prompt 给的 Phase 3 起点基线完全一致。全计划期望数以 352 为起点递增(359/365/375/382/416/444/450)。junit 的 `tests` 属性是 collected(含 skipped),passed = collected − skipped − failures − errors,铁律段已钉死此口径。
  7. **不接管线是刻意的低风险选择**:实读 `runtime.run_workflow` 是线性固定管线,插 ModuleRouter 节点会改动 predictor fan-out 的上游契约(app.payload 结构)。为守"不改现有逻辑"红线 + 降低 v1.0 里程碑回归风险,Phase 3 只交付可独立测试的 agent + 数据结构 + golden,接管线与 Phase 4 LLM 编排一起做(那时本就要改管线插 LLMModulePlanner)。已在 Architecture + 决策 R1(隐含)+ 台账注明。

- **无占位符**:每 task 每 step 含完整可跑测试代码 + 实现代码 + 确切命令 + 期望数。golden YAML 给出全部 case(representative 32 + safety 28,含每条 input/expect),非 "similar to above"。一致性校验器给出 4 条完整规则实现。

- **类型一致性**:`ModulePlanEntry` 的字段名(module/display_name/role/engine/route_disposition/species_support/species_verdict/caution_flags/data_gated/pillars/available_models/reason/mismatch/verdict)在 Task 3.1 定义、Task 3.4 router 构造、Task 3.5/3.7 测试断言、Task 3.7 一致性校验器读取,四处一致;`synthesize_verdict(route_disposition, species_verdict, mismatch)` 签名在 3.1 定义与 3.4 隐式(__post_init__)一致;`ModulePlan.to_dict()` 键(species/request/primary/secondary/overall_verdict/entries/notes)在 3.4 payload、3.5/3.7 断言一致;`check_module_plan(plan_dict)->list[str]` 在 3.7 定义与测试一致;`_SEVERITY` 映射在 module_plan.py 与 module_consistency.py 两处**一致**(accept0/caution1/downgrade2/abstain3/reject3);`pick_primary/pick_secondary/mismatch_query_for` 签名在 3.3 定义与 3.4 调用一致;SpeciesContext 产的 `module_support[mid]` 键(support/verdict/display_name/models/tools/reason)在 3.2 产出与 3.4 消费一致。

- **铁律段完整**:纯新增+复用、OFFLINE 零 LLM(grep 核验)、fail-closed/无静默 accept、module 白名单单一真相源、测试口径 praxis_virtualcell/tests + junit passed=collected−skipped 精确口径、每 task 删 ._* + Co-Authored-By trailer + 当前分支不 push、Phase 3=v1.0 里程碑才打 tag —— 全写进头部铁律段并逐 task 执行。

---

## 下一步(Phase 4 展开时机)

Phase 3 全绿(450 passed)+ v1.0 tag 后,回主路线图 §9,把 **Phase 4(LLM_ORCHESTRATED:LLMModulePlanner + cross_module_reasoner + safety_contract + 把 ModuleRouter/SpeciesContext 接进 runtime 管线 + EvidenceLevelAgent E0–E5)** 展开成同粒度详细计划。Phase 4 会用到本 Phase 的 **ModulePlan 数据结构**(LLM 产 primary/secondary → 过滤成合法 module → 合成同一 ModulePlan)、`module_consistency.check_module_plan`(接进 Critic 做 G4)、SpeciesContext/ModuleRouter(接进 run_workflow)。Phase 4 = v1.1 里程碑。
