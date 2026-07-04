# Phase 2:ModelBroker + model_zoo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把"公开模型下载"和"自训模型注册"标准化成一套 **ModelBroker 治理框架**(`praxis_virtualcell/model_zoo/` 新子包 + `agents/model_broker_agent.py`),缺模型/缺依赖/sha 不匹配一律 **fail-closed**,绝不 silent accept。

**Architecture:** 全部**净新增 + 复用**,不改现有 predictor/管线/治理逻辑。`ModelZooRegistry` 照抄 `biological_modules/registry.py` 的 yaml+白名单校验模式;`ModelWrapper` 扩 `predictors/base.py:PredictorAgent`(已有 3 方法,补 `declare_scope()`/`estimate_uncertainty()` 两个显式方法);`GemWrapper` 把真实 `GemModel`(`predictors/mechanistic/gem_model.py`)包成 wrapper 证明契约在**真模型**上跑通;`cache.py` 做资产存在性 + sha256 版本锁;`downloader.py` 只做下载**契约**(本地资产指认;远端 GEARS/scGPT gated → `requires_manual_fetch`,Phase 2 不真下载);`ModelBrokerAgent` 扩 `core/agent.py:BaseAgent` 进 message bus。Phase 2 只交付 model_zoo 库 + broker agent,可**独立测试**;接进 runtime 管线留到 Phase 3。

**Tech Stack:** Python 3.13 / pytest 参数化 + `importorskip` gated / PyYAML(核心依赖)/ hashlib(标准库,sha256)。cobra/torch 为可选依赖,缺则 skip(不 fail),延续现有 GEM 测试 skip 惯例。

**铁律:**
- 只**新增**文件,不改 `core/` `agents/`(现有)`predictors/`(现有)`route_table` 任何逻辑;若发现现有行为与预期不符 → 真实 bug,停下报告,不改代码迁就测试。
- **缺模型 / 缺依赖(requires 不满足)/ sha 不匹配 → fail-closed,绝不 silent accept**(本 Phase 核心红线)。
- 测试口径 = `praxis_virtualcell/tests`(当前 **344 passed / 25 skipped / 0 failed**,已含 Phase 0+1);**不碰根 `tests/`**。`-q` 不打印精确汇总,用 `--junit-xml` 取精确数。
- cobra/torch/gpu gated 的测试用 `pytest.importorskip` skip(无依赖不 fail),延续现有 `test_ecoli_gem_case.py` 惯例。
- 每 task 全量 `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q` 绿后再 commit;commit 前删 `._*`;commit message 末尾加 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`;当前分支 `feat/v0.9-phase0-module-core`,**不 push、不 tag**。

**数据契约(已实跑核实,计划代码与之对齐):**
- `PredictorAgent`(`predictors/base.py:14`):`assess_applicability(request, brain_context)->(score, reason)`、`prepare_input(request, brain_context)->dict`、`run_prediction(model_input)->dict`(abstract,返回 `{prediction, uncertainty}`)、`handle(message, bus)`(fail-closed:rejected/failed/success 三态,retrieve-before-predict 门)。`name` 类属性。
- `GemModel`(`predictors/mechanistic/gem_model.py:23`)是**普通类不是 agent**:`__init__(sbml_path)` 读 SBML(`from cobra.io import read_sbml_model`)、`wt_growth`、`knockout(gene_id)->KOResult(gene,in_model,growth,ratio,essential)`、`knockout_many`。`EcoliGEM` 用 cobra 自带 textbook;`YeastGEM` 用 `data/gems/iMM904.xml.gz`(repo 根,`parents[3]/data/gems/`)。
- `ModuleRegistry`(`biological_modules/registry.py`)= yaml+校验模式样板:`__init__(brains_root=None)` 用 `RuntimeConfig().brains_root`;`_load`+`_cache`;`support`/`matrix`;未知 → 明确态而非静默。
- `biological_modules.modules`:`MODULE_ORDER`(8 项 list)、`MODULES`(dict)、`module(id)`(未知 raise KeyError)。module 白名单 = `MODULE_ORDER`。
- `BaseAgent`(`core/agent.py:10`):抽象 `handle(message, bus)->None`,只经 `bus.send` 产出,`name` 类属性。
- `MessageBus`(`core/bus.py`):`send`/`get_messages(agent_name)`/`trace`/`latest(type)`/`has_message_type(type)`。
- `AgentMessage`(`core/message.py:13`):`message_id/sender/receiver/message_type/payload/timestamp/parent_message_id`。
- `RuntimeConfig`(`core/config.py:40`):有 `brains_root` 字段;**无 `cache_root`**(cache 目录由 model_zoo 自管,不改 config)。
- `route_table.ENGINES` = `("donor_predictor","gem_fba","embedding","state_scoring","pathway_scoring","communication","spatial_niche","reject")`;`build_predictor_from_ckpt`(`predictors/ml/donor_bridge.py:37`)= json cfg + .pt bundle 重建(torch-gated,远端)。

**与骨架的一处校正(按真实代码调整):** 骨架说 `estimate_uncertainty` "默认从 run_prediction 的 uncertainty 提取"。核实 `PredictorAgent.run_prediction` 返回的 `uncertainty` **可能为 None**(见 `base.py:63` `uncertainty=out.get("uncertainty")`),故 `estimate_uncertainty` 默认实现必须**优雅处理 None**(返回 `{"available": False, ...}` 而非崩溃)。已在 Task 2.2 代码落实。

---

# Phase 2:model_zoo 库 + ModelBrokerAgent

## Task 2.1:model_zoo 注册表 `registry.yaml` + `ModelZooRegistry`

**决策说明:** `ModelZooRegistry` 直接照抄 `biological_modules/registry.py` 的 yaml+校验模式(`_load`/`_cache`/白名单),不进 message bus(broker 的 bus 接线在 Task 2.6)。种子只放 2-3 条(ecoli_gem available / gears planned+requires[torch,gpu] / yeast_deletion_fitness self_trained+planned),证明 schema + 查询 + 校验闭环即可,大规模填表留到 Phase 6/7。

**Files:**
- Create: `praxis_virtualcell/model_zoo/__init__.py`
- Create: `praxis_virtualcell/model_zoo/registry.yaml`
- Create: `praxis_virtualcell/model_zoo/registry.py`
- Test: `praxis_virtualcell/tests/test_model_zoo_registry.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_model_zoo_registry.py`:

```python
"""Phase 2:ModelZooRegistry —— 声明式模型注册表 schema + 查询 + 白名单校验。
铁律:module 必须 ∈ MODULE_ORDER;status 合法枚举;未知 name → KeyError(不静默返 None)。"""
import pytest

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.model_zoo.registry import (
    LEGAL_STATUS,
    LEGAL_TYPES,
    ModelZooRegistry,
)


@pytest.fixture(scope="module")
def reg():
    return ModelZooRegistry()  # 默认读 model_zoo/registry.yaml


def test_seed_entries_present(reg):
    names = set(reg.names())
    # 至少三条种子:一条 available 真模型、一条 planned 公开模型、一条 self_trained
    assert {"ecoli_gem", "gears", "yeast_deletion_fitness"} <= names


def test_every_entry_schema_is_legal(reg):
    for name in reg.names():
        e = reg.get(name)
        assert e["name"] == name
        assert e["type"] in LEGAL_TYPES, f"{name} 非法 type: {e['type']}"
        assert e["status"] in LEGAL_STATUS, f"{name} 非法 status: {e['status']}"
        assert e["module"] in M.MODULE_ORDER, f"{name} module 越白名单: {e['module']}"
        assert isinstance(e.get("requires", []), list)
        assert e.get("species"), f"{name} 缺 species"
        assert e.get("wrapper"), f"{name} 缺 wrapper 类路径"


def test_query_by_module_and_species(reg):
    ecoli = reg.by_module("cytoplasmic_metabolism")
    assert "ecoli_gem" in {e["name"] for e in ecoli}
    bact = reg.by_species("bacteria")
    assert "ecoli_gem" in {e["name"] for e in bact}


def test_status_helpers(reg):
    assert reg.status("ecoli_gem") == "available"
    assert reg.status("gears") == "planned"
    assert reg.is_available("ecoli_gem") is True
    assert reg.is_available("gears") is False


def test_unknown_name_raises_keyerror(reg):
    with pytest.raises(KeyError):
        reg.get("no_such_model")
    with pytest.raises(KeyError):
        reg.status("no_such_model")


def test_illegal_module_in_yaml_is_rejected(tmp_path):
    """注册表加载时校验 module ∈ MODULE_ORDER;非法 module → ValueError(fail-closed)。"""
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "models:\n"
        "  broken:\n"
        "    name: broken\n"
        "    type: public_model\n"
        "    species: [human]\n"
        "    module: not_a_real_module\n"
        "    task: growth\n"
        "    source: local\n"
        "    license: MIT\n"
        "    status: available\n"
        "    wrapper: x.Y\n"
        "    version: '1'\n"
        "    requires: []\n"
        "    reliability_policy: gem_growth\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        ModelZooRegistry(registry_path=str(bad))
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_model_zoo_registry.py -q`
Expected: FAIL(ModuleNotFoundError: praxis_virtualcell.model_zoo)。

- [ ] **Step 3: 写 `__init__.py`**

写 `praxis_virtualcell/model_zoo/__init__.py`:

```python
"""model_zoo:ModelBroker 治理框架 —— 声明式注册表 + wrapper 契约 + 缓存/版本锁 + 下载契约。

设计:公开模型下载与自训模型注册标准化。缺模型/缺依赖/sha 不匹配一律 fail-closed,
绝不 silent accept。Phase 2 只交付库 + ModelBrokerAgent,可独立测试;接进 runtime 管线在 Phase 3。
"""
```

- [ ] **Step 4: 写 `registry.yaml` 种子**

写 `praxis_virtualcell/model_zoo/registry.yaml`:

```yaml
# 声明式模型注册表(model zoo)。每条模型字段:
#   name / type(public_model|self_trained) / species(list) / module(∈ MODULE_ORDER) /
#   task / source / license / status(available|planned|missing) / wrapper(类路径) /
#   version / requires(list,如 cobra/torch/gpu) / reliability_policy /
#   training_card(仅 self_trained 必填,见 Task 2.7)
# 铁律:module 必须 ∈ biological_modules.MODULE_ORDER;缺资产/缺依赖 → 由 broker fail-closed。
models:
  ecoli_gem:
    name: ecoli_gem
    type: public_model
    species: [bacteria]
    module: cytoplasmic_metabolism
    task: growth
    source: cobra_bundled_textbook          # cobra 自带 e_coli_core,无需下载
    license: cobrapy-bundled
    status: available
    wrapper: praxis_virtualcell.model_zoo.wrappers.gem_wrapper.GemWrapper
    version: e_coli_core-textbook
    requires: [cobra]
    reliability_policy: gem_growth_disposition

  gears:
    name: gears
    type: public_model
    species: [human]
    module: genetic_hub
    task: perturbation_response
    source: "remote:gears_ckpt"             # 远端权重,Phase 2 不真下载(Phase 6 接入)
    license: MIT
    status: planned
    wrapper: praxis_virtualcell.model_zoo.wrappers.gears_wrapper.GearsWrapper  # Phase 6 才实现
    version: norman_2019
    requires: [torch, gpu]
    reliability_policy: ml_disagreement

  yeast_deletion_fitness:
    name: yeast_deletion_fitness
    type: self_trained
    species: [yeast]
    module: genetic_hub
    task: deletion_fitness
    source: "self_trained:yeast_deletion_fitness"
    license: internal
    status: planned
    wrapper: praxis_virtualcell.model_zoo.wrappers.self_trained_wrapper.SelfTrainedWrapper  # 未来
    version: v0-planned
    requires: [torch]
    reliability_policy: ml_disagreement
    training_card:                           # self_trained 必填(Task 2.7 校验)
      training_data: SGD deletion library growth screens (planned)
      split: by-gene holdout (planned)
      baseline: mean-fitness predictor
      metrics: {pearson: null, note: "planned, not yet trained"}
      provenance: "planned; no weights yet — status=planned gates broker fail-closed"
```

- [ ] **Step 5: 写 `registry.py`**

写 `praxis_virtualcell/model_zoo/registry.py`:

```python
"""model zoo 注册表:读 model_zoo/registry.yaml,提供 schema 校验 + name/module/species 查询 + status。
照抄 biological_modules/registry.py 的 yaml+白名单校验模式。纯库(不进 message bus;broker 在 Task 2.6)。
"""
from __future__ import annotations

from pathlib import Path

import yaml

from praxis_virtualcell.biological_modules import modules as M

LEGAL_TYPES = ("public_model", "self_trained")
LEGAL_STATUS = ("available", "planned", "missing")

_REQUIRED_FIELDS = ("name", "type", "species", "module", "task", "source",
                    "license", "status", "wrapper", "version")

_DEFAULT_REGISTRY = Path(__file__).parent / "registry.yaml"


class ModelZooRegistry:
    def __init__(self, registry_path: str | None = None) -> None:
        self.path = Path(registry_path or _DEFAULT_REGISTRY)
        self._models: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        doc = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        models = doc.get("models") or {}
        for name, entry in models.items():
            self._validate(name, entry)
            self._models[name] = entry

    @staticmethod
    def _validate(name: str, entry: dict) -> None:
        """schema 校验(fail-closed:任何非法字段 → ValueError,不静默接受坏条目)。"""
        for f in _REQUIRED_FIELDS:
            if f not in entry:
                raise ValueError(f"model_zoo 条目 {name} 缺必填字段: {f}")
        if entry["name"] != name:
            raise ValueError(f"model_zoo 条目 key({name})与 name({entry['name']})不一致")
        if entry["type"] not in LEGAL_TYPES:
            raise ValueError(f"{name} 非法 type: {entry['type']}(合法: {LEGAL_TYPES})")
        if entry["status"] not in LEGAL_STATUS:
            raise ValueError(f"{name} 非法 status: {entry['status']}(合法: {LEGAL_STATUS})")
        if entry["module"] not in M.MODULE_ORDER:
            raise ValueError(f"{name} module 越白名单: {entry['module']}(须 ∈ MODULE_ORDER)")
        if not isinstance(entry["species"], list) or not entry["species"]:
            raise ValueError(f"{name} species 必须是非空 list")
        if not isinstance(entry.get("requires", []), list):
            raise ValueError(f"{name} requires 必须是 list")

    # ---- 查询 ----
    def names(self) -> list[str]:
        return list(self._models)

    def get(self, name: str) -> dict:
        if name not in self._models:
            raise KeyError(f"未知模型: {name}(已注册: {sorted(self._models)})")
        return self._models[name]

    def status(self, name: str) -> str:
        return self.get(name)["status"]

    def is_available(self, name: str) -> bool:
        return self.get(name)["status"] == "available"

    def by_module(self, module_id: str) -> list[dict]:
        if module_id not in M.MODULES:
            raise KeyError(f"未知模块: {module_id}")
        return [e for e in self._models.values() if e["module"] == module_id]

    def by_species(self, species: str) -> list[dict]:
        return [e for e in self._models.values() if species in e["species"]]
```

- [ ] **Step 6: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_model_zoo_registry.py -q`
Expected: 6 passed。

- [ ] **Step 7: 全量回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 350 passed / 25 skipped / 0 failed(344 + 6 新)。关键是 0 failed。

- [ ] **Step 8: 提交**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/model_zoo/__init__.py praxis_virtualcell/model_zoo/registry.yaml praxis_virtualcell/model_zoo/registry.py praxis_virtualcell/tests/test_model_zoo_registry.py
git commit -m "feat(phase2): ModelZooRegistry + registry.yaml(声明式模型注册表 + module 白名单校验 + 3 种子)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 2.2:ModelWrapper 契约 `wrappers/base.py`(扩 PredictorAgent,补 2 方法)

**决策说明:** `ModelWrapper` extends `predictors/base.py:PredictorAgent`,保留其 fail-closed(rejected/failed/success 三态 + retrieve-before-predict 门),**只补两个显式方法**:`declare_scope()->dict`(声明 species/module/task/perturbation 边界,供治理读)、`estimate_uncertainty(model_input, prediction)->dict`(显式不确定性;默认从 `run_prediction` 的 uncertainty 提取,**优雅处理 None**)。骨架校正:因 `PredictorAgent.run_prediction` 的 uncertainty 可能为 None,默认 `estimate_uncertainty` 返回 `{"available": bool, ...}` 而非崩溃。超出 scope 的输入 → 由 `handle` 走 rejected(不硬预测)。

**Files:**
- Create: `praxis_virtualcell/model_zoo/wrappers/__init__.py`
- Create: `praxis_virtualcell/model_zoo/wrappers/base.py`
- Test: `praxis_virtualcell/tests/test_model_wrapper_base.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_model_wrapper_base.py`:

```python
"""Phase 2:ModelWrapper 契约。测 declare_scope 结构、estimate_uncertainty 契约(含 None 优雅降级)、
超出 scope 的输入 → rejected(不硬预测)。用一个最小 DummyWrapper 具化 abstract。"""
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper


class _DummyWrapper(ModelWrapper):
    """最小具化:scope=human/genetic_hub/expression;run_prediction 回定值。"""
    name = "DummyWrapper"

    def declare_scope(self) -> dict:
        return {
            "species": ["human"],
            "module": "genetic_hub",
            "task": ["expression"],
            "perturbation": ["gene"],
        }

    def run_prediction(self, model_input: dict) -> dict:
        return {"prediction": {"delta": 0.5}, "uncertainty": {"std": 0.1}}


class _NoUncertaintyWrapper(_DummyWrapper):
    name = "NoUncWrapper"

    def run_prediction(self, model_input: dict) -> dict:
        return {"prediction": {"delta": 0.2}}  # 无 uncertainty


def _bus_with_brain():
    bus = MessageBus()
    bus.record_trace(AgentMessage(
        message_id="m0", sender="SpeciesBrain", receiver="X",
        message_type="brain_retrieved", payload={}, timestamp="t0"))
    return bus


def _brain_ctx():
    # 让 assess_applicability 放行 human/gene/expression
    return {
        "species": "human",
        "model_applicability": {
            "DummyWrapper": {
                "supported_species": ["human"],
                "supported_modalities": ["scRNA"],
                "supported_tasks": ["expression"],
            }
        },
        "rules_referenced": ["r1"],
    }


def _request(**over):
    base = {
        "species": "human", "input_modality": "scRNA", "task_type": "expression",
        "perturbation_type": "gene", "perturbation_targets": ["AHR"],
    }
    base.update(over)
    return base


def test_declare_scope_structure():
    scope = _DummyWrapper().declare_scope()
    assert set(scope) >= {"species", "module", "task"}
    assert scope["module"] == "genetic_hub"
    assert "human" in scope["species"]


def test_estimate_uncertainty_from_prediction():
    w = _DummyWrapper()
    out = w.run_prediction({})
    unc = w.estimate_uncertainty({}, out["prediction"])
    assert unc["available"] is True
    assert unc["uncertainty"] == {"std": 0.1} or "std" in unc.get("uncertainty", {})


def test_estimate_uncertainty_handles_missing_gracefully():
    """铁律:run_prediction 无 uncertainty → 不崩溃,available=False(诚实:说没有,不假造)。"""
    w = _NoUncertaintyWrapper()
    out = w.run_prediction({})
    unc = w.estimate_uncertainty({}, out.get("prediction"))
    assert unc["available"] is False


def test_in_scope_request_succeeds():
    w = _DummyWrapper()
    bus = _bus_with_brain()
    w.handle(AgentMessage(
        message_id="m1", sender="X", receiver="DummyWrapper", message_type="predict",
        payload={"request": _request(), "brain_context": _brain_ctx()}, timestamp="t1"), bus)
    res = bus.latest("predictor_result")
    assert res.payload["status"] == "success"


def test_out_of_scope_request_is_rejected_not_hard_predicted():
    """超出 scope(mouse)→ rejected,不硬预测(fail-closed)。"""
    w = _DummyWrapper()
    bus = _bus_with_brain()
    ctx = _brain_ctx()  # applicability 仍只列 human
    w.handle(AgentMessage(
        message_id="m2", sender="X", receiver="DummyWrapper", message_type="predict",
        payload={"request": _request(species="mouse"), "brain_context": ctx}, timestamp="t2"), bus)
    res = bus.latest("predictor_result")
    assert res.payload["status"] == "rejected"
    assert res.payload["prediction"] is None
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_model_wrapper_base.py -q`
Expected: FAIL(ModuleNotFoundError: praxis_virtualcell.model_zoo.wrappers.base)。

- [ ] **Step 3: 写 `wrappers/__init__.py`**

写 `praxis_virtualcell/model_zoo/wrappers/__init__.py`:

```python
"""model_zoo wrapper 层:ModelWrapper(扩 PredictorAgent + declare_scope/estimate_uncertainty)。"""
```

- [ ] **Step 4: 写 `wrappers/base.py`**

写 `praxis_virtualcell/model_zoo/wrappers/base.py`:

```python
"""ModelWrapper:model zoo 的统一模型契约。extends PredictorAgent(保留 fail-closed +
retrieve-before-predict 门),补两个显式治理方法:

- declare_scope() -> dict:声明该模型适用的 species/module/task/perturbation 边界,供治理读。
- estimate_uncertainty(model_input, prediction) -> dict:显式不确定性。默认从 run_prediction 的
  uncertainty 提取;若无(run_prediction 未产 uncertainty)→ available=False(诚实,不假造)。

超出 scope 的输入由继承的 assess_applicability/handle 走 rejected,不硬预测。
"""
from __future__ import annotations

from abc import abstractmethod

from praxis_virtualcell.predictors.base import PredictorAgent


class ModelWrapper(PredictorAgent):
    name = "ModelWrapper"

    @abstractmethod
    def declare_scope(self) -> dict:
        """返回 {species: list, module: str, task: list, perturbation?: list}。治理据此判 in/out of scope。"""

    def estimate_uncertainty(self, model_input: dict, prediction: dict | None) -> dict:
        """默认:调 run_prediction 取 uncertainty(可能为 None → available=False,不假造)。
        子类可覆写为更显式的估计(如 bootstrap CI / ensemble disagreement)。"""
        try:
            out = self.run_prediction(model_input)
        except Exception as e:  # noqa: BLE001 — 不确定性估计失败视为不可用,fail-closed
            return {"available": False, "reason": f"uncertainty_estimation_failed: {e}"}
        unc = out.get("uncertainty")
        if unc is None:
            return {"available": False, "reason": "model_reports_no_uncertainty"}
        return {"available": True, "uncertainty": unc}
```

- [ ] **Step 5: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_model_wrapper_base.py -q`
Expected: 5 passed。

- [ ] **Step 6: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 355 passed / 25 skipped / 0 failed(350 + 5 新)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/model_zoo/wrappers/__init__.py praxis_virtualcell/model_zoo/wrappers/base.py praxis_virtualcell/tests/test_model_wrapper_base.py
git commit -m "feat(phase2): ModelWrapper 契约(扩 PredictorAgent + declare_scope/estimate_uncertainty,uncertainty 缺失优雅降级)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 2.3:GemWrapper `wrappers/gem_wrapper.py`(真模型证明契约)

**决策说明:** 把真实 `GemModel`(`predictors/mechanistic/gem_model.py`,非 agent)包成 `ModelWrapper`,证明契约在**真模型**上跑通。`GemModel` 是普通类,`GemWrapper.run_prediction` 内部 lazy 载 cobra + SBML 并调 `knockout_many`;缺 cobra 或 SBML → fail-closed(`run_prediction` 抛异常 → 继承的 `handle` 归为 `failed`;或 scope 不符 → `rejected`)。`declare_scope` = {species: bacteria/yeast, module: cytoplasmic_metabolism, task: growth}。基因不在 GEM → `in_model=False`,`run_prediction` 如实标注,不虚构生长。

**Files:**
- Create: `praxis_virtualcell/model_zoo/wrappers/gem_wrapper.py`
- Test: `praxis_virtualcell/tests/test_gem_wrapper.py`

- [ ] **Step 1: 写失败测试(cobra-gated)**

写 `praxis_virtualcell/tests/test_gem_wrapper.py`:

```python
"""Phase 2:GemWrapper —— 真实 GemModel 包成 ModelWrapper,证明契约在真模型上跑通。
cobra-gated(无 cobra → 整文件 skip,延续 test_ecoli_gem_case 惯例)。
断言:declare_scope 正确;真跑 KO(b0720 essential);基因不在 GEM → 不虚构(in_model=False)。"""
import pytest

cobra = pytest.importorskip("cobra")   # 无 cobra → skip

from praxis_virtualcell.model_zoo.wrappers.gem_wrapper import GemWrapper  # noqa: E402


@pytest.fixture(scope="module")
def wrapper():
    return GemWrapper()  # 默认 e_coli_core textbook(cobra 自带,无需外部数据)


def test_declare_scope_growth_bacteria_yeast(wrapper):
    scope = wrapper.declare_scope()
    assert scope["module"] == "cytoplasmic_metabolism"
    assert "bacteria" in scope["species"]
    assert "growth" in scope["task"]


def test_run_prediction_real_ko_essential(wrapper):
    # b0720 (gltA) 在 e_coli_core 中 essential → growth≈0
    out = wrapper.run_prediction({"targets": ["b0720"]})
    kos = {k["gene"]: k for k in out["prediction"]["knockouts"]}
    assert kos["b0720"]["in_model"] is True
    assert kos["b0720"]["essential"] is True


def test_gene_not_in_gem_not_fabricated(wrapper):
    # 基因不在 GEM → in_model=False,growth=None(不虚构生长)
    out = wrapper.run_prediction({"targets": ["ZZZ_notagene"]})
    ko = out["prediction"]["knockouts"][0]
    assert ko["in_model"] is False
    assert ko["growth"] is None


def test_uncertainty_contract(wrapper):
    out = wrapper.run_prediction({"targets": ["b0720"]})
    unc = wrapper.estimate_uncertainty({"targets": ["b0720"]}, out["prediction"])
    # GEM 是确定性 FBA:声明 method=deterministic_fba,available 明确(不假造随机 CI)
    assert "available" in unc
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_gem_wrapper.py -q`
Expected: FAIL(ModuleNotFoundError: ...gem_wrapper)——若本机无 cobra 则整文件 skip(此时视为"红"未达成,须在有 cobra 的环境跑;本仓 `.venv` 已装 cobra,应真 FAIL)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/model_zoo/wrappers/gem_wrapper.py`:

```python
"""GemWrapper:把真实 GemModel(predictors/mechanistic/gem_model.py)包成 ModelWrapper。

证明 model_zoo 契约在**真机制模型**上跑通。默认 e_coli_core(cobra 自带 textbook,无外部数据)。
缺 cobra → 构造时抛(继承 handle 归 failed);缺 SBML → GemModel 构造抛。基因不在 GEM →
knockout 返 in_model=False(不虚构生长)。GEM 是确定性 FBA,estimate_uncertainty 声明 deterministic。
"""
from __future__ import annotations

from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper


class GemWrapper(ModelWrapper):
    name = "GemWrapper"

    def __init__(self, sbml_path: str | None = None) -> None:
        # lazy:仅在实例化时载模型;缺 cobra/SBML → 抛 → 上层 fail-closed
        from praxis_virtualcell.predictors.mechanistic.ecoli_gem import EcoliGEM
        from praxis_virtualcell.predictors.mechanistic.gem_model import GemModel

        self._gem = GemModel(sbml_path) if sbml_path else EcoliGEM()

    def declare_scope(self) -> dict:
        return {
            "species": ["bacteria", "yeast"],   # GEM 覆盖微生物 KO growth
            "module": "cytoplasmic_metabolism", # M4(与 registry.yaml ecoli_gem.module 一致)
            "task": ["growth"],
            "perturbation": ["gene"],
        }

    def run_prediction(self, model_input: dict) -> dict:
        """真跑 cobra FBA KO。返回 {prediction: {wt_growth, knockouts:[...]}, uncertainty}。
        基因不在 GEM → in_model=False, growth=None(不虚构)。"""
        targets = model_input.get("targets", [])
        kos = self._gem.knockout_many(targets)
        return {
            "prediction": {
                "wt_growth": round(self._gem.wt_growth, 5),
                "knockouts": [
                    {"gene": k.gene, "in_model": k.in_model,
                     "growth": None if k.growth is None else round(k.growth, 5),
                     "ratio": None if k.ratio is None else round(k.ratio, 4),
                     "essential": k.essential}
                    for k in kos
                ],
            },
            # GEM 是确定性约束型模型:不产随机 uncertainty,如实声明 deterministic
            "uncertainty": {"method": "deterministic_fba"},
        }

    def estimate_uncertainty(self, model_input: dict, prediction: dict | None) -> dict:
        """GEM 确定性:available=True 但 method=deterministic_fba(诚实:非概率不确定性)。"""
        return {"available": True, "method": "deterministic_fba",
                "note": "constraint-based FBA is deterministic; essentiality needs wet-lab confirmation"}
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_gem_wrapper.py -q`
Expected: 4 passed(有 cobra);无 cobra 环境 → 4 skipped。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 359 passed / 25 skipped / 0 failed(355 + 4 新,cobra 已装)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/model_zoo/wrappers/gem_wrapper.py praxis_virtualcell/tests/test_gem_wrapper.py
git commit -m "feat(phase2): GemWrapper(真实 GemModel 包成 ModelWrapper;真跑 KO;基因不在 GEM 不虚构)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 2.4:本地缓存 + 版本锁 `cache.py`

**决策说明:** `cache.py` 管缓存目录(默认 `~/.cache/praxis_virtualcell/model_zoo/`,可 override,测试用 tmp_path)+ 资产存在性检查 + **版本锁(sha256 校验)**。资产缺失或 sha 不匹配 → 返回 `AssetStatus(available=False, reason=...)`(fail-closed),**绝不 silent accept**。不改 `RuntimeConfig`(config 无 cache_root,cache 目录由本模块自管)。

**Files:**
- Create: `praxis_virtualcell/model_zoo/cache.py`
- Test: `praxis_virtualcell/tests/test_model_zoo_cache.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_model_zoo_cache.py`:

```python
"""Phase 2:model zoo 本地缓存 + 版本锁(sha256)。铁律:资产缺失/sha 不匹配 → unavailable(fail-closed),
绝不 silent accept。测:命中 / 未命中 / sha 不匹配 / 版本锁行为。"""
import hashlib

from praxis_virtualcell.model_zoo.cache import ModelCache


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_missing_asset_is_unavailable(tmp_path):
    cache = ModelCache(root=str(tmp_path))
    st = cache.check("gears", "weights.pt")
    assert st.available is False
    assert "not_found" in st.reason or "missing" in st.reason


def test_present_asset_without_lock_is_available(tmp_path):
    cache = ModelCache(root=str(tmp_path))
    p = cache.asset_path("ecoli_gem", "model.xml")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"SBML")
    st = cache.check("ecoli_gem", "model.xml")            # 无 sha 锁 → 存在即可用
    assert st.available is True


def test_sha256_lock_match_is_available(tmp_path):
    cache = ModelCache(root=str(tmp_path))
    p = cache.asset_path("m", "w.bin")
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = b"hello-weights"
    p.write_bytes(payload)
    st = cache.check("m", "w.bin", sha256=_sha256(payload))
    assert st.available is True


def test_sha256_mismatch_is_unavailable(tmp_path):
    """铁律:sha 不匹配 → unavailable(可能被篡改/版本错),绝不 silent accept。"""
    cache = ModelCache(root=str(tmp_path))
    p = cache.asset_path("m", "w.bin")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"actual-bytes")
    st = cache.check("m", "w.bin", sha256=_sha256(b"expected-different"))
    assert st.available is False
    assert "sha256_mismatch" in st.reason


def test_asset_path_is_namespaced_by_model(tmp_path):
    cache = ModelCache(root=str(tmp_path))
    pa = cache.asset_path("model_a", "f.pt")
    pb = cache.asset_path("model_b", "f.pt")
    assert pa != pb
    assert "model_a" in str(pa) and "model_b" in str(pb)
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_model_zoo_cache.py -q`
Expected: FAIL(ModuleNotFoundError: ...cache)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/model_zoo/cache.py`:

```python
"""model zoo 本地缓存 + 版本锁(sha256)。

缓存目录:默认 ~/.cache/praxis_virtualcell/model_zoo/<model_name>/<asset>,root 可 override。
check():资产存在性 + 可选 sha256 版本锁。缺失或 sha 不匹配 → AssetStatus(available=False),
fail-closed,绝不 silent accept(篡改/版本错的权重宁可判不可用)。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_ROOT = Path.home() / ".cache" / "praxis_virtualcell" / "model_zoo"


@dataclass
class AssetStatus:
    available: bool
    path: str | None
    reason: str


class ModelCache:
    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or _DEFAULT_ROOT)

    def asset_path(self, model_name: str, asset: str) -> Path:
        """命名空间化路径:<root>/<model_name>/<asset>(不同模型互不覆盖)。"""
        return self.root / model_name / asset

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def check(self, model_name: str, asset: str, *, sha256: str | None = None) -> AssetStatus:
        """资产存在性 + 可选 sha256 锁。缺失/不匹配 → available=False(fail-closed)。"""
        p = self.asset_path(model_name, asset)
        if not p.is_file():
            return AssetStatus(False, None, f"asset_not_found: {p}")
        if sha256 is not None:
            actual = self._sha256(p)
            if actual != sha256:
                return AssetStatus(False, None,
                                   f"sha256_mismatch: expected {sha256[:12]}… got {actual[:12]}…")
        return AssetStatus(True, str(p), "ok")
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_model_zoo_cache.py -q`
Expected: 5 passed。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 364 passed / 25 skipped / 0 failed(359 + 5 新)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/model_zoo/cache.py praxis_virtualcell/tests/test_model_zoo_cache.py
git commit -m "feat(phase2): ModelCache 本地缓存 + sha256 版本锁(缺失/不匹配 → unavailable fail-closed)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 2.5:下载契约 `downloader.py`(远端 gated)

**决策说明:** 给一条 registry 条目 → 解析 `source` → 目标缓存路径。**Phase 2 不真下载大模型**:`source` 以 `cobra_bundled_*` / `local:` 开头的(本地已有,如 cobra textbook / `data/gems/*.xml.gz`)→ 直接指认为 `resolved`;以 `remote:` 开头(GEARS/scGPT ckpt,requires[torch,gpu])→ 返回 `requires_manual_fetch`/fail-closed 状态,**不假装下载成功**;缺 `source` 字段 → ValueError。

**Files:**
- Create: `praxis_virtualcell/model_zoo/downloader.py`
- Test: `praxis_virtualcell/tests/test_model_zoo_downloader.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_model_zoo_downloader.py`:

```python
"""Phase 2:下载契约(远端 gated)。铁律:Phase 2 不真下载大模型。
- 本地资产(cobra_bundled_* / local:)→ resolved(直接指认)
- 远端(remote:...)→ requires_manual_fetch(不假装下载成功,不静默)
- 缺 source → ValueError"""
import pytest

from praxis_virtualcell.model_zoo.downloader import resolve_source


def test_cobra_bundled_source_is_resolved():
    r = resolve_source({"name": "ecoli_gem", "source": "cobra_bundled_textbook", "requires": ["cobra"]})
    assert r["status"] == "resolved"
    assert r["fetch"] == "none"           # 本地自带,无需下载


def test_local_data_source_is_resolved():
    r = resolve_source({"name": "yeast_gem", "source": "local:data/gems/iMM904.xml.gz",
                        "requires": ["cobra"]})
    assert r["status"] == "resolved"
    assert "data/gems/iMM904.xml.gz" in r["path"]


def test_remote_source_is_gated_not_silently_ok():
    """铁律:远端权重 → requires_manual_fetch,绝不假装下载成功。"""
    r = resolve_source({"name": "gears", "source": "remote:gears_ckpt", "requires": ["torch", "gpu"]})
    assert r["status"] == "requires_manual_fetch"
    assert r["available"] is False
    assert "torch" in r["reason"] or "manual" in r["reason"] or "remote" in r["reason"]


def test_missing_source_raises():
    with pytest.raises(ValueError):
        resolve_source({"name": "broken", "requires": []})
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_model_zoo_downloader.py -q`
Expected: FAIL(ModuleNotFoundError: ...downloader)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/model_zoo/downloader.py`:

```python
"""下载契约(远端 gated)。给一条 registry 条目 → 解析 source → 目标/指认。

Phase 2 不真下载大模型:
- cobra_bundled_* / local:<relpath> → 本地已有 → status=resolved(fetch=none),直接指认路径。
- remote:<id> → 远端 ckpt(GEARS/scGPT,requires torch/gpu)→ status=requires_manual_fetch,
  available=False,fail-closed(不假装下载成功;真接入是 Phase 6)。
- 缺 source → ValueError(坏条目,不静默)。
"""
from __future__ import annotations

from pathlib import Path

# repo 根:此文件在 praxis_virtualcell/model_zoo/downloader.py → parents[2] = repo 根
_REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_source(entry: dict) -> dict:
    """返回 {status, available, ...}。status ∈ resolved | requires_manual_fetch。"""
    source = entry.get("source")
    if not source:
        raise ValueError(f"model_zoo 条目 {entry.get('name')} 缺 source 字段")

    if source.startswith("cobra_bundled"):
        # cobra 自带,由 wrapper 内部经 cobra 加载,无需下载
        return {"status": "resolved", "available": True, "fetch": "none",
                "path": None, "reason": "cobra-bundled asset, loaded via cobra"}

    if source.startswith("local:"):
        rel = source.split("local:", 1)[1]
        p = (_REPO_ROOT / rel)
        if not p.is_file():
            return {"status": "requires_manual_fetch", "available": False, "fetch": "manual",
                    "path": str(p), "reason": f"declared local asset missing: {rel}"}
        return {"status": "resolved", "available": True, "fetch": "none",
                "path": str(p), "reason": "local repo asset"}

    if source.startswith("remote:") or source.startswith("self_trained:"):
        # Phase 2 不真下载:远端权重/自训权重需人工获取(Phase 6/7 产品化)
        req = entry.get("requires", [])
        return {"status": "requires_manual_fetch", "available": False, "fetch": "manual",
                "path": None,
                "reason": f"remote/self-trained weights require manual fetch (requires={req}); "
                          "Phase 2 does not download large models"}

    raise ValueError(f"model_zoo 条目 {entry.get('name')} 无法识别 source scheme: {source}")
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_model_zoo_downloader.py -q`
Expected: 4 passed。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 368 passed / 25 skipped / 0 failed(364 + 4 新)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/model_zoo/downloader.py praxis_virtualcell/tests/test_model_zoo_downloader.py
git commit -m "feat(phase2): downloader 下载契约(本地资产指认;远端 GEARS/scGPT gated → requires_manual_fetch 不静默)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 2.6:ModelBrokerAgent `agents/model_broker_agent.py`(进 message bus)

**决策说明:** `ModelBrokerAgent` extends `core/agent.py:BaseAgent`,进 message bus。收模型请求(payload `{model_name}` 或 `{module, species}`)→ 查 `ModelZooRegistry` + `ModelCache`/`resolve_source` → 经 `bus.send` 产出一条 `model_broker_result` 消息,payload `{available, wrapper, status, reason}`。`available` 模型返回 wrapper 类路径;`planned`/`missing`/`requires` 不满足 → fail-closed(`available=False` + reason,**不 silent accept**)。requires 依赖检查用 `importlib.util.find_spec`(torch/cobra;gpu 无法静态检 → 按 requires 声明降级为 unavailable,诚实标注 gpu 需运行时确认)。放在**新** `agents/model_broker_agent.py`(与现有 agents 同目录但纯新增,不改现有)。

**Files:**
- Create: `praxis_virtualcell/agents/model_broker_agent.py`
- Test: `praxis_virtualcell/tests/test_model_broker_agent.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_model_broker_agent.py`:

```python
"""Phase 2:ModelBrokerAgent —— 进 message bus,查 registry + cache/source → available/fail-closed。
铁律:available 模型返回 wrapper;planned/missing/requires 不满足 → fail-closed(不 silent accept)。
测:bus 消息结构、available、planned→降级、缺依赖→明确降级。"""
from praxis_virtualcell.agents.model_broker_agent import ModelBrokerAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _ask(model_name):
    return AgentMessage(
        message_id="q1", sender="Client", receiver="ModelBrokerAgent",
        message_type="model_request", payload={"model_name": model_name}, timestamp="t1")


def test_available_model_returns_wrapper():
    """ecoli_gem status=available 且 cobra 已装 → available=True + wrapper 类路径。"""
    bus = MessageBus()
    ModelBrokerAgent().handle(_ask("ecoli_gem"), bus)
    res = bus.latest("model_broker_result")
    assert res is not None
    p = res.payload
    assert p["model_name"] == "ecoli_gem"
    assert p["available"] is True
    assert p["wrapper"] == "praxis_virtualcell.model_zoo.wrappers.gem_wrapper.GemWrapper"


def test_planned_model_is_fail_closed():
    """gears status=planned → available=False(不 silent accept),带 reason。"""
    bus = MessageBus()
    ModelBrokerAgent().handle(_ask("gears"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert p["status"] == "planned"
    assert p["reason"]


def test_unknown_model_is_fail_closed():
    bus = MessageBus()
    ModelBrokerAgent().handle(_ask("no_such_model"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert "unknown" in p["reason"] or "未知" in p["reason"]


def test_bus_message_structure():
    bus = MessageBus()
    ModelBrokerAgent().handle(_ask("ecoli_gem"), bus)
    res = bus.latest("model_broker_result")
    assert res.sender == "ModelBrokerAgent"
    assert res.message_type == "model_broker_result"
    assert set(res.payload) >= {"model_name", "available", "status", "wrapper", "reason"}


def test_missing_dependency_degrades_explicitly(monkeypatch):
    """requires 依赖缺失(模拟 cobra 不可用)→ available=False + reason 点名缺的依赖(不 silent accept)。"""
    import praxis_virtualcell.agents.model_broker_agent as mba

    monkeypatch.setattr(mba, "_dep_available", lambda dep: dep != "cobra")
    bus = MessageBus()
    mba.ModelBrokerAgent().handle(_ask("ecoli_gem"), bus)
    p = bus.latest("model_broker_result").payload
    assert p["available"] is False
    assert "cobra" in p["reason"]
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_model_broker_agent.py -q`
Expected: FAIL(ModuleNotFoundError: ...model_broker_agent)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/agents/model_broker_agent.py`:

```python
"""ModelBrokerAgent:模型治理代理,进 message bus。

收 model_request(payload {model_name})→ 查 ModelZooRegistry + 检 requires 依赖 + 解析 source →
产 model_broker_result({model_name, available, status, wrapper, reason})。

铁律(本 Phase 核心):status != available / requires 依赖不满足 / source 需人工获取 →
available=False + reason,fail-closed,绝不 silent accept。gpu 无法静态检测,按声明降级
(available=False,reason 注明需运行时确认 gpu)。
"""
from __future__ import annotations

import importlib.util

from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.model_zoo.downloader import resolve_source
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry

# 可静态检测的 python 依赖(gpu 不可静态检 → 见下)
_PY_DEPS = {"torch", "cobra"}


def _dep_available(dep: str) -> bool:
    """python 依赖是否可 import(gpu 类非 python 依赖返 False,交由 reason 说明)。"""
    if dep in _PY_DEPS:
        return importlib.util.find_spec(dep) is not None
    return False  # gpu 等运行时资源无法静态确认 → 保守判不满足(fail-closed)


class ModelBrokerAgent(BaseAgent):
    name = "ModelBrokerAgent"

    def __init__(self, registry: ModelZooRegistry | None = None) -> None:
        self._reg = registry or ModelZooRegistry()

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        model_name = message.payload.get("model_name")
        result = self._resolve(model_name)
        bus.send(AgentMessage(
            message_id=message.message_id + ":broker",
            sender=self.name, receiver="EnsembleCoordinator",
            message_type="model_broker_result", payload=result,
            timestamp=message.timestamp, parent_message_id=message.message_id))

    def _resolve(self, model_name: str | None) -> dict:
        base = {"model_name": model_name, "available": False, "status": "missing",
                "wrapper": None, "reason": ""}
        # 1) 未知模型 → fail-closed
        try:
            entry = self._reg.get(model_name)
        except KeyError:
            base["reason"] = f"unknown model: {model_name}(未知模型,不静默接受)"
            return base

        status = entry["status"]
        base["status"] = status
        base["wrapper"] = entry.get("wrapper")

        # 2) status 非 available → fail-closed(planned/missing)
        if status != "available":
            base["reason"] = f"model status={status}, not available(fail-closed,not silent accept)"
            return base

        # 3) requires 依赖检查(缺任一 → 明确降级,点名缺的依赖)
        missing_deps = [d for d in entry.get("requires", []) if not _dep_available(d)]
        if missing_deps:
            base["reason"] = f"missing required dependencies: {missing_deps}(fail-closed)"
            return base

        # 4) source 解析(远端 gated → requires_manual_fetch → 不可用)
        src = resolve_source(entry)
        if not src["available"]:
            base["reason"] = f"source not resolvable: {src['reason']}"
            return base

        # 全部通过 → available
        base["available"] = True
        base["reason"] = "ok"
        return base
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_model_broker_agent.py -q`
Expected: 5 passed(cobra 已装,ecoli_gem available)。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 373 passed / 25 skipped / 0 failed(368 + 5 新)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/agents/model_broker_agent.py praxis_virtualcell/tests/test_model_broker_agent.py
git commit -m "feat(phase2): ModelBrokerAgent 进 message bus(available→wrapper;planned/missing/缺依赖→fail-closed)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 2.7:self_trained training_card 校验 + Phase 2 完成闸门

**决策说明:** self_trained 类型的模型在 registry 里**必须**有 `training_card`(字段:training_data / split / baseline / metrics / provenance),缺则加载校验失败(fail-closed:无 provenance 的自训模型不入库)。此校验加进 `ModelZooRegistry._validate`(Task 2.1 已建的校验函数),纯扩展不改现有逻辑。最后跑全量回归 + 红线核验 + 台账更新(**不打 tag**——Phase 2 不是里程碑,v1.0 要等 Phase 3)。

**Files:**
- Modify: `praxis_virtualcell/model_zoo/registry.py`(在 `_validate` 末尾加 self_trained → training_card 必填)
- Test: `praxis_virtualcell/tests/test_self_trained_card.py`
- Modify: `docs/STATUS-2026-07-03-v0.6-v0.8-delivery.md`(追加 Phase 2 完成台账段)

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_self_trained_card.py`:

```python
"""Phase 2:self_trained 模型必须有 training_card(training_data/split/baseline/metrics/provenance)。
铁律:无 provenance 的自训模型不入库(fail-closed)。测:合法通过;缺 card → ValueError;缺字段 → ValueError。"""
import pytest

from praxis_virtualcell.model_zoo.registry import ModelZooRegistry


def _write(tmp_path, card_block: str) -> str:
    p = tmp_path / "reg.yaml"
    p.write_text(
        "models:\n"
        "  yst:\n"
        "    name: yst\n"
        "    type: self_trained\n"
        "    species: [yeast]\n"
        "    module: genetic_hub\n"
        "    task: deletion_fitness\n"
        "    source: 'self_trained:yst'\n"
        "    license: internal\n"
        "    status: planned\n"
        "    wrapper: x.Y\n"
        "    version: v0\n"
        "    requires: [torch]\n"
        "    reliability_policy: ml_disagreement\n"
        + card_block,
        encoding="utf-8")
    return str(p)


def test_self_trained_with_full_card_loads(tmp_path):
    card = (
        "    training_card:\n"
        "      training_data: SGD deletion library\n"
        "      split: by-gene holdout\n"
        "      baseline: mean-fitness\n"
        "      metrics: {pearson: null}\n"
        "      provenance: planned\n"
    )
    reg = ModelZooRegistry(registry_path=_write(tmp_path, card))
    assert reg.get("yst")["training_card"]["split"] == "by-gene holdout"


def test_self_trained_without_card_is_rejected(tmp_path):
    with pytest.raises(ValueError) as ei:
        ModelZooRegistry(registry_path=_write(tmp_path, ""))
    assert "training_card" in str(ei.value)


def test_self_trained_card_missing_field_is_rejected(tmp_path):
    card = (
        "    training_card:\n"
        "      training_data: SGD deletion library\n"
        "      split: by-gene holdout\n"
        # 缺 baseline / metrics / provenance
    )
    with pytest.raises(ValueError) as ei:
        ModelZooRegistry(registry_path=_write(tmp_path, card))
    assert "training_card" in str(ei.value)


def test_public_model_needs_no_card(tmp_path):
    """public_model 不要求 training_card(只 self_trained 要求)。"""
    p = tmp_path / "reg.yaml"
    p.write_text(
        "models:\n"
        "  pub:\n"
        "    name: pub\n"
        "    type: public_model\n"
        "    species: [bacteria]\n"
        "    module: cytoplasmic_metabolism\n"
        "    task: growth\n"
        "    source: cobra_bundled_textbook\n"
        "    license: MIT\n"
        "    status: available\n"
        "    wrapper: x.Y\n"
        "    version: v1\n"
        "    requires: [cobra]\n"
        "    reliability_policy: gem_growth\n",
        encoding="utf-8")
    reg = ModelZooRegistry(registry_path=str(p))
    assert reg.get("pub")["type"] == "public_model"
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_self_trained_card.py -q`
Expected: FAIL(`test_self_trained_without_card_is_rejected` 不抛 ValueError → 失败;因当前 `_validate` 尚未查 training_card)。

- [ ] **Step 3: 扩 `_validate`(加 self_trained → training_card 必填)**

在 `praxis_virtualcell/model_zoo/registry.py` 的 `_validate` 方法末尾(`requires` 检查之后)加入:

找到:

```python
        if not isinstance(entry.get("requires", []), list):
            raise ValueError(f"{name} requires 必须是 list")
```

在其后追加:

```python
        # self_trained 必须带 training_card(无 provenance 的自训模型不入库,fail-closed)
        if entry["type"] == "self_trained":
            card = entry.get("training_card")
            required_card = ("training_data", "split", "baseline", "metrics", "provenance")
            if not isinstance(card, dict):
                raise ValueError(f"{name} 是 self_trained 但缺 training_card(必填)")
            missing = [k for k in required_card if k not in card]
            if missing:
                raise ValueError(f"{name} training_card 缺字段: {missing}")
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_self_trained_card.py -q`
Expected: 4 passed。

- [ ] **Step 5: 红线核验 —— LLM 边界 + golden/negative KPI 仍绿**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_llm_boundary_flags.py praxis_virtualcell/tests/test_golden_cases.py praxis_virtualcell/tests/test_negative_cases.py -q`
Expected: 全绿(Phase 2 未碰管线/治理,assert_llm_boundaries 三 flag 恒 False、golden unsafe-accept=0、negative 无静默 accept 不变)。

- [ ] **Step 6: 全量回归(精确数)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q --junit-xml=/tmp/junit_phase2.xml`
然后取精确数:
Run: `python3 -c "import xml.etree.ElementTree as ET; r=ET.parse('/tmp/junit_phase2.xml').getroot(); s=r if r.tag=='testsuite' else r[0]; print('tests=%s failures=%s errors=%s skipped=%s'%(s.get('tests'),s.get('failures'),s.get('errors'),s.get('skipped')))"`
Expected: `tests=377 failures=0 errors=0 skipped=25`(344 基线 + 6+5+4+5+4+5+4 = 33 新 = 377;cobra 已装,gem_wrapper 4 条计入 passed)。关键:failures=0 errors=0。

- [ ] **Step 7: 核对新增数据/代码进 wheel(离线报告基建仍在)**

model_zoo 是 `praxis_virtualcell/` 下新子包(纯 .py + registry.yaml);现有 `MANIFEST.in` 已有 `recursive-include praxis_virtualcell *.yaml *.json`,`registry.yaml` 自动纳入。核对:
Run: `grep -n "recursive-include praxis_virtualcell" MANIFEST.in`
Expected: 有该行(`registry.yaml` 被覆盖)。若无 `*.yaml` 通配则追加。
再核对离线报告基线仍绿:
Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/baseline -q`
Expected: 全绿(Phase 2 未碰管线,离线报告不变)。

- [ ] **Step 8: 台账更新(不打 tag)**

在 `docs/STATUS-2026-07-03-v0.6-v0.8-delivery.md` 末尾追加(用 Edit 在文件尾部加一段):

```markdown

---

## Phase 2 完成台账(2026-07-04,ModelBroker + model_zoo)

- **交付**:`praxis_virtualcell/model_zoo/`(registry.yaml + registry.py + cache.py + downloader.py + wrappers/{base,gem_wrapper}.py)+ `agents/model_broker_agent.py`。
- **契约**:ModelWrapper 扩 PredictorAgent 补 declare_scope/estimate_uncertainty;GemWrapper 在**真 GemModel** 上跑通(cobra-gated)。
- **红线守住**:缺模型/缺依赖(requires)/sha 不匹配/远端权重 → 全 fail-closed,无 silent accept;self_trained 无 training_card 不入库。管线/治理/LLM 边界未动,344 基线零回归 → **377 passed / 25 skipped / 0 failed**。
- **未接管线**:Phase 2 只交付 model_zoo 库 + ModelBrokerAgent(可独立测试);接进 runtime 管线留 Phase 3。
- **不打 tag**:Phase 2 不是里程碑,v1.0 要等 Phase 3(module router)。下一步回主路线图 §9 展开 Phase 3。
```

- [ ] **Step 9: 提交(不 tag、不 push)**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/model_zoo/registry.py praxis_virtualcell/tests/test_self_trained_card.py docs/STATUS-2026-07-03-v0.6-v0.8-delivery.md
git commit -m "feat(phase2): self_trained training_card 必填校验 + Phase 2 完成闸门(377 passed,不打 tag)

Phase 2 交付 ModelBroker + model_zoo:声明式注册表 / ModelWrapper 契约 / GemWrapper 真模型 /
cache+sha256 版本锁 / 下载契约(远端 gated)/ ModelBrokerAgent 进 bus。缺模型/缺依赖/sha 不匹配
一律 fail-closed。管线未动,344 基线保持。Phase 2 非里程碑,不打 tag,v1.0 等 Phase 3。

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

**Phase 2 验收:**
- ✅ 声明式模型注册表(`ModelZooRegistry` + `registry.yaml`),module ∈ MODULE_ORDER 白名单校验,未知 name → KeyError。
- ✅ ModelWrapper 契约(扩 PredictorAgent + declare_scope/estimate_uncertainty),超出 scope → rejected 不硬预测,uncertainty 缺失优雅降级。
- ✅ GemWrapper 在**真 GemModel** 上证明契约(cobra-gated 真跑 KO;基因不在 GEM 不虚构)。
- ✅ cache + sha256 版本锁:缺失/不匹配 → unavailable,fail-closed。
- ✅ 下载契约:本地资产指认;远端 GEARS/scGPT gated → requires_manual_fetch,不静默;缺 source → 报错。
- ✅ ModelBrokerAgent 进 bus:available→wrapper;planned/missing/缺依赖 → fail-closed 不 silent accept。
- ✅ self_trained 必带 training_card(无 provenance 不入库)。
- ✅ 344 基线零回归(纯新增 + 复用,未碰管线/治理/LLM 边界),→ 377 passed;不打 tag。

---

## Self-Review(写完对照骨架 + 真实代码)

- **骨架覆盖**:7 个 task(2.1 registry / 2.2 ModelWrapper / 2.3 GemWrapper / 2.4 cache / 2.5 downloader / 2.6 broker agent / 2.7 training_card + 闸门)全部展开,每个 TDD 红→绿→commit。骨架每条子要求(schema 字段全集、declare_scope/estimate_uncertainty、cobra-gated skip、sha256、远端 gated、fail-closed、training_card 必填、不打 tag)均落到具体测试断言。

- **写作中发现并修正的点:**
  1. **基线测试数从 277 改到 344**:骨架/模板引用 277(Phase 0 前基线),但实跑核实**当前分支 `feat/v0.9-phase0-module-core` 已是 344 passed / 25 skipped**(Phase 0+1 已 commit,含 baseline + biological_modules 测试)。全计划的期望测试数以 344 为起点重算(→377),避免执行者对不上数。
  2. **`estimate_uncertainty` 默认实现处理 None**:骨架说"默认从 run_prediction 的 uncertainty 提取",但核实 `PredictorAgent.run_prediction` 的 uncertainty 可能为 None(`base.py:63` `out.get("uncertainty")`)。若直接透传会误导下游"有不确定性"。改为返回 `{"available": bool, ...}` 契约,None → `available=False`(诚实)。已在 Task 2.2 代码 + 专门测试 `test_estimate_uncertainty_handles_missing_gracefully` 落实。
  3. **`GemModel` 是普通类不是 agent**:骨架说"GemWrapper 包 GemModel"。核实 `GemModel` 无 `handle`、非 PredictorAgent,故 GemWrapper 的 `run_prediction` 内部 lazy 实例化 `EcoliGEM()`/`GemModel(path)` 并调 `knockout_many`,而不是"把 GemModel 当 predictor 直接继承"。GemWrapper 自己 extends ModelWrapper→PredictorAgent 拿 fail-closed。
  4. **不改 `RuntimeConfig`**:核实 config **无 `cache_root` 字段**。cache 目录改由 `ModelCache` 自管(默认 `~/.cache/...`,可 override,测试用 tmp_path),不动 config —— 守"不改现有逻辑"铁律。
  5. **cobra 已装**:核实本仓 `.venv` 已装 cobra(`test_ecoli_gem_case` 实跑非 skip),故 gem_wrapper 4 条测试计入 **passed** 而非 skipped;若换到无 cobra 环境则 skip(测试用 `importorskip` 已 gated)。skip 基线仍 25。
  6. **module 白名单来源**:用 `biological_modules.modules.MODULE_ORDER`(Phase 1 已落),registry `_validate` 直接引它 —— 与 Task 2.1 registry.yaml 的 `ecoli_gem.module=cytoplasmic_metabolism`、GemWrapper.declare_scope 的 module 三处一致(类型一致性检查通过)。
  7. **downloader `_REPO_ROOT` = parents[2]**:`downloader.py` 在 `praxis_virtualcell/model_zoo/`,`parents[2]` = repo 根,对齐 `yeast_gem.py` 用 `parents[3]`(那文件在 `predictors/mechanistic/` 深一层)。已核实层级差异,path 解析正确。

- **无占位符**:每步含完整可跑代码 + 确切命令 + 期望输出。测试用最小 Dummy 具化 abstract(`_DummyWrapper`),monkeypatch 模拟缺依赖,tmp_path 造坏 yaml,均无 TODO。

- **类型一致性**:`ModelZooRegistry.get/status/is_available/by_module/by_species/names` 签名在 registry.py 定义、测试与 broker 中调用一致;`AssetStatus(available,path,reason)` / `resolve_source(entry)->dict{status,available,...}` / broker `_resolve->dict{model_name,available,status,wrapper,reason}` 三处返回结构自洽;`ModelWrapper.declare_scope()->dict`、`estimate_uncertainty(model_input,prediction)->dict{available,...}` 在 base/gem_wrapper/测试中签名统一。

- **铁律段完整**:纯新增+复用、fail-closed 核心红线、测试口径 `praxis_virtualcell/tests` + junit 精确数、cobra/torch gated skip、每 task 删 `._*` + commit trailer + 当前分支不 push/tag —— 全写进头部铁律段并逐 task 执行。

---

## 下一步(Phase 3 展开时机)

Phase 2 全部 task 绿(377 passed)后,回主路线图 §9,把 **Phase 3(module router + 把 model_zoo/broker 接进 runtime 管线)** 展开成同粒度详细计划。Phase 3 到 v1.0 里程碑才打 tag。Phase 3 会用到本 Phase 的 `ModelBrokerAgent`(bus 接线)+ `ModelZooRegistry`(module→模型查询)+ ModelWrapper 契约。
