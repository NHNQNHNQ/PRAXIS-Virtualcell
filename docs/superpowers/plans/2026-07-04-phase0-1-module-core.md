# Phase 0 + Phase 1:冻结基线 + 八模块核心 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不碰现有运行管线的前提下,先冻结 v0.8 行为为回归安全网(Phase 0),再新增一个**自包含的 `biological_modules/` 包**——八模块规范定义 + 4 物种模块支持矩阵 + 注册表查询 + 物种特异生物学错配守卫(Phase 1),达到 v0.9 里程碑。

**Architecture:** Phase 1 全部是**新增、隔离、数据驱动**的代码,不修改 `core/`、`agents/`、`predictors/`、`route_table` 任何逻辑,因此现有 277 测试零风险保持绿。八模块用**单一数据驱动定义**(`modules.py` 常量)+ **每物种一个 `module_support.yaml`**,而非规格 §10 的 8 个目录 40 个 stub 文件(见 Task 1.1 决策说明)。`ModuleRegistry` 直接读 yaml,不进 message bus(SpeciesContextAgent 的 bus 接线留到 Phase 3,避免 Phase 1 动管线)。

**Tech Stack:** Python 3.13 / pytest 参数化 / PyYAML(已是核心依赖)。

**铁律:**
- 只**新增**文件,不改现有逻辑;若发现现有行为与预期不符→真实 bug,停下报告,不改代码迁就测试。
- 测试口径 = `praxis_virtualcell/tests`(当前 277 passed / 25 skipped),不是整仓 1602。
- 每 task 全量 `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q` 绿后再 commit。
- commit 前删 `._*`;commit message 末尾加 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`;在 main 分支上先确认无未提交改动再开工。

**数据契约(已实跑核实):**
- `examples/ahr_k562.json` = human/K562/gene/AHR/predict_delta_expression(路由 donor_predictor,mock,离线无需 cobra)。
- `run_query(request_dict, config)` 返回 `{structured_report, narrative, trace, provenance, reliability_decision, llm_used_for_prediction, mode, llm_enabled}`(`workflows/run_virtualcell_query.py:143`)。
- `render_report_md(job_like)` 的 `job_like` 形状见 `io/job_store.py:42-48`。
- brain yaml 加载:`SpeciesBrainAgent` 读 `brains_root/{species}/*.yaml`(`agents/species_brain.py:44`);`RuntimeConfig.brains_root` 默认 = `praxis_virtualcell/brains/virtualcell`。
- 物种/对象/输出白名单:`agents/species_schema.py:14-20`。

---

# Phase 0:冻结当前 v0.8

## Task 0.1:基线架构文档

**Files:**
- Create: `docs/ARCHITECTURE-v0.8-baseline.md`

- [ ] **Step 1: 写基线文档**

写 `docs/ARCHITECTURE-v0.8-baseline.md`:

```markdown
# PRAXIS-VirtualCell v0.8 架构基线(冻结点)

> 冻结日期 2026-07-04 · tag `v0.8.0`(commit 7fc4aa5)· 升级起点。
> 详细复用映射见 `docs/superpowers/plans/2026-07-04-v0.9-v1.3-upgrade-roadmap.md`。

## 运行管线(core/runtime.py:46 run_workflow)

client → InputInterpreter → BioObjectNormalizer → SpeciesBrain → ModelApplicability
→ [LLMRouter 建议] → predictor fan-out → EnsembleCoordinator → Reliability → Critic
→ ProvenanceAgent → Report → [LLMCritic / LLMReport]

- 全程走 `MessageBus`(core/bus.py),记全量 trace 可 replay。
- 默认 mode=OFFLINE,llm_enabled=False,零 LLM token 可跑核心 case。

## 关键不变量(升级不得破坏)

1. 测试基线:`pytest praxis_virtualcell/tests` = 277 passed / 25 skipped / 0 failed。
2. LLM 边界:`assert_llm_boundaries` 三 flag(allow_llm_to_modify_core_decision /
   allow_llm_to_modify_prediction / allow_llm_to_override_hard_rules)恒 False。
3. 治理裁决:accept / caution / downgrade / abstain 四态(route_table.RouteDecision)。
4. KPI:golden unsafe-accept = 0;negative 无静默 accept。
5. offline 产 9 段 report.md(io/report_markdown.py),可复现。

## 4 物种 × 8 engine 现状

- 物种:human(原生)/ mouse(ortholog caution)/ yeast、bacteria(GEM 机制,scRNA abstain)。
- engine:donor_predictor / gem_fba / embedding / state_scoring / pathway_scoring /
  communication / spatial_niche / reject。
- 真实模型:E.coli iML1515、yeast iMM904(cobra-gated,真跑);LINCS 药物签名。
- mock / 远端:MockGEARS/MockCPA/MockLinear 本地 mock;GEARS/scGPT/Coordinator 远端 eval
  (@pytest.mark.remote,需 torch+GPU,本地 skip)。

## 继承包裹项(与虚拟细胞无关,永不维护)

- 整仓 `pytest` 会 collect ~1602(含根 tests/ 里 ~1398 个继承自 PRAXIS-2 的 Web/Auth/Admin
  框架测试,BASELINE.md 记录 14 个 pre-existing 失败)。这些是 bootstrap 时随 PRAXIS-2
  代码一起复制进来的历史包裹,与虚拟细胞科学核心无关。
- **决策(用户拍板 2026-07-04):这 ~1398 个继承测试永不纳入维护——不修、不迁移、不计入 CI
  绿勾口径、不计入 450+ 目标。升级全程只在 `praxis_virtualcell/tests` 内工作。**
```

- [ ] **Step 2: 提交**

```bash
find . -name '._*' -delete
git add docs/ARCHITECTURE-v0.8-baseline.md
git commit -m "docs(phase0): 冻结 v0.8 架构基线(管线/不变量/物种 engine 现状)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 0.2:离线报告特征化测试(pin 当前离线行为)

**Files:**
- Create: `praxis_virtualcell/tests/baseline/__init__.py`
- Create: `praxis_virtualcell/tests/baseline/test_baseline_offline_report.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/baseline/__init__.py`(空文件):

```python
```

写 `praxis_virtualcell/tests/baseline/test_baseline_offline_report.py`:

```python
"""Phase 0 基线特征化:pin v0.8 离线行为,升级过程若改变则红灯。
只读断言现有行为;若与期望不符=升级引入的真实回归,停下排查,不改此测试迁就。"""
import json
from pathlib import Path

from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.io.report_markdown import render_report_md
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_EXAMPLE = Path(__file__).resolve().parents[3] / "examples" / "ahr_k562.json"


def _offline_result():
    req = json.loads(_EXAMPLE.read_text(encoding="utf-8"))
    return req, run_query(req, config=RuntimeConfig(mode=Mode.OFFLINE))


def test_offline_run_is_zero_llm():
    _, out = _offline_result()
    assert out["mode"] == "offline"
    assert out["llm_enabled"] is False
    assert out["llm_used_for_prediction"] is False


def test_offline_ahr_accepts_and_reports_reliability():
    _, out = _offline_result()
    rd = out["reliability_decision"]
    assert rd["abstain"] is False, "human AHR gene→expression 应可预测,非弃权"
    assert rd["reliability"] in {"high", "medium", "low"}


def test_offline_report_md_has_nine_sections():
    req, out = _offline_result()
    job_like = {
        "report": out["structured_report"],
        "request": req,
        "provenance": out["provenance"],
        "mode": out["mode"],
        "llm_enabled": out["llm_enabled"],
    }
    md = render_report_md(job_like)
    for header in ("# PRAXIS-VirtualCell Report", "## 1. Question", "## 2. Cell Context"):
        assert header in md, f"报告缺段落: {header}"
    # 9 段:段落编号 1..9 全在
    for n in range(1, 10):
        assert f"## {n}." in md, f"报告缺第 {n} 段"
```

- [ ] **Step 2: 跑确认通过(特征化测试直接绿)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/baseline/test_baseline_offline_report.py -q`
Expected: 3 passed。若 `test_offline_report_md_has_nine_sections` 因段落编号断言失败,先读 `io/report_markdown.py` 核实实际段落标题,把断言改成实际标题(这是 pin 现状,不是迁就)。

- [ ] **Step 3: 全量回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 280 passed / 25 skipped / 0 failed(277 + 3 新)。

- [ ] **Step 4: 提交**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/tests/baseline/
git commit -m "test(phase0): 离线报告特征化基线(零 LLM + 9 段 + reliability)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 0.3:路由快照测试(pin 当前 4 物种路由)

**Files:**
- Create: `praxis_virtualcell/tests/baseline/test_baseline_routing_snapshot.py`

- [ ] **Step 1: 写测试**

写 `praxis_virtualcell/tests/baseline/test_baseline_routing_snapshot.py`:

```python
"""Phase 0 基线:pin 当前 4 物种代表请求的路由决策。
Phase 3 引入 module router 后,这些底层路由决策必须保持不变(module 是外层视图,
不改 engine 级路由)。若变=真实回归,停下排查。"""
import pytest

from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request

# (input, 期望 engine, 期望 disposition)—— 均为 route() 实跑锚点值
_SNAPSHOT = [
    ({"species": "human", "perturbation_object": "gene", "target_output": "expression",
      "perturbation_targets": ["AHR"]}, "donor_predictor", "accept"),
    ({"species": "mouse", "perturbation_object": "gene", "target_output": "expression",
      "perturbation_targets": ["Gata1"]}, "donor_predictor", "caution"),
    ({"species": "bacteria", "perturbation_object": "gene", "target_output": "growth",
      "perturbation_targets": ["b0720"]}, "gem_fba", "accept"),
    ({"species": "yeast", "perturbation_object": "gene", "target_output": "growth",
      "perturbation_targets": ["YBR166C"]}, "gem_fba", "accept"),
    ({"species": "bacteria", "perturbation_object": "gene", "target_output": "expression",
      "perturbation_targets": ["b0720"]}, "reject", "abstain"),
    ({"species": "yeast", "perturbation_object": "gene", "target_output": "expression",
      "perturbation_targets": ["YBR166C"]}, "reject", "abstain"),
]


@pytest.mark.parametrize("inp,engine,disp", _SNAPSHOT,
                         ids=[f"{c[0]['species']}_{c[0]['target_output']}" for c in _SNAPSHOT])
def test_routing_snapshot(inp, engine, disp):
    dec = route(normalize_request(inp))
    assert dec.engine == engine, f"engine 漂移: {dec.engine} != {engine}"
    assert dec.disposition == disp, f"disposition 漂移: {dec.disposition} != {disp}"


def test_four_species_snapshot_covered():
    assert {c[0]["species"] for c in _SNAPSHOT} == {"human", "mouse", "yeast", "bacteria"}
```

- [ ] **Step 2: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/baseline/test_baseline_routing_snapshot.py -q`
Expected: 7 passed(6 参数化 + 1 覆盖检查)。若某锚点值不符,读 `route_table.py:43` 核实真值改锚点(pin 现状)。

- [ ] **Step 3: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 287 passed / 25 skipped / 0 failed。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/tests/baseline/test_baseline_routing_snapshot.py
git commit -m "test(phase0): 4 物种路由快照基线(engine/disposition 防漂移)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

**Phase 0 验收:** 287 passed / 25 skipped / 0 failed;基线文档 + 特征化 + 路由快照三网就位。**v0.8 行为已冻结,可以安全开动 Phase 1。**

---

# Phase 1:八模块骨架 + species profile + registry

## Task 1.1:八模块规范定义 `modules.py`

**决策说明(偏离规格 §10):** 规格建议 `biological_modules/{module}/{agent,schema,evidence,tools,governance}.py`(8 目录 40 文件)。Phase 1 用**单一数据驱动定义** `modules.py`(一份 `MODULES` 常量),因为 Phase 1 阶段这 40 个文件 90% 是空 stub,违反 DRY 且"个人开发环境不要过度抽象"。当某模块后续需要 bespoke 逻辑(如 M4 接 GEM 的特殊输入),再在 Phase 3+ 为它单独建 agent 子类。数据驱动的 `MODULES` 已满足 Phase 1 验收("4×8 support matrix 可生成")。

**Files:**
- Create: `praxis_virtualcell/biological_modules/__init__.py`
- Create: `praxis_virtualcell/biological_modules/modules.py`
- Test: `praxis_virtualcell/tests/test_biological_modules.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_biological_modules.py`:

```python
"""Phase 1:八模块规范定义。测 8 模块齐全、code M1-M8、engines 合法、bacteria M3 术语别名。"""
from praxis_virtualcell.agents.route_table import ENGINES
from praxis_virtualcell.biological_modules import modules as M


def test_eight_modules_in_stable_order():
    assert len(M.MODULE_ORDER) == 8
    assert M.MODULE_ORDER == [
        "membrane_system", "genetic_hub", "mitochondrial_energy_metabolism",
        "cytoplasmic_metabolism", "biosynthetic_network", "cytoskeletal_framework",
        "stress_processor", "degradation_machinery",
    ]


def test_each_module_has_m_code():
    for i, mid in enumerate(M.MODULE_ORDER, start=1):
        assert M.MODULES[mid]["code"] == f"M{i}"


def test_module_engines_are_known_engines():
    known = set(ENGINES)
    for mid in M.MODULE_ORDER:
        for eng in M.MODULES[mid]["engines"]:
            assert eng in known, f"{mid} 引用未知 engine: {eng}"


def test_bacteria_m3_display_alias():
    # 铁律:bacteria 不叫线粒体,前端显示 energy/redox
    assert M.display_name("mitochondrial_energy_metabolism", species="bacteria") \
        == "Energy metabolism / redox module"
    # 其它物种保留原名
    assert "Mitochond" in M.display_name("mitochondrial_energy_metabolism", species="yeast")


def test_module_ids_helper():
    assert set(M.module_ids()) == set(M.MODULE_ORDER)
    assert M.module("genetic_hub")["code"] == "M2"
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_biological_modules.py -q`
Expected: FAIL(ModuleNotFoundError: biological_modules)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/biological_modules/__init__.py`:

```python
"""八大细胞功能模块(M1-M8)的规范定义 + 物种支持矩阵 + 注册表。

设计:数据驱动(modules.py 定义 8 模块;每物种 brains/virtualcell/<species>/module_support.yaml
定义支持度)。模块是逻辑视图,内部映射到现有 engine/predictor,不为每模块造新引擎。"""
```

写 `praxis_virtualcell/biological_modules/modules.py`:

```python
"""八大细胞功能模块规范定义(单一真相源)。

engines 字段 = 该模块当前映射到的现有 route_table engine(可空 = 该模块暂无直接引擎,
走规则/工具/abstain)。pillars = 三大数据支柱归属(mechanistic_knowledge /
subcellular_architecture / dynamic_states)。"""
from __future__ import annotations

# 八模块规范顺序(M1..M8),前端与 registry 均以此为准
MODULE_ORDER = [
    "membrane_system",                 # M1
    "genetic_hub",                     # M2
    "mitochondrial_energy_metabolism", # M3
    "cytoplasmic_metabolism",          # M4
    "biosynthetic_network",            # M5
    "cytoskeletal_framework",          # M6
    "stress_processor",                # M7
    "degradation_machinery",           # M8
]

MODULES: dict[str, dict] = {
    "membrane_system": {
        "code": "M1", "display_name": "Membrane System",
        "engines": [],  # 暂无直接引擎,走脂质通路规则/transporter 注释
        "pillars": ["subcellular_architecture", "mechanistic_knowledge"],
    },
    "genetic_hub": {
        "code": "M2", "display_name": "Genetic Hub",
        "engines": ["donor_predictor"],  # + 未来 GEARS/scGPT
        "pillars": ["dynamic_states", "mechanistic_knowledge"],
    },
    "mitochondrial_energy_metabolism": {
        "code": "M3", "display_name": "Mitochondrial Energy Metabolism",
        "engines": ["gem_fba", "pathway_scoring"],
        "pillars": ["mechanistic_knowledge", "dynamic_states"],
    },
    "cytoplasmic_metabolism": {
        "code": "M4", "display_name": "Cytoplasmic Metabolism",
        "engines": ["gem_fba", "pathway_scoring"],
        "pillars": ["mechanistic_knowledge", "dynamic_states"],
    },
    "biosynthetic_network": {
        "code": "M5", "display_name": "Biosynthetic Network",
        "engines": [],  # 暂无;未来 AlphaFold/ESMFold/PLM
        "pillars": ["mechanistic_knowledge", "subcellular_architecture"],
    },
    "cytoskeletal_framework": {
        "code": "M6", "display_name": "Cytoskeletal Framework",
        "engines": ["spatial_niche"],
        "pillars": ["subcellular_architecture", "dynamic_states"],
    },
    "stress_processor": {
        "code": "M7", "display_name": "Stress Processor",
        "engines": ["state_scoring", "embedding"],
        "pillars": ["dynamic_states", "mechanistic_knowledge"],
    },
    "degradation_machinery": {
        "code": "M8", "display_name": "Degradation Machinery",
        "engines": [],  # 暂无;走 proteostasis/autophagy 基因集规则
        "pillars": ["mechanistic_knowledge", "subcellular_architecture"],
    },
}

# 物种特异显示别名(铁律:bacteria 不叫线粒体)。key = (species, module_id)。
_SPECIES_DISPLAY_ALIASES = {
    ("bacteria", "mitochondrial_energy_metabolism"): "Energy metabolism / redox module",
}


def module_ids() -> list[str]:
    return list(MODULE_ORDER)


def module(module_id: str) -> dict:
    if module_id not in MODULES:
        raise KeyError(f"未知模块: {module_id}(支持: {MODULE_ORDER})")
    return MODULES[module_id]


def display_name(module_id: str, *, species: str | None = None) -> str:
    if species is not None and (species, module_id) in _SPECIES_DISPLAY_ALIASES:
        return _SPECIES_DISPLAY_ALIASES[(species, module_id)]
    return module(module_id)["display_name"]
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_biological_modules.py -q`
Expected: 5 passed。

- [ ] **Step 5: 提交**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/biological_modules/ praxis_virtualcell/tests/test_biological_modules.py
git commit -m "feat(phase1): 八模块规范定义 modules.py(M1-M8 + engine 映射 + bacteria 术语别名)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 1.2:4 物种模块支持矩阵数据 `module_support.yaml`

**Files:**
- Create: `praxis_virtualcell/brains/virtualcell/human/module_support.yaml`
- Create: `praxis_virtualcell/brains/virtualcell/mouse/module_support.yaml`
- Create: `praxis_virtualcell/brains/virtualcell/yeast/module_support.yaml`
- Create: `praxis_virtualcell/brains/virtualcell/bacteria/module_support.yaml`
- Test: `praxis_virtualcell/tests/test_module_support_data.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_module_support_data.py`:

```python
"""Phase 1:每物种 module_support.yaml 合法性。8 模块齐全 + support 枚举合法 +
unsupported/mismatch 必须带 reason(诚实:不支持要说为什么)。"""
from pathlib import Path

import pytest
import yaml

from praxis_virtualcell.biological_modules import modules as M

_ROOT = Path(__file__).resolve().parents[1] / "brains" / "virtualcell"
_SPECIES = ["human", "mouse", "yeast", "bacteria"]
_LEVELS = {"strong", "medium", "weak", "unsupported"}


def _load(species):
    return yaml.safe_load((_ROOT / species / "module_support.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("species", _SPECIES)
def test_file_exists_and_species_matches(species):
    doc = _load(species)
    assert doc["species"] == species


@pytest.mark.parametrize("species", _SPECIES)
def test_all_eight_modules_present(species):
    doc = _load(species)
    assert set(doc["modules"].keys()) == set(M.MODULE_ORDER), \
        f"{species} 的 module_support 缺模块或多模块"


@pytest.mark.parametrize("species", _SPECIES)
def test_support_levels_legal_and_reasoned(species):
    doc = _load(species)
    for mid, rec in doc["modules"].items():
        assert rec["support"] in _LEVELS, f"{species}/{mid} 非法 support: {rec['support']}"
        if rec["support"] in {"weak", "unsupported"}:
            assert rec.get("reason"), f"{species}/{mid} 弱/不支持却无 reason(不诚实)"


def test_bacteria_declares_autophagy_mismatch():
    # 铁律:细菌不能强行套自噬
    doc = _load("bacteria")
    mismatches = {m["query"] for m in doc.get("biological_mismatch", [])}
    assert "bacteria_autophagy" in mismatches


def test_yeast_declares_tissue_niche_mismatch():
    # 铁律:单细胞酵母无组织 niche
    doc = _load("yeast")
    mismatches = {m["query"] for m in doc.get("biological_mismatch", [])}
    assert "tissue_spatial_niche" in mismatches
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_support_data.py -q`
Expected: FAIL(FileNotFoundError: module_support.yaml)。

- [ ] **Step 3: 写 human 数据**

写 `praxis_virtualcell/brains/virtualcell/human/module_support.yaml`:

```yaml
# M1-M8 支持度矩阵(human)。support ∈ strong/medium/weak/unsupported。
# 权威适用性/词汇留 model_applicability.yaml + route_table;本文件只加"模块维度"视图。
species: human
modules:
  membrane_system:
    support: weak
    reason: 暂无膜系统专用引擎;仅脂质通路规则/transporter 注释间接证据
    tools: [lipid_pathway_rules, transporter_annotation]
  genetic_hub:
    support: strong
    reason: 原生 scRNA predictor(donor_predictor);Perturb-seq 领地
    models: [donor_predictor]
  mitochondrial_energy_metabolism:
    support: medium
    reason: 无机制 GEM 接入;表达层代谢通路 tendency 评分(pathway_scoring)
    models: [pathway_scoring]
  cytoplasmic_metabolism:
    support: medium
    reason: 哺乳类无机制 GEM;pathway_scoring tendency
    models: [pathway_scoring]
  biosynthetic_network:
    support: weak
    reason: 暂无蛋白丰度/折叠预测引擎;未来 AlphaFold/PLM
    tools: [ribosome_upr_gene_set]
  cytoskeletal_framework:
    support: weak
    reason: spatial_niche 仅间接;无 morphology foundation model
    models: [spatial_niche]
  stress_processor:
    support: medium
    reason: state_scoring + 药物签名(LINCS)覆盖应激状态
    models: [state_scoring, embedding]
  degradation_machinery:
    support: weak
    reason: 暂无降解通路引擎;proteasome/autophagy 基因集规则
    tools: [proteostasis_gene_set]
biological_mismatch: []
```

- [ ] **Step 4: 写 mouse 数据**

写 `praxis_virtualcell/brains/virtualcell/mouse/module_support.yaml`:

```yaml
# M1-M8 支持度矩阵(mouse)。跨 human ortholog 迁移,普遍带 caution。
species: mouse
modules:
  membrane_system:
    support: weak
    reason: 无膜系统引擎;ortholog 迁移间接
    tools: [lipid_pathway_rules]
  genetic_hub:
    support: medium
    reason: human predictor 迁移需 ortholog(caution);非原生
    models: [donor_predictor]
  mitochondrial_energy_metabolism:
    support: medium
    reason: pathway_scoring tendency,ortholog caution
    models: [pathway_scoring]
  cytoplasmic_metabolism:
    support: medium
    reason: pathway_scoring tendency,ortholog caution
    models: [pathway_scoring]
  biosynthetic_network:
    support: weak
    reason: 无引擎;ortholog 迁移间接
    tools: [ribosome_upr_gene_set]
  cytoskeletal_framework:
    support: weak
    reason: 无 morphology model
    models: [spatial_niche]
  stress_processor:
    support: medium
    reason: state_scoring ortholog 迁移
    models: [state_scoring]
  degradation_machinery:
    support: weak
    reason: 无降解引擎;基因集规则
    tools: [proteostasis_gene_set]
biological_mismatch: []
```

- [ ] **Step 5: 写 yeast 数据**

写 `praxis_virtualcell/brains/virtualcell/yeast/module_support.yaml`:

```yaml
# M1-M8 支持度矩阵(yeast)。代谢强(iMM904 GEM);scRNA/组织类不支持。
species: yeast
modules:
  membrane_system:
    support: medium
    reason: ER-Golgi trafficking/脂质合成规则;无专用预测器
    tools: [lipid_pathway_rules, trafficking_knowledge]
  genetic_hub:
    support: weak
    reason: deletion library 知识存在但无 offline scRNA predictor;待自训 deletion-to-fitness
    self_training: yeast_deletion_to_fitness
  mitochondrial_energy_metabolism:
    support: medium
    reason: respiration-fermentation switch;GEM 覆盖呼吸代谢
    models: [gem_fba]
  cytoplasmic_metabolism:
    support: strong
    reason: iMM904 GEM 真跑(碳氮源切换/氨基酸合成)
    models: [gem_fba]
  biosynthetic_network:
    support: weak
    reason: 无蛋白质量控制预测器;ER quality control 规则
    tools: [ribosome_folding_gene_set]
  cytoskeletal_framework:
    support: weak
    reason: 无 bud morphology 预测器
    self_training: yeast_bud_morphology
  stress_processor:
    support: weak
    reason: 应激颗粒/P-body 知识存在但无预测器;待自训 stress-state classifier
    self_training: yeast_stress_state
  degradation_machinery:
    support: weak
    reason: 液泡/自噬规则;无预测器
    tools: [vacuole_autophagy_gene_set]
biological_mismatch:
  - query: tissue_spatial_niche
    verdict: reject
    reason: 单细胞真菌,无组织/空间 niche 概念
  - query: mammalian_cell_communication
    verdict: reject
    reason: 无哺乳类细胞间通讯语境
```

- [ ] **Step 6: 写 bacteria 数据**

写 `praxis_virtualcell/brains/virtualcell/bacteria/module_support.yaml`:

```yaml
# M1-M8 支持度矩阵(bacteria)。代谢强(iML1515 GEM);术语需映射(M3 显示 energy/redox)。
species: bacteria
modules:
  membrane_system:
    support: medium
    reason: inner/outer membrane、LPS、cell envelope 规则;无 lipidomics 预测器
    tools: [cell_envelope_rules, transporter_annotation]
  genetic_hub:
    support: weak
    reason: nucleoid/replication 知识;无 regulon perturbation 预测器;待自训 regulon-aware model
    self_training: bacteria_regulon_response
  mitochondrial_energy_metabolism:
    support: medium
    reason: 术语映射为 respiratory chain/redox/proton motive force;GEM 覆盖呼吸链
    display_alias: Energy metabolism / redox module
    models: [gem_fba]
  cytoplasmic_metabolism:
    support: strong
    reason: iML1515 GEM 真跑(碳源切换/必需基因/抗生素代谢靶)
    models: [gem_fba]
  biosynthetic_network:
    support: weak
    reason: ribosome/chaperone/分泌系统规则;无预测器
    tools: [chaperone_secretion_gene_set]
  cytoskeletal_framework:
    support: weak
    reason: MreB/FtsZ/细胞形状规则;待自训 cell shape/division 预测器
    self_training: bacteria_cell_shape
  stress_processor:
    support: weak
    reason: SOS/heat shock/stringent response 规则;待自训 antibiotic stress classifier
    self_training: bacteria_antibiotic_stress
  degradation_machinery:
    support: weak
    reason: ATP-依赖蛋白酶/蛋白质量控制;无预测器
    tools: [atp_protease_gene_set]
biological_mismatch:
  - query: bacteria_autophagy
    verdict: caution
    reason: 原核生物无真核自噬机制;不可强行套用,应指向蛋白酶/蛋白质量控制
  - query: mitochondria
    verdict: caution
    reason: 原核无线粒体;应映射到 M3 energy/redox 模块(呼吸链)
```

- [ ] **Step 7: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_support_data.py -q`
Expected: 14 passed(4×3 参数化 + 2 mismatch)。

- [ ] **Step 8: 提交**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/brains/virtualcell/*/module_support.yaml praxis_virtualcell/tests/test_module_support_data.py
git commit -m "feat(phase1): 4 物种 8 模块支持矩阵 module_support.yaml(含 bacteria 自噬/组织错配声明)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 1.3:模块注册表 `registry.py`

**Files:**
- Create: `praxis_virtualcell/biological_modules/registry.py`
- Test: `praxis_virtualcell/tests/test_module_registry.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_module_registry.py`:

```python
"""Phase 1:ModuleRegistry 查询。4×8 support matrix 可生成;support→verdict 映射;
unsupported 模块 reject/caution;生物学错配返回 verdict。"""
import pytest

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.biological_modules.registry import ModuleRegistry


@pytest.fixture(scope="module")
def reg():
    return ModuleRegistry()  # 默认 brains_root


def test_matrix_is_four_by_eight(reg):
    mat = reg.matrix()
    assert set(mat.keys()) == {"human", "mouse", "yeast", "bacteria"}
    for species, row in mat.items():
        assert set(row.keys()) == set(M.MODULE_ORDER), f"{species} 行不是 8 模块"


def test_support_query_returns_level_and_reason(reg):
    rec = reg.support("yeast", "cytoplasmic_metabolism")
    assert rec["support"] == "strong"
    rec2 = reg.support("yeast", "genetic_hub")
    assert rec2["support"] == "weak"
    assert rec2["reason"]


def test_verdict_mapping(reg):
    # strong/medium → 可用(非弃权);weak → caution;unsupported → reject
    assert reg.default_verdict("yeast", "cytoplasmic_metabolism") == "accept"
    assert reg.default_verdict("yeast", "genetic_hub") == "caution"


def test_unknown_species_or_module_is_unsupported(reg):
    assert reg.support("martian", "genetic_hub")["support"] == "unsupported"
    assert reg.default_verdict("martian", "genetic_hub") == "reject"
    with pytest.raises(KeyError):
        reg.support("human", "no_such_module")


def test_biological_mismatch_lookup(reg):
    # 铁律:细菌自噬 → caution;酵母组织 niche → reject
    assert reg.biological_mismatch("bacteria", "bacteria_autophagy") == "caution"
    assert reg.biological_mismatch("yeast", "tissue_spatial_niche") == "reject"
    assert reg.biological_mismatch("human", "anything_normal") is None


def test_display_name_honors_bacteria_alias(reg):
    assert reg.display_name("bacteria", "mitochondrial_energy_metabolism") \
        == "Energy metabolism / redox module"
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_registry.py -q`
Expected: FAIL(ImportError: registry)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/biological_modules/registry.py`:

```python
"""模块注册表:读 brains/virtualcell/<species>/module_support.yaml,提供支持度/裁决/错配查询。
纯库(不进 message bus;SpeciesContextAgent 的 bus 接线在 Phase 3)。"""
from __future__ import annotations

from pathlib import Path

import yaml

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.core.config import RuntimeConfig

_SPECIES = ("human", "mouse", "yeast", "bacteria")

# support 等级 → 默认裁决(与 route_table 四态对齐)
_VERDICT = {"strong": "accept", "medium": "accept", "weak": "caution", "unsupported": "reject"}


class ModuleRegistry:
    def __init__(self, brains_root: str | None = None) -> None:
        self.root = Path(brains_root or RuntimeConfig().brains_root)
        self._cache: dict[str, dict] = {}

    def _load(self, species: str) -> dict:
        if species not in self._cache:
            fp = self.root / species / "module_support.yaml"
            self._cache[species] = (yaml.safe_load(fp.read_text(encoding="utf-8"))
                                    if fp.is_file() else {"species": species, "modules": {}})
        return self._cache[species]

    def support(self, species: str, module_id: str) -> dict:
        """返回 {support, reason?, models?, tools?, ...}。未知物种/模块 → unsupported。"""
        if module_id not in M.MODULES:
            raise KeyError(f"未知模块: {module_id}")
        rec = (self._load(species).get("modules") or {}).get(module_id)
        if not rec:
            return {"support": "unsupported", "reason": f"{species} 未声明该模块支持度"}
        return rec

    def default_verdict(self, species: str, module_id: str) -> str:
        return _VERDICT[self.support(species, module_id)["support"]]

    def matrix(self) -> dict[str, dict[str, dict]]:
        """4×8 support matrix:{species: {module_id: support_record}}。"""
        return {sp: {mid: self.support(sp, mid) for mid in M.MODULE_ORDER} for sp in _SPECIES}

    def biological_mismatch(self, species: str, query: str) -> str | None:
        """生物学错配查询 → verdict(reject/caution)或 None(无错配)。"""
        for m in (self._load(species).get("biological_mismatch") or []):
            if m.get("query") == query:
                return m.get("verdict")
        return None

    def display_name(self, species: str, module_id: str) -> str:
        return M.display_name(module_id, species=species)
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_registry.py -q`
Expected: 7 passed。

- [ ] **Step 5: 提交**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/biological_modules/registry.py praxis_virtualcell/tests/test_module_registry.py
git commit -m "feat(phase1): ModuleRegistry(4x8 support matrix + verdict 映射 + 生物错配查询)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 1.4:物种特异错配守卫测试(bacteria 不套自噬 / yeast 不套 niche)

**Files:**
- Test: `praxis_virtualcell/tests/test_species_module_guards.py`

- [ ] **Step 1: 写测试**

写 `praxis_virtualcell/tests/test_species_module_guards.py`:

```python
"""Phase 1:物种特异生物学守卫(数据驱动)。铁律:
- bacteria 不能强行解释为自噬/线粒体 → mismatch caution
- yeast/bacteria 单细胞无组织 niche → mismatch reject
- 弱支持模块默认 caution,不静默 accept"""
import pytest

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.biological_modules.registry import ModuleRegistry

reg = ModuleRegistry()

# (species, query, 期望 verdict)
_MISMATCH = [
    ("bacteria", "bacteria_autophagy", "caution"),
    ("bacteria", "mitochondria", "caution"),
    ("yeast", "tissue_spatial_niche", "reject"),
    ("yeast", "mammalian_cell_communication", "reject"),
]


@pytest.mark.parametrize("species,query,verdict", _MISMATCH,
                         ids=[f"{s}_{q}" for s, q, _ in _MISMATCH])
def test_biological_mismatch_verdict(species, query, verdict):
    assert reg.biological_mismatch(species, query) == verdict


def test_weak_modules_never_silently_accept():
    """所有 weak 模块默认裁决必须是 caution,不能是 accept(诚实:弱支持要带告警)。"""
    offenders = []
    for sp in ("human", "mouse", "yeast", "bacteria"):
        for mid in M.MODULE_ORDER:
            rec = reg.support(sp, mid)
            if rec["support"] == "weak" and reg.default_verdict(sp, mid) == "accept":
                offenders.append(f"{sp}/{mid}")
    assert offenders == [], f"弱支持模块被静默 accept: {offenders}"


def test_unsupported_modules_reject():
    """unsupported 模块默认 reject。"""
    for sp in ("human", "mouse", "yeast", "bacteria"):
        for mid in M.MODULE_ORDER:
            if reg.support(sp, mid)["support"] == "unsupported":
                assert reg.default_verdict(sp, mid) == "reject"


def test_bacteria_m3_not_called_mitochondria_in_display():
    """bacteria 的 M3 前端显示不得出现 'Mitochondrial'。"""
    name = reg.display_name("bacteria", "mitochondrial_energy_metabolism")
    assert "Mitochond" not in name
```

- [ ] **Step 2: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_species_module_guards.py -q`
Expected: 7 passed(4 mismatch + 3 守卫)。

- [ ] **Step 3: 提交**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/tests/test_species_module_guards.py
git commit -m "test(phase1): 物种特异生物学守卫(细菌不套自噬/线粒体,酵母不套组织 niche)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 1.5:全量回归 + 打包数据核对 + v0.9 里程碑

**Files:**
- Modify: `MANIFEST.in`(核对,可能无需改)
- Modify: `docs/ARCHITECTURE-v0.8-baseline.md`(补一行指向 v0.9 起点)

- [ ] **Step 1: 全量回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 315 passed / 25 skipped / 0 failed(287 Phase0 + 5 + 14 + 7 + 7 Phase1 = 315 左右;以实际为准,关键是 0 failed)。

- [ ] **Step 2: 核对 module_support.yaml 进 wheel**

新增的 yaml 在 `praxis_virtualcell/brains/virtualcell/*/`,现有 `MANIFEST.in` 已纳 `brains/**`(见 STATUS-2026-07-03 交付报告)。核对:

Run: `grep -n "brains" MANIFEST.in`
Expected: 有 `recursive-include praxis_virtualcell/brains *.yaml`(或等价)。若无,追加该行。

- [ ] **Step 3: 核对不破坏离线报告(基线特征化仍绿)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/baseline -q`
Expected: 全绿(Phase 1 未碰管线,基线不变)。

- [ ] **Step 4: 提交 + 打 v0.9 tag**

```bash
find . -name '._*' -delete
git add -A
git commit -m "chore(v0.9): Phase 1 完成 — 八模块 core + 4 物种支持矩阵 + registry(315 passed)

v0.9 PRAXIS-AIVC module core 里程碑:species profiles / eight modules /
module registry / 生物学错配守卫。管线未动,277 基线保持。

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git tag -a v0.9.0 -m "PRAXIS-AIVC module core: 八模块 + 物种支持矩阵 + registry"
```

**Phase 1 验收(对齐规格 §14 Phase 1):**
- ✅ 4 物种 × 8 模块 support matrix 可生成(`ModuleRegistry.matrix()`)。
- ✅ unsupported module 可 reject / caution(`default_verdict` + `biological_mismatch`)。
- ✅ 铁律钉死:bacteria 不套自噬/线粒体,yeast 不套组织 niche。
- ✅ 277 基线零回归(Phase 1 全新增、隔离,未碰管线)。
- ✅ 新增 ~40 测试(5+14+7+7 + 基线 10),277 → ~315,向 450+ 目标推进。

---

## Self-Review(写完对照规格)

- **规格覆盖**:Phase 0(§14 冻结)+ Phase 1(§14 八模块 + species profile + module_registry)全覆盖。§3.3 决策(profile 建在 brains 而非新目录)、§6-E(bacteria 术语/错配)、§8(主动学习结构)中 Phase 1 相关项已落。
- **偏离规格处(已注明理由)**:(1)Task 1.1 用数据驱动 `modules.py` 替代 §10 的 8 目录 40 文件(DRY + 不过度抽象);(2)species profile 落 `brains/virtualcell/*/module_support.yaml` 而非 `species_profiles/`(§3.3 避免双真相源);(3)SpeciesContextAgent 的 bus 接线延后到 Phase 3(Phase 1 不碰管线以零风险保基线)。
- **无占位符**:每步都有完整可跑代码 + 确切命令 + 期望输出。
- **类型一致**:`modules.MODULE_ORDER`/`MODULES`/`display_name` 在 registry 与测试中签名一致;`support()` 返回 dict、`default_verdict()` 返回 str、`biological_mismatch()` 返回 str|None,全程一致。

---

## 下一步(Phase 2 展开时机)

Phase 1 打完 v0.9 tag 后,回到主路线图 §9,把 **Phase 2(ModelBroker + model_zoo)** 展开成同样粒度的详细计划。Phase 2 的关键接口(ModelWrapper 补 `declare_scope()`/`estimate_uncertainty()`)依赖 Phase 1 的 `modules.py` engine 映射,届时对着真代码写。
