# P10.B4 M1/M5/M8 rule-based advisory 实现 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: 用 superpowers:subagent-driven-development 逐 task 执行本 plan(每 task fresh implementer + 两审)。步骤用 checkbox(`- [ ]`)跟踪。

**Goal:** 让三个休眠零预测器模块 M1(膜系统)/M5(生物合成)/M8(降解)在相关基因扰动时进 module_plan 并挂 rule_based/evidence_limited advisory(不伪造任何数值 delta),把它们从"从不激活"提升到"可运行 case",达 G2「8/8 至少可运行」。

**Architecture:** 纯**模块层**扩展(module_plan advisory,非引擎/裁决)。新增公开策展 gene-set 数据 + 确定性加载器 → 扩 `module_rules.pick_secondary`(gene-set 命中 → 加 M1/M5/M8 secondary)→ `ModuleRouterAgent._build_entry` 对 gene-set 激活的 entry 叠加 advisory(caution_flags `rule_based:<module>_gene_set`+`evidence_limited`、`route_disposition=downgrade`、reason 追加)。**不碰 reliability/critic/引擎/case_dispatch/route() 裁决**;module_plan 经既有 `provenance.module_plan` 透出;预测仍归请求级引擎(donor_predictor 等),M1/M5/M8 零 delta。

**Tech Stack:** Python 3、`json`+`functools.lru_cache`(加载器)、pytest;既有 `ModulePlan`/`ModulePlanEntry` dataclass、`route_table.route()`、`SpeciesContextAgent`+`ModuleRouterAgent` 消息链、`run_query` 端到端 harness。

---

## ⚠️ 对 spec 的一处刻意偏离(数据路径,已核对约定)

spec §二 写数据落 `praxis_virtualcell/data/module_gene_sets/`,但该目录**不存在**;全仓策展数据的既定约定是**仓库根 `data/`**(实测:`data/gems/`、`data/drug_signatures/`、`data/cellstate/` 均由 `Path(__file__).resolve().parents[3] / "data" / ...` 定位,B1/B2/B3 全部沿用)。本 plan 把 gene-set 数据落 **`data/module_gene_sets/`**(仓库根),与 B1/B2/B3 数据约定一致;加载器从 `praxis_virtualcell/biological_modules/module_gene_sets.py` 用 `parents[2] / "data" / "module_gene_sets"` 定位。spec 的意图(公开策展 gene-set 数据目录 + 精确匹配加载器)完全保留,仅位置对齐约定。

## 勘察坐实的关键事实(写 plan 前已核对,implementer 可信赖)

1. **零碰撞**:58 个 gene-set 基因符号在全部 `praxis_virtualcell/tests/*.py` 与两个 golden yaml(`module_golden_cases/module_representative.yaml`、`module_safety.yaml`)中**零出现**(`git grep` 实测)。既有 module routing 测试的靶标全是 AHR/MYC/Gata1/b0720/SNF1/SNAI1/vorinostat/lon,均不在 gene-set → `pick_secondary` 加 M1/M5/M8 对既有测试是**纯增量,不打破任何断言**。
2. **红线安全**:仓库根 `tests/`(继承 PRAXIS-2 的 214 框架测试)**不引用任何 module routing 符号**(`git grep` 实测)——B4 module 层改动不触碰红线 tests/。
3. **verdict 链(human)**:`registry._VERDICT = {"strong":"accept","medium":"accept","weak":"caution","unsupported":"reject"}`;human 的 M1/M5/M8 `module_support.yaml` 均 `support: weak` → `species_verdict = "caution"`(severity 1)。`synthesize_verdict(route_disposition, species_verdict, mismatch)` 取最保守:`synthesize("downgrade"(2), "caution"(1), None) = "downgrade"(2)`。故 M1/M5/M8 entry 端到端 verdict = **downgrade**(非 reject,不拖整请求成 abstain),`overall_verdict = max(M2 accept=0, M1 downgrade=2) = downgrade`。**完全符合 spec 意图。**
4. **advisory 独立(非 abstain)**:`core/runtime.py` 中 `module_plan` 只挂 `report["provenance"]["module_plan"]`(约 line 109),`reliability_decision` 由独立 dispatch(约 line 98)从 used predictors 算,**不读 module_plan.overall_verdict**。故 M1 downgrade advisory **不影响** `reliability_decision.abstain` 与主预测数值。
5. **governance 兼容**:`governance/module_consistency.py` 的漂移检查 `if legal_engines and ...`——M1/M5/M8 `MODULES[mid]["engines"] == []`(falsy)→ 跳过,无 `engine_module_drift` note;`overall_more_optimistic` 检查:overall=downgrade 与最保守 entry(downgrade)一致 → 不触发。
6. **`safety_contract.build_candidate_modules` 连带**:它也调 `pick_secondary`(LLM 路径候选集)。gene-set 命中时候选集会含 M1/M5/M8——语义正确(该基因确实相关),`assert_plan_within_bounds` 因候选集同步扩张而仍通过。OFFLINE 主链走 `pick_secondary` 直取,不经此函数。

## File Structure

- **Create** `data/module_gene_sets/membrane_system.json`(M1 策展 gene-set)
- **Create** `data/module_gene_sets/biosynthetic_network.json`(M5)
- **Create** `data/module_gene_sets/degradation_machinery.json`(M8)
- **Create** `praxis_virtualcell/biological_modules/module_gene_sets.py`(加载器:`gene_set_of` / `modules_hit_by` / `GENE_SET_MODULES`)
- **Modify** `praxis_virtualcell/agents/module_rules.py`(加 `_M1`/`_M5` 常量;`pick_secondary` 末尾并入 gene-set 激活)
- **Modify** `praxis_virtualcell/agents/module_router_agent.py`(`_build_entry` 对 gene-set 激活 entry 叠加 advisory)
- **Modify** `praxis_virtualcell/tests/test_module_router_agent.py`(仅更新 line 69-77 陈旧 docstring:M8 现可经 gene-set 激活作 secondary)
- **Test(扩)** `praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py`(追加 `P10.B4` 段:gene-set 单元 + pick_secondary + 端到端 advisory + 诚实红线 + 8/8 可运行)

**测试口径(铁律)**:全量永远 `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider`;单测 `... -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k b4 -p no:cacheprovider`。绝不裸跑 `pytest`。子代理环境缺 SCGPT_CKPT/GEARS_CKPT 会得一堆 ML failed,是环境依赖非回归;以规范命令为准,数值/字节等价控制器独立复验。

**⚠️ import 位置约定(Task 1 code review 修正)**:`test_t10_2_module_contracts.py` 既有约定是**所有顶层 import 都在文件头部**(该文件与整个 phase10 套件无 mid-file import 先例)。下文各 task 的测试代码块里为可读性写在 `# ===== P10.B4 =====` 段内的 `from ... import ...` 行,**落地时一律移到文件顶部既有 import 块**(按 isort 字母序插入),不得留 mid-file import(否则触发 ruff E402,Task 5 ruff 全检会判红)。测试段内只保留测试函数与 `_b4_*` helper。

---

## Task 1:gene-set 数据 + 确定性加载器

**Files:**
- Create: `data/module_gene_sets/membrane_system.json`
- Create: `data/module_gene_sets/biosynthetic_network.json`
- Create: `data/module_gene_sets/degradation_machinery.json`
- Create: `praxis_virtualcell/biological_modules/module_gene_sets.py`
- Test: `praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py`(追加 B4 gene-set 单元段)

- [ ] **Step 1:写三个 gene-set 数据文件**

`data/module_gene_sets/membrane_system.json`:
```json
{
  "module": "M1",
  "module_id": "membrane_system",
  "source": "curated public (GO/Reactome-style)",
  "note": "rule-based advisory only; qualitative membership, no numeric delta",
  "gene_set": ["FASN", "SCD", "SREBF1", "SREBF2", "HMGCR", "ACACA", "ELOVL6", "DGAT1",
               "SLC2A1", "SLC7A5", "SLC1A5", "SLC3A2", "SLC16A1", "ATP1A1", "ATP2A2",
               "CAV1", "FLOT1", "ABCA1", "ABCB1"]
}
```

`data/module_gene_sets/biosynthetic_network.json`:
```json
{
  "module": "M5",
  "module_id": "biosynthetic_network",
  "source": "curated public (GO/Reactome-style)",
  "note": "rule-based advisory only; qualitative membership, no numeric delta",
  "gene_set": ["RPL5", "RPL11", "RPL23", "RPS3", "RPS6", "RPS19", "XBP1", "ATF6", "ERN1",
               "HSPA5", "EIF2AK3", "DDIT3", "HSP90AA1", "CALR", "EIF4E", "EIF2S1", "MTOR",
               "PDIA3"]
}
```

`data/module_gene_sets/degradation_machinery.json`:
```json
{
  "module": "M8",
  "module_id": "degradation_machinery",
  "source": "curated public (GO/Reactome-style)",
  "note": "rule-based advisory only; qualitative membership, no numeric delta",
  "gene_set": ["PSMA1", "PSMA5", "PSMB5", "PSMB6", "PSMC1", "PSMD1", "UBB", "UBC", "UBA1",
               "UBE2D1", "ATG5", "ATG7", "ATG12", "MAP1LC3B", "SQSTM1", "BECN1", "ULK1",
               "LAMP1", "CTSB", "CTSD"]
}
```

- [ ] **Step 2:写加载器的失败测试**(追加到 `test_t10_2_module_contracts.py` 末尾)

```python
# ==================== P10.B4:M1/M5/M8 rule-based advisory ====================
from praxis_virtualcell.biological_modules import module_gene_sets as MGS


def test_b4_gene_set_of_membrane_has_real_symbols():
    gs = MGS.gene_set_of("membrane_system")
    assert isinstance(gs, frozenset)
    assert {"SLC2A1", "FASN", "SREBF1"} <= gs
    # 非 gene-set 模块 → 空集(不崩)
    assert MGS.gene_set_of("genetic_hub") == frozenset()


def test_b4_modules_hit_by_single_hits():
    assert MGS.modules_hit_by(["SLC2A1"]) == ["membrane_system"]
    assert MGS.modules_hit_by(["RPS6"]) == ["biosynthetic_network"]
    assert MGS.modules_hit_by(["PSMB5"]) == ["degradation_machinery"]


def test_b4_modules_hit_by_mixed_hit_and_miss():
    # TP53 不在任何 gene-set → 只命中 degradation
    assert MGS.modules_hit_by(["PSMB5", "TP53"]) == ["degradation_machinery"]
    assert MGS.modules_hit_by(["TP53"]) == []


def test_b4_modules_hit_by_exact_match_no_substring():
    assert MGS.modules_hit_by(["slc2a1"]) == ["membrane_system"]   # 大小写归一
    assert MGS.modules_hit_by(["SLC2A"]) == []                     # 子串不误命中
    assert MGS.modules_hit_by(["XSLC2A1"]) == []                   # 前缀污染不误命中


def test_b4_modules_hit_by_multi_ordered_by_module_order():
    hits = MGS.modules_hit_by(["PSMB5", "SLC2A1", "RPS6"])
    assert hits == ["membrane_system", "biosynthetic_network", "degradation_machinery"]


def test_b4_gene_set_deterministic():
    assert MGS.gene_set_of("membrane_system") == MGS.gene_set_of("membrane_system")
    assert MGS.modules_hit_by(["SLC2A1"]) == MGS.modules_hit_by(["SLC2A1"])
```

- [ ] **Step 3:运行确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k b4 -p no:cacheprovider`
Expected: FAIL —— `ModuleNotFoundError: ... module_gene_sets`(加载器未建)。

- [ ] **Step 4:写加载器 `module_gene_sets.py`**

```python
"""M1/M5/M8 gene-set 加载与命中(P10.B4 rule-based advisory 数据层)。

确定性、零 LLM、lazy 缓存。gene-set 为公开策展真实基因符号(GO/Reactome-style),
仅用于让休眠模块 M1/M5/M8 在相关基因扰动时进 module_plan 并挂 rule_based/evidence_limited
advisory —— 不产任何数值 delta(gene-set 成员只能给定性 advisory,数值预测=过度声称)。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from praxis_virtualcell.biological_modules import modules as M

# gene-set 数据目录:仓库根 data/(与 data/gems、data/drug_signatures、data/cellstate 同源约定)
_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "module_gene_sets"

# gene-set 覆盖的模块 id(∈ MODULE_ORDER)→ 数据文件名。声明序 = M1,M5,M8。
_MODULE_FILES: dict[str, str] = {
    "membrane_system": "membrane_system.json",
    "biosynthetic_network": "biosynthetic_network.json",
    "degradation_machinery": "degradation_machinery.json",
}

# 供上层判「该 module 是否 gene-set advisory 模块」(公开只读集合)
GENE_SET_MODULES = frozenset(_MODULE_FILES)


@lru_cache(maxsize=None)
def gene_set_of(module_code: str) -> frozenset[str]:
    """返回 module 的大写基因符号集(lazy 读 JSON,缓存)。非 gene-set 模块 → 空集。"""
    fname = _MODULE_FILES.get(module_code)
    if fname is None:
        return frozenset()
    doc = json.loads((_DATA_DIR / fname).read_text(encoding="utf-8"))
    return frozenset(str(g).strip().upper() for g in doc.get("gene_set", []))


def modules_hit_by(targets: list[str]) -> list[str]:
    """targets 命中的 module id(M1/M5/M8 子集),按 MODULE_ORDER 序、去重。
    精确大写归一匹配(防子串误命中,B3 IFNB2/IL-6 教训)。"""
    norm = {str(t).strip().upper() for t in (targets or []) if str(t).strip()}
    hits = [mid for mid in _MODULE_FILES if norm & gene_set_of(mid)]
    return sorted(hits, key=M.MODULE_ORDER.index)
```

- [ ] **Step 5:运行确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k b4 -p no:cacheprovider`
Expected: PASS(6 个 b4 gene-set 单元全绿)。

- [ ] **Step 6:ruff + commit**

Run: `.venv/bin/ruff check praxis_virtualcell/biological_modules/module_gene_sets.py`
Expected: 全绿。

```bash
git add data/module_gene_sets/ praxis_virtualcell/biological_modules/module_gene_sets.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "$(cat <<'EOF'
feat(phase10b4): Task 1 gene-set 数据 + 确定性加载器(M1/M5/M8 精确匹配,零 delta)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2:`pick_secondary` 并入 gene-set 激活

**Files:**
- Modify: `praxis_virtualcell/agents/module_rules.py`
- Test: `praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py`(追加 B4 pick_secondary 段)

- [ ] **Step 1:写失败测试**(追加)

```python
from praxis_virtualcell.agents import module_rules as MR
from praxis_virtualcell.agents.species_schema import normalize_request as _norm


def _b4_norm_req(**kw):
    base = {"species": "human", "perturbation_object": "gene",
            "target_output": "expression", "perturbation_targets": ["SLC2A1"]}
    base.update(kw)
    return _norm(base)


def test_b4_pick_secondary_membrane_gene_adds_m1():
    sec = MR.pick_secondary(_b4_norm_req(), "genetic_hub")
    assert "membrane_system" in sec


def test_b4_pick_secondary_degradation_gene_adds_m8():
    sec = MR.pick_secondary(_b4_norm_req(perturbation_targets=["PSMB5"]), "genetic_hub")
    assert "degradation_machinery" in sec


def test_b4_pick_secondary_non_hit_gene_adds_nothing():
    sec = MR.pick_secondary(_b4_norm_req(perturbation_targets=["TP53"]), "genetic_hub")
    assert not ({"membrane_system", "biosynthetic_network", "degradation_machinery"} & set(sec))


def test_b4_pick_secondary_excludes_primary_and_dedups():
    # 防御:即便 primary 恰为 gene-set 模块也排除(现状 primary 永不为 M1/M5/M8)
    sec = MR.pick_secondary(_b4_norm_req(), "membrane_system")
    assert "membrane_system" not in sec
    # 去重:结果无重复
    assert len(sec) == len(set(sec))


def test_b4_pick_secondary_preserves_m3_for_mammalian_growth():
    # 现有 M3 逻辑不变:human growth 仍加 M3;若靶标同时命中 gene-set 则并存
    req = _b4_norm_req(target_output="growth", perturbation_targets=["SLC2A1"])
    sec = MR.pick_secondary(req, "cytoplasmic_metabolism")
    assert "mitochondrial_energy_metabolism" in sec   # M3 保留
    assert "membrane_system" in sec                   # gene-set 命中并存
```

- [ ] **Step 2:运行确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "b4_pick_secondary" -p no:cacheprovider`
Expected: FAIL(`membrane_system` 未进 secondary)。

- [ ] **Step 3:扩 `module_rules.py`**

顶部加常量(在既有 `_M2..._M8` 常量块内补):
```python
_M1 = "membrane_system"
_M5 = "biosynthetic_network"
```

顶部 import 区(在 `from __future__ import annotations` 之后)加:
```python
from praxis_virtualcell.biological_modules import module_gene_sets
```

把 `pick_secondary` 整体替换为:
```python
def pick_secondary(req: dict, primary: str) -> list[str]:
    """决策 M1 secondary:最小确定性集。哺乳类 growth/flux 加 M3 能量代谢为 secondary;
    P10.B4:gene-set(膜/生物合成/降解)命中的基因扰动 → 并入 M1/M5/M8 rule-based advisory
    secondary(module_plan advisory,非权威 abstain;预测仍归请求级引擎,M1/M5/M8 零 delta)。"""
    out = req["target_output"]
    species = req["species"]
    sec: list[str] = []
    if out in _METABOLIC and species in ("human", "mouse"):
        sec.append(_M3)
    # gene-set 命中的休眠模块作 advisory secondary(现有 M3 逻辑不变)
    sec += module_gene_sets.modules_hit_by(req.get("perturbation_targets", []))
    # 去重(保序)+ 排除 primary
    result: list[str] = []
    for m in sec:
        if m != primary and m not in result:
            result.append(m)
    return result
```

- [ ] **Step 4:运行确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "b4_pick_secondary" -p no:cacheprovider`
Expected: PASS(5 个 pick_secondary 测试全绿)。

- [ ] **Step 5:回归既有 module_rules / router 测试(证明零碰撞)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_rules.py praxis_virtualcell/tests/test_module_router_agent.py praxis_virtualcell/tests/test_module_golden_cases.py praxis_virtualcell/tests/test_module_consistency.py praxis_virtualcell/tests/test_llm_orchestration_contract.py -p no:cacheprovider`
Expected: 全 PASS(既有靶标 AHR/MYC/... 不在 gene-set,行为不变)。若有 FAIL,**停止**——说明碰撞假设有误,报告控制器复核(不改 golden 迁就)。

- [ ] **Step 6:ruff + commit**

```bash
.venv/bin/ruff check praxis_virtualcell/agents/module_rules.py
git add praxis_virtualcell/agents/module_rules.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "$(cat <<'EOF'
feat(phase10b4): Task 2 pick_secondary 并入 gene-set 激活(M1/M5/M8 advisory secondary,现有 M3 逻辑不变)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3:`_build_entry` 叠加 rule-based advisory

**Files:**
- Modify: `praxis_virtualcell/agents/module_router_agent.py`
- Test: `praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py`(追加 B4 端到端 module_plan 段)

- [ ] **Step 1:写失败测试**(追加;复刻 SpeciesContext→ModuleRouter 全链路的本地 helper)

```python
from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent


def _b4_plan_for(request):
    """SpeciesContext → ModuleRouter 全链路,返回 module_plan_ready payload(dict)。request 为 raw。"""
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


_B4_RAW_MEMBRANE = {"species": "human", "perturbation_object": "gene",
                    "target_output": "expression", "perturbation_targets": ["SLC2A1"]}


def test_b4_membrane_entry_carries_rule_based_advisory():
    p = _b4_plan_for(dict(_B4_RAW_MEMBRANE))
    m1 = next(e for e in p["entries"] if e["module"] == "membrane_system")
    assert m1["role"] == "secondary"
    assert m1["route_disposition"] == "downgrade"            # 非 accept(不伪装)、非 reject(不拖 abstain)
    assert m1["species_verdict"] == "caution"                # human membrane weak→caution
    assert m1["verdict"] == "downgrade"                      # synthesize(downgrade,caution,None)=downgrade
    assert "rule_based:membrane_system_gene_set" in m1["caution_flags"]
    assert "evidence_limited" in m1["caution_flags"]
    assert "rule_based_gene_set_advisory" in m1["reason"]


def test_b4_overall_verdict_downgrades_not_abstain():
    p = _b4_plan_for(dict(_B4_RAW_MEMBRANE))
    assert p["overall_verdict"] == "downgrade"               # 不是 abstain/reject
    # primary M2 entry 未被 advisory 污染
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["module"] == "genetic_hub"
    assert prim["verdict"] == "accept"
    assert "rule_based:membrane_system_gene_set" not in prim["caution_flags"]


def test_b4_non_gene_set_gene_no_advisory_entry():
    p = _b4_plan_for(dict(_B4_RAW_MEMBRANE, perturbation_targets=["TP53"]))
    modules = {e["module"] for e in p["entries"]}
    assert not ({"membrane_system", "biosynthetic_network", "degradation_machinery"} & modules)
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["verdict"] == "accept"                       # 非命中基因行为不变


def test_b4_advisory_entry_has_no_numeric_delta_field():
    p = _b4_plan_for(dict(_B4_RAW_MEMBRANE))
    m1 = next(e for e in p["entries"] if e["module"] == "membrane_system")
    # ModulePlanEntry 无任何数值 delta/prediction 字段(定性 advisory,零伪造)
    assert "delta" not in m1
    assert "prediction" not in m1
```

- [ ] **Step 2:运行确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "b4_membrane_entry or b4_overall_verdict or b4_non_gene_set_gene_no_advisory or b4_advisory_entry_has_no" -p no:cacheprovider`
Expected: FAIL(`route_disposition` 仍为 route() 的原值 accept,无 rule_based flag)。

- [ ] **Step 3:改 `_build_entry`**

顶部 import 区加(与既有 module import 同块):
```python
from praxis_virtualcell.biological_modules import module_gene_sets
```

在 `_build_entry` 内,把「构造 `ModulePlanEntry` 之前」的部分改为(在 `mismatch = ...` 行之后、`return ModulePlanEntry(...)` 之前插入 advisory 叠加,并让 return 用叠加后的变量):
```python
        mq = module_rules.mismatch_query_for(req, mid)
        mismatch = mismatch_queries.get(mq) if mq else None

        # P10.B4:gene-set 激活的休眠模块 M1/M5/M8 挂 rule_based/evidence_limited advisory。
        # 仅当该 module 因 gene-set 命中而进 plan 时叠加(modules_hit_by 只返回 M1/M5/M8);
        # 不伪装定量预测(downgrade,无数值 delta)、不改 engine/route()、不碰其余字段。
        disposition = dec.disposition
        caution = list(dec.caution_flags)
        reason = dec.reason
        if mid in module_gene_sets.modules_hit_by(req.get("perturbation_targets", [])):
            disposition = "downgrade"
            caution += [f"rule_based:{mid}_gene_set", "evidence_limited"]
            reason = (f"{reason} | rule_based_gene_set_advisory" if reason
                      else "rule_based_gene_set_advisory")

        return ModulePlanEntry(
            module=mid,
            display_name=sup.get("display_name", M.display_name(mid, species=species)),
            role=role,
            engine=dec.engine,
            route_disposition=disposition,
            species_support=sup["support"],
            species_verdict=sup["verdict"],
            caution_flags=caution,
            data_gated=dec.data_gated,
            pillars=list(M.MODULES[mid]["pillars"]),
            available_models=list(sup.get("models", [])),
            reason=reason,
            mismatch=mismatch,
        )
```

（注:`engine=dec.engine` 保持请求级路由结果不变——secondary 复用 primary 路由是既有设计[module_router_agent 顶部注释],advisory 的 downgrade/evidence_limited 已明示"这是 M1 advisory 非真实 M1 预测";这一点留 opus final review 复核是否需在 reason 里进一步说明。）

- [ ] **Step 4:运行确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "b4_membrane_entry or b4_overall_verdict or b4_non_gene_set_gene_no_advisory or b4_advisory_entry_has_no" -p no:cacheprovider`
Expected: PASS。

- [ ] **Step 5:回归既有 router / golden / consistency 测试**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_router_agent.py praxis_virtualcell/tests/test_module_golden_cases.py praxis_virtualcell/tests/test_module_consistency.py praxis_virtualcell/tests/test_runtime_module_plan.py praxis_virtualcell/tests/test_report_markdown.py -p no:cacheprovider`
Expected: 全 PASS(既有靶标非 gene-set → advisory 分支不触发,行为不变)。

- [ ] **Step 6:ruff + commit**

```bash
.venv/bin/ruff check praxis_virtualcell/agents/module_router_agent.py
git add praxis_virtualcell/agents/module_router_agent.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "$(cat <<'EOF'
feat(phase10b4): Task 3 _build_entry 叠加 rule_based/evidence_limited advisory(downgrade,零 delta,不碰 engine/route)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4:端到端非干扰 + 诚实红线 + 陈旧 docstring 修

**Files:**
- Modify: `praxis_virtualcell/tests/test_module_router_agent.py`(仅更新 line 69-77 陈旧 docstring)
- Test: `praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py`(追加 B4 端到端 run_query 段)

- [ ] **Step 1:写端到端失败测试**(追加;经完整 `run_query` 证明 advisory 不改预测/不拖 abstain)

```python
_B4_RUNQ_MEMBRANE = {"species": "human", "perturbation_type": "gene",
                     "perturbation_targets": ["SLC2A1"], "input_modality": "scRNA",
                     "output_modality": "delta_expression",
                     "task_type": "predict_delta_expression"}


def test_b4_advisory_does_not_abstain_or_alter_prediction_e2e():
    out = run_query(dict(_B4_RUNQ_MEMBRANE), config=_CFG)
    # module_plan 是 advisory:M1 downgrade 不拖 reliability abstain
    assert out["reliability_decision"]["abstain"] is False
    assert out["llm_used_for_prediction"] is False
    sr = out["structured_report"]
    # 预测仍由 donor 引擎产(mock 3-model),非空;不含 CaseRunner
    assert sr["prediction"] is not None
    assert "CaseRunner" not in sr["provenance"]["models_used"]
    # provenance.module_plan 含 M1 advisory entry
    m1 = next(e for e in sr["provenance"]["module_plan"]["entries"]
              if e["module"] == "membrane_system")
    assert m1["verdict"] == "downgrade"
    assert "rule_based:membrane_system_gene_set" in m1["caution_flags"]
    assert "evidence_limited" in m1["caution_flags"]


def test_b4_membrane_request_deterministic_byte_equal():
    outs = [run_query(dict(_B4_RUNQ_MEMBRANE), config=_CFG) for _ in range(3)]
    assert len({_canon(o["structured_report"]) for o in outs}) == 1
    assert len({_canon(o["trace"]) for o in outs}) == 1


def test_b4_all_three_modules_runnable_e2e():
    # G2 8/8:M1/M5/M8 各至少一个基因请求使其进 module_plan 并产 advisory
    for gene, module in [("SLC2A1", "membrane_system"), ("RPS6", "biosynthetic_network"),
                         ("PSMB5", "degradation_machinery")]:
        out = run_query(dict(_B4_RUNQ_MEMBRANE, perturbation_targets=[gene]), config=_CFG)
        entries = out["structured_report"]["provenance"]["module_plan"]["entries"]
        entry = next((e for e in entries if e["module"] == module), None)
        assert entry is not None, f"{gene} 未激活 {module}"
        assert f"rule_based:{module}_gene_set" in entry["caution_flags"]
        assert "evidence_limited" in entry["caution_flags"]
        assert entry["route_disposition"] == "downgrade"
```

- [ ] **Step 2:运行确认失败/通过判定**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "b4_advisory_does_not or b4_membrane_request_deterministic or b4_all_three_modules_runnable" -p no:cacheprovider`
Expected: **应全 PASS**(Task 1-3 已实现全部行为;本 task 是端到端断言,无新源码)。若某条 FAIL:
- 若 `provenance.module_plan` 键不存在于 mock human 路径 → **停止报告控制器**(需确认 runtime 对 mock 路径是否建 module_plan;勘察结论是"routable 请求建",但以实跑为准,不擅自改 runtime gating)。
- 若 `sr["prediction"]` 结构不同 → 按实际 mock 预测结构调整断言(仍须证明非空 + 不含 CaseRunner)。

- [ ] **Step 3:修 `test_module_router_agent.py` 陈旧 docstring**

`test_yeast_niche_mismatch_downgrades` 的 docstring(line 69-77)现声称"M8 从不作为 primary/secondary 出现"——B4 后 M8 可经 gene-set 激活作 secondary。把该 docstring 中间段替换为:
```python
    """决策 E(可达路径):yeast + niche state → primary M6 cytoskeletal_framework →
    mismatch query tissue_spatial_niche → registry 判 reject → entry verdict 降级不 accept。

    注:本 case 靶标(SNF1)不在 P10.B4 gene-set,故不触发 M1/M5/M8 gene-set 激活;
    mismatch 降级红线由本 yeast niche 端到端路径覆盖。
    (P10.B4 起 M8/M1/M5 可经 gene-set 命中作 advisory secondary,见 test_t10_2 的 B4 段;
    但那是 rule_based/evidence_limited advisory,与本处 mismatch 降级红线是两条独立路径。)"""
```
（其余断言逐字不动——SNF1 非 gene-set 基因,plan 与断言不变。）

- [ ] **Step 4:回归受影响文件 + 确认 docstring 改动不破坏测试**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_router_agent.py -p no:cacheprovider`
Expected: 全 PASS(仅 docstring 变,断言不变)。

- [ ] **Step 5:commit**

```bash
git add praxis_virtualcell/tests/test_module_router_agent.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "$(cat <<'EOF'
test(phase10b4): Task 4 端到端非干扰(advisory 不改预测/不拖 abstain/字节稳)+ 8/8 可运行 + 修 M8 陈旧 docstring

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5:全量回归 + 确定性 + ruff 收口

**Files:** 无源码改动(纯核验 + 台账留给控制器)。

- [ ] **Step 1:全量回归(规范命令)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider`
Expected:相较 B3 基线 **736 passed/39 skipped/0 failed** 净增 B4 新测(约 +20),**0 failed**。子代理环境若报 SCGPT/GEARS 相关 ML failed → 记为环境依赖非回归,控制器用规范命令独立复验。**0 failed 之外的任何 failed 必须定位到"确由 gene-set 激活引起的语义提升"或真 bug;真 bug 停止修复,不改 golden 迁就。**

- [ ] **Step 2:ruff 全绿**

Run: `.venv/bin/ruff check praxis_virtualcell/biological_modules/module_gene_sets.py praxis_virtualcell/agents/module_rules.py praxis_virtualcell/agents/module_router_agent.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py`
Expected: `All checks passed!`

- [ ] **Step 3:确定性字节稳独立复验**(控制器亲验,不只信子代理)

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "b4_membrane_request_deterministic or b4_real or byte_equal" -p no:cacheprovider`
Expected: PASS(3 跑字节一致)。

- [ ] **Step 4:报告控制器(不自行合并/勾账)**

输出:新增测试数、全量 passed/skipped/failed、各 commit hash、`git status` 干净、确认 `core/`+根 `tests/`+`reliability`/`critic` 裁决零改动。**由控制器做 opus final review + 台账勾账 + 暂停问用户是否 FF 合并 main。**

---

## Self-Review(对照 spec 落实核对)

- **spec §一 目标**:M1/M5/M8 从"从不激活"→ Task 2/3 使 gene-set 命中时进 module_plan 并产 advisory,达 G2 8/8 → Task 4 Step1 `test_b4_all_three_modules_runnable_e2e` 覆盖。✅
- **spec §二 gene-set 数据**:Task 1 三个 JSON 逐符号照落(19+18+20),`str(target).strip().upper()` 精确匹配 → Task 1 Step4 + `test_b4_modules_hit_by_exact_match_no_substring`。✅(路径偏离已在顶部显式声明。)
- **spec §三.1 加载器**:`gene_set_of`/`modules_hit_by` + 确定性缓存 → Task 1。✅
- **spec §三.2 pick_secondary**:末尾并入 `modules_hit_by`,去重排除 primary,M3 逻辑不变 → Task 2 + `test_b4_pick_secondary_preserves_m3_for_mammalian_growth`。✅
- **spec §三.3 entry advisory**:caution_flags 加 `rule_based:<module>_gene_set`+`evidence_limited`、disposition→downgrade、reason 追加 → Task 3。✅
- **spec §四 数据流 / §五 影响**:预测仍由引擎产、reliability.abstain 不受影响、非命中基因不激活 → Task 4 端到端三测。✅
- **spec §六 测试**:gene-set 单元 / module_rules / 端到端 / 诚实红线(无 delta、rule_based/evidence_limited、非命中不激活、确定性)/ 8/8 → Task 1-4 全覆盖。✅
- **spec §七 红线**:不碰 reliability/critic/引擎/case_dispatch/route();gene-set 精确匹配;核心+根 tests/ 零触碰;trailer 恒 Opus4.8;不 push。→ 各 task commit 范围受限,Task 5 Step4 明列核验项。✅
- **类型一致性**:`gene_set_of(str)->frozenset[str]`、`modules_hit_by(list)->list[str]`、`GENE_SET_MODULES: frozenset` 在 Task 1 定义,Task 2(`pick_secondary` 调 `modules_hit_by`)、Task 3(`_build_entry` 调 `modules_hit_by`)、测试(`MGS.gene_set_of`/`MGS.modules_hit_by`)一致;`ModulePlanEntry` 字段名(module/role/route_disposition/species_verdict/caution_flags/verdict/reason)在既有 dataclass 与 Task 3 构造、Task 3/4 断言一致。✅
- **占位符扫描**:无 TBD/TODO;每 code step 含完整代码。✅

## 收官后控制器职责(不在本 plan task 内)

1. **opus final review**(铁律,B1/B2/B3 每次都抓到 per-task 漏掉的跨 task 接缝/过度声称)——重点审:①`engine=dec.engine` 在 M1 advisory entry 是否读作"M1 有 donor 引擎"的过度声称;②overall_verdict=downgrade 是否有下游(report_markdown/前端/module_consistency)误读;③三 gene-set 是否有跨模块重复基因导致多激活的意外;④gene-set 数据是否夹带非真实符号。
2. 台账勾账:`UPGRADE-PROGRESS.md` + `memory/phase10-deep-validation.md`(M1/M5/M8 从 limitation → rule-based advisory 可运行)+ `MEMORY.md` 索引。
3. **暂停问用户是否 FF 合并 main**(合则不 push、保留分支)。
