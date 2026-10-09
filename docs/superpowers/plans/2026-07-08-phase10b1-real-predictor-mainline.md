# P10.B1 真实预测器接入主链(adapter + gem_fba 首接)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建 adapter 基建把真实 `run_*_case` 接进 offline 主链,首接 gem_fba engine——让 bacteria/yeast gene KO growth 请求在主链跑真实 cobra FBA,同时保 mock 请求(donor_predictor/AHR)字节等价不变。

**Architecture:** `CaseRunnerPredictorAgent`(PredictorAgent 子类,内部按 engine→runner 分发)把 CaseReport 映射成 `{prediction:{delta},...}`;`ModelApplicability` 按 route engine 分诊(`gem_fba`→adapter、其余→现状 mock 枚举);EnsembleCoordinator 已支持单 predictor,无需改。

**Tech Stack:** Python、cobra(0.31.1 本地已装)、pytest。测试口径 `praxis_virtualcell/tests`(裸 pytest 会卷入根 tests/,永远显式 `pytest praxis_virtualcell/tests`)。提交前必跑 `ruff check`。

**上游:** spec `docs/superpowers/specs/2026-07-08-phase10b1-real-predictor-mainline-design.md`。

**红线:** 不碰 reliability/critic/provenance/LLM 边界裁决逻辑;ModelApplicability 只改"选哪些候选";真实预测确定性(cobra FBA 已证字节稳);adapter 诚实透传不伪造;根 tests/ 零触碰;不 push;trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。

---

## File Structure

- **Modify** `praxis_virtualcell/core/exceptions.py` — 加 `UnsupportedEngine`
- **Create** `praxis_virtualcell/agents/request_adapter.py` — 抽出 `request_to_module_input`(A→B 键映射)
- **Modify** `praxis_virtualcell/core/runtime.py:175` — `_request_to_module_input` 改委托 request_adapter(消重、保兼容)
- **Create** `praxis_virtualcell/predictors/case_dispatch.py` — `dispatch_runner` + `map_case_delta`
- **Create** `praxis_virtualcell/predictors/case_runner_agent.py` — `CaseRunnerPredictorAgent`
- **Modify** `praxis_virtualcell/agents/model_applicability.py` — `_REAL_ENGINES` 分诊
- **Modify** `praxis_virtualcell/workflows/predict_delta_expression.py:30` — 注册 adapter
- **Modify** 受影响测试(执行时定位,如 `tests/test_offline_workflow.py`) — bacteria/yeast growth abstain→predict
- **Create** `praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` — B1 契约/端到端测试

---

## Task 1: UnsupportedEngine 异常

**Files:** Modify `praxis_virtualcell/core/exceptions.py`;Test `tests/phase10/test_t10_2_module_contracts.py`

- [ ] **Step 1: Write the failing test**

新建 `praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py`:
```python
from praxis_virtualcell.core.exceptions import PraxisVCError, UnsupportedEngine


def test_unsupported_engine_is_praxisvc_error():
    assert issubclass(UnsupportedEngine, PraxisVCError)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py::test_unsupported_engine_is_praxisvc_error -v`
Expected: FAIL — `ImportError: cannot import name 'UnsupportedEngine'`。

- [ ] **Step 3: Write minimal implementation**

`praxis_virtualcell/core/exceptions.py` 末尾追加:
```python
class UnsupportedEngine(PraxisVCError):
    """B1 case 分发:请求的 engine/物种/扰动组合尚无接入的真实 case runner。"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: 同 Step 2。Expected: PASS。

- [ ] **Step 5: ruff + commit**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && .venv/bin/ruff check praxis_virtualcell/core/exceptions.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` → All checks passed。
```bash
git add praxis_virtualcell/core/exceptions.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "feat(phase10b1): Task 1 UnsupportedEngine 异常

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: 抽出 request_to_module_input 共享函数

**Files:** Create `praxis_virtualcell/agents/request_adapter.py`;Modify `praxis_virtualcell/core/runtime.py:175`;Test `tests/phase10/test_t10_2_module_contracts.py`

**背景:** `AgentRuntime._request_to_module_input`(runtime.py:175,@staticmethod)是 A 面 request → B 面 raw 键映射。B1 的 adapter 与 ModelApplicability 都要用,抽为独立函数,runtime 改委托(消重、保现有行为)。

- [ ] **Step 1: Write the failing test**

往 `test_t10_2_module_contracts.py` 追加:
```python
from praxis_virtualcell.agents.request_adapter import request_to_module_input


def test_request_to_module_input_maps_keys():
    req = {"species": "bacteria", "perturbation_type": "gene",
           "perturbation_targets": ["b0720"], "output_modality": "growth"}
    raw = request_to_module_input(req)
    assert raw["species"] == "bacteria"
    assert raw["perturbation_object"] == "gene"      # perturbation_type → perturbation_object
    assert raw["target_output"] == "growth"          # output_modality → target_output
    assert raw["perturbation_targets"] == ["b0720"]


def test_request_to_module_input_default_expression():
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "output_modality": "delta_expression"}
    assert request_to_module_input(req)["target_output"] == "expression"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k request_to_module -v`
Expected: FAIL — `ModuleNotFoundError: praxis_virtualcell.agents.request_adapter`。

- [ ] **Step 3: Write minimal implementation**

新建 `praxis_virtualcell/agents/request_adapter.py`(逐字迁移 runtime._request_to_module_input 的函数体):
```python
"""A 面 request(perturbation_type/output_modality/metadata.requested_outputs)确定性映射到
module 路由期望的 B 面 raw(perturbation_object/target_output/perturbation_targets)。零 LLM。
runtime 与 ModelApplicability/CaseRunner 共用。"""
from __future__ import annotations

_OUT_MAP = {"delta_expression": "expression", "pathway_response": "flux",
            "reliability_report": "expression", "growth": "growth", "flux": "flux",
            "state": "state", "communication": "communication", "expression": "expression"}


def request_to_module_input(req: dict) -> dict:
    requested = ((req.get("metadata") or {}).get("requested_outputs") or [])
    target_output = next((o for o in requested if o in _OUT_MAP.values()), None)
    if target_output is None:
        target_output = _OUT_MAP.get(str(req.get("output_modality", "")).lower(), "expression")
    raw = {"species": req.get("species"),
           "perturbation_object": req.get("perturbation_type"),
           "target_output": target_output,
           "perturbation_targets": list(req.get("perturbation_targets") or [])}
    for k in ("cell_type", "medium", "dose"):
        if req.get(k) is not None:
            raw[k] = req[k]
    return raw
```

改 `praxis_virtualcell/core/runtime.py` 的 `_request_to_module_input` 为委托(保持 @staticmethod 签名不变,函数体改成):
```python
    @staticmethod
    def _request_to_module_input(req: dict) -> dict:
        """委托 agents.request_adapter.request_to_module_input(消重,行为不变)。"""
        from praxis_virtualcell.agents.request_adapter import request_to_module_input
        return request_to_module_input(req)
```
(删掉原 `_OUT_MAP`/函数体逻辑,只留委托。原 docstring 可精简。)

- [ ] **Step 4: Run test to verify it passes + 现有 module 路由测试不破**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k request_to_module praxis_virtualcell/tests/test_runtime_module_plan.py praxis_virtualcell/tests/test_module_router_agent.py -v`
Expected: 全 PASS(委托后行为不变)。

- [ ] **Step 5: ruff + 全量 + commit**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && .venv/bin/ruff check praxis_virtualcell/agents/request_adapter.py praxis_virtualcell/core/runtime.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` → All checks passed。
Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider 2>&1 | tail -3` → 应 ≥672 passed / 0 failed(670 + 本批新增 4 测试)。
```bash
git add praxis_virtualcell/agents/request_adapter.py praxis_virtualcell/core/runtime.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "refactor(phase10b1): Task 2 抽出 request_to_module_input 共享函数(runtime 委托)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: case_dispatch(dispatch_runner + map_case_delta)

**Files:** Create `praxis_virtualcell/predictors/case_dispatch.py`;Test `tests/phase10/test_t10_2_module_contracts.py`

- [ ] **Step 1: Write the failing test**

追加:
```python
from types import SimpleNamespace

import pytest

from praxis_virtualcell.core.exceptions import UnsupportedEngine
from praxis_virtualcell.predictors.case_dispatch import dispatch_runner, map_case_delta


def test_dispatch_runner_gem_fba_bacteria():
    raw = {"species": "bacteria", "perturbation_object": "gene"}
    from praxis_virtualcell.predictors.mechanistic.ecoli_gem import run_ecoli_growth_case
    assert dispatch_runner("gem_fba", raw) is run_ecoli_growth_case


def test_dispatch_runner_gem_fba_yeast():
    raw = {"species": "yeast", "perturbation_object": "gene"}
    from praxis_virtualcell.predictors.mechanistic.yeast_gem import run_yeast_growth_case
    assert dispatch_runner("gem_fba", raw) is run_yeast_growth_case


def test_dispatch_runner_unsupported():
    with pytest.raises(UnsupportedEngine):
        dispatch_runner("state_scoring", {"species": "human", "perturbation_object": "gene"})


def test_map_case_delta_gem_fba():
    report = SimpleNamespace(raw_output={"knockouts": [
        {"gene": "b0720", "ratio": 0.0}, {"gene": "x", "ratio": 1.0}, {"gene": "y", "ratio": None}]})
    # ratio-1: essential 0.0→-1.0, 无效应 1.0→0.0, None 跳过
    assert map_case_delta("gem_fba", report) == [-1.0, 0.0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "dispatch_runner or map_case_delta" -v`
Expected: FAIL — `ModuleNotFoundError: case_dispatch`。

- [ ] **Step 3: Write minimal implementation**

新建 `praxis_virtualcell/predictors/case_dispatch.py`:
```python
"""engine→真实 run_*_case 分发 + CaseReport→delta 映射。B1 只实现 gem_fba 的 gene→growth。
其余 engine / gem_fba 的 medium·drug 子路径由后续增量 task 往这里加分支。"""
from __future__ import annotations

from praxis_virtualcell.core.exceptions import UnsupportedEngine

# 已接入真实预测的 engine(ModelApplicability 分诊用同一集合的镜像,见 model_applicability._REAL_ENGINES)
REAL_ENGINES = frozenset({"gem_fba"})


def dispatch_runner(engine: str, raw_req: dict):
    """engine + 请求上下文 → 具体 run_*_case(返回可调用,签名 (raw_req, ...) → (CaseReport, RouteDecision))。"""
    species = raw_req.get("species")
    obj = raw_req.get("perturbation_object")
    if engine == "gem_fba" and obj == "gene":
        if species == "bacteria":
            from praxis_virtualcell.predictors.mechanistic.ecoli_gem import run_ecoli_growth_case
            return run_ecoli_growth_case
        if species == "yeast":
            from praxis_virtualcell.predictors.mechanistic.yeast_gem import run_yeast_growth_case
            return run_yeast_growth_case
    raise UnsupportedEngine(f"B1 未接入 case runner: engine={engine} object={obj} species={species}")


def map_case_delta(engine: str, report) -> list[float]:
    """CaseReport.raw_output → delta 向量(确定性,继承 raw_output 的 round)。"""
    if engine == "gem_fba":
        # 每个 KO 基因 growth 相对 WT 的变化:ratio-1(essential ratio0→-1.0;无效应 1.0→0)。
        # ratio None(基因不在 GEM)→跳过,不虚构(disposition 已 abstain/caution 表达)。
        return [round(k["ratio"] - 1.0, 4) for k in report.raw_output["knockouts"]
                if k["ratio"] is not None]
    raise UnsupportedEngine(f"map_case_delta 未支持 engine={engine}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: 同 Step 2。Expected: PASS(4 个)。

- [ ] **Step 5: ruff + commit**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && .venv/bin/ruff check praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` → All checks passed。
```bash
git add praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "feat(phase10b1): Task 3 case_dispatch(engine→runner 分发 + gem_fba delta 映射)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: CaseRunnerPredictorAgent adapter

**Files:** Create `praxis_virtualcell/predictors/case_runner_agent.py`;Test `tests/phase10/test_t10_2_module_contracts.py`

- [ ] **Step 1: Write the failing test**

追加(单元测试 adapter 的 run_prediction 映射 + assess_applicability):
```python
from praxis_virtualcell.predictors.case_runner_agent import CaseRunnerPredictorAgent

_BACT_GROWTH = {"species": "bacteria", "perturbation_type": "gene",
                "perturbation_targets": ["b0720"], "input_modality": "scRNA",
                "output_modality": "growth", "task_type": "predict_delta_expression"}


def test_case_runner_run_prediction_gem_fba():
    agent = CaseRunnerPredictorAgent()
    out = agent.run_prediction({"request": _BACT_GROWTH})
    assert out["prediction"]["delta"] == [-1.0]         # b0720 essential
    assert out["uncertainty"]["disposition"] == "accept"
    assert out["provenance"]["engine"] == "gem_fba"
    assert out["provenance"]["tool"] == "cobrapy"
    assert out["provenance"]["case_id"]


def test_case_runner_assess_applicability_reject_unsupported():
    agent = CaseRunnerPredictorAgent()
    # human gene expression → route donor_predictor(非真实 engine)→ dispatch UnsupportedEngine → reject
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    score, reject = agent.assess_applicability(req, {})
    assert reject is not None and score == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k case_runner -v`
Expected: FAIL — `ModuleNotFoundError: case_runner_agent`。

- [ ] **Step 3: Write minimal implementation**

新建 `praxis_virtualcell/predictors/case_runner_agent.py`:
```python
"""真实 case runner → offline 主链的 adapter。PredictorAgent 子类,内部按 route engine
分发到具体 run_*_case,把 CaseReport 映射成 {prediction:{delta},uncertainty,evidence,provenance}。
诚实透传 CaseReport 的 disposition/boundary,不伪造。"""
from __future__ import annotations

from praxis_virtualcell.agents.request_adapter import request_to_module_input
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.core.exceptions import UnsupportedEngine
from praxis_virtualcell.predictors.base import PredictorAgent
from praxis_virtualcell.predictors.case_dispatch import dispatch_runner, map_case_delta


class CaseRunnerPredictorAgent(PredictorAgent):
    name = "CaseRunner"

    def prepare_input(self, request: dict, brain_context: dict) -> dict:
        return {"request": request}          # adapter 需完整 request(route+dispatch 用)

    def assess_applicability(self, request: dict, brain_context: dict) -> tuple[float, str | None]:
        raw = request_to_module_input(request)
        engine = route(normalize_request(raw)).engine
        try:
            dispatch_runner(engine, raw)
        except UnsupportedEngine as e:
            return 0.0, str(e)
        return 1.0, None

    def run_prediction(self, model_input: dict) -> dict:
        request = model_input["request"]
        raw = request_to_module_input(request)
        engine = route(normalize_request(raw)).engine
        runner = dispatch_runner(engine, raw)
        report, _ = runner(raw)              # runner 内部自 normalize+route+真跑
        return {
            "prediction": {"delta": map_case_delta(engine, report)},
            "uncertainty": {"disposition": report.reliability_decision["disposition"],
                            "caution_flags": report.reliability_decision["caution_flags"]},
            "evidence": list(report.provenance_boundary.get("rules_hit", [])),
            "provenance": {**report.provenance_boundary, "case_id": report.case_id, "engine": engine},
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: 同 Step 2。Expected: PASS(2 个)。

- [ ] **Step 5: ruff + commit**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && .venv/bin/ruff check praxis_virtualcell/predictors/case_runner_agent.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` → All checks passed。
```bash
git add praxis_virtualcell/predictors/case_runner_agent.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "feat(phase10b1): Task 4 CaseRunnerPredictorAgent adapter(CaseReport→delta 映射)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: ModelApplicability _REAL_ENGINES 分诊

**Files:** Modify `praxis_virtualcell/agents/model_applicability.py`;Test `tests/phase10/test_t10_2_module_contracts.py`

- [ ] **Step 1: Write the failing test**

追加(直接驱动 ModelApplicabilityAgent.handle,验证 gem_fba→CaseRunner、donor→mock 不变):
```python
from praxis_virtualcell.agents.model_applicability import ModelApplicabilityAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _run_applicability(req):
    bus = MessageBus()
    bus.set_context(trace_id="t", task_id="t")
    agent = ModelApplicabilityAgent()
    msg = AgentMessage("m1", "SpeciesBrain", "ModelApplicability", "decide",
                       {"request": req, "brain_context": {"species": req["species"]}}, "t0001")
    agent.handle(msg, bus)
    return bus.latest("applicability_decided").payload


def test_applicability_gem_fba_routes_to_case_runner():
    out = _run_applicability(_BACT_GROWTH)
    assert out["applicable"] == ["CaseRunner"]
    assert out["rejected_candidates"] == []
    assert out["brain_context"]["routing"]["real_engine"] == "gem_fba"


def test_applicability_donor_predictor_keeps_mock_enumeration():
    # human AHR gene→expression: route donor_predictor(非真实 engine)→ 走现状 mock 枚举
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    out = _run_applicability(req)
    # 现状:brain_context 无 model_applicability 规则 → 3 mock 全 rejected(unsupported_species 等),
    # 但关键是仍走 mock 枚举分支(applicable/rejected 只含 mock 名,不含 CaseRunner)
    assert "CaseRunner" not in out["applicable"]
    assert set(out["rejected_candidates"]) <= {"MockLinear", "MockCPA", "MockGEARS"}
    assert "real_engine" not in out["brain_context"].get("routing", {})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k applicability -v`
Expected: FAIL — `test_applicability_gem_fba_routes_to_case_runner`:现状 gem_fba 请求走 mock 枚举 → applicable 不是 ["CaseRunner"](多半空 + rejected 含 mock)。

- [ ] **Step 3: Write minimal implementation**

`praxis_virtualcell/agents/model_applicability.py`:顶部 import 加(按 ruff 排序):
```python
from praxis_virtualcell.agents.request_adapter import request_to_module_input
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
```
模块级常量(在 `_CANDIDATES` 附近)加:
```python
_REAL_ENGINES = frozenset({"gem_fba"})   # 已接入真实 case runner 的 engine(与 case_dispatch.REAL_ENGINES 对齐)
```
`handle` 方法开头(读 req/bc 后、mock 枚举 for 循环前)插入分诊:
```python
    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        req = message.payload["request"]
        bc = message.payload["brain_context"]
        # B1:真实 engine 请求 → 候选=单个 CaseRunner adapter,跳过 mock 枚举(其余 engine 走现状)
        raw = request_to_module_input(req)
        engine = route(normalize_request(raw)).engine
        if engine in _REAL_ENGINES:
            bc2 = {**bc, "routing": {"cautions": {}, "rejection_reasons": {},
                                     "rules_hit": [], "real_engine": engine}}
            bus.send(AgentMessage(message.message_id + ":app", self.name,
                "EnsembleCoordinator", "applicability_decided",
                {"request": req, "brain_context": bc2,
                 "applicable": ["CaseRunner"], "rejected_candidates": []},
                message.timestamp, message.message_id))
            return
        appmap = bc.get("model_applicability") or {}
        # ...(原有 mock 枚举逻辑完全不变,从 vocab=... 那行起)
```
(注:原 `req`/`bc` 读取行若已在开头,复用即可;只在其后、`appmap=...` 前插入分诊块。原 mock 枚举逻辑一行不动。)

- [ ] **Step 4: Run test to verify it passes + mock 请求现状不变**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k applicability praxis_virtualcell/tests/test_module_applicability.py -v`
(若无 test_module_applicability.py,改跑 `praxis_virtualcell/tests/test_offline_mode.py` 等 offline 冒烟)
Expected: 全 PASS(gem_fba→CaseRunner;donor/mock 枚举不变)。

- [ ] **Step 5: ruff + commit**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && .venv/bin/ruff check praxis_virtualcell/agents/model_applicability.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` → All checks passed。
```bash
git add praxis_virtualcell/agents/model_applicability.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "feat(phase10b1): Task 5 ModelApplicability 按 engine 分诊(gem_fba→CaseRunner,mock 路径不变)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: build_runtime 注册 adapter + 端到端真实预测

**Files:** Modify `praxis_virtualcell/workflows/predict_delta_expression.py:30`;Test `tests/phase10/test_t10_2_module_contracts.py`

- [ ] **Step 1: Write the failing test**

追加(offline 端到端:bacteria b0720 growth → 真实 FBA accept):
```python
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_CFG = RuntimeConfig(mode=Mode.OFFLINE)


def test_bacteria_growth_runs_real_fba_end_to_end():
    out = run_query(dict(_BACT_GROWTH), config=_CFG)
    rd = out["reliability_decision"]
    assert rd["abstain"] is False                        # 接入真实 GEM → 不再 abstain
    sr = out["structured_report"]
    assert "CaseRunner" in sr["provenance"]["models_used"]
    assert out["llm_used_for_prediction"] is False       # 仍零 LLM
    # 真实预测:b0720 essential → delta [-1.0]
    assert sr["prediction"]["delta"] == [-1.0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k bacteria_growth_runs_real -v`
Expected: FAIL — CaseRunner 未注册,fan-out 到 "CaseRunner" 抛 UnknownAgentError,或 applicable=["CaseRunner"] 但无此 agent。

- [ ] **Step 3: Write minimal implementation**

`praxis_virtualcell/workflows/predict_delta_expression.py`:import 区加 `from praxis_virtualcell.predictors.case_runner_agent import CaseRunnerPredictorAgent`;`build_runtime` 的第一个 register 循环(line 29-32)把 `CaseRunnerPredictorAgent()` 加进 tuple(与 3 mock 并列):
```python
    for a in (InputInterpreterAgent(), BioObjectNormalizerAgent(), SpeciesBrainAgent(cfg),
              ModelApplicabilityAgent(), MockLinearAgent(), MockCPAAgent(), MockGEARSAgent(),
              CaseRunnerPredictorAgent(),
              EnsembleCoordinatorAgent(), ReliabilityAgent(mode=cfg.reliability_mode), CriticAgent(),
              ProvenanceAgent(), ReportAgent()):
        rt.register_agent(a)
```

- [ ] **Step 4: Run test to verify it passes**

Run: 同 Step 2。Expected: PASS。

- [ ] **Step 5: ruff + commit**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && .venv/bin/ruff check praxis_virtualcell/workflows/predict_delta_expression.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` → All checks passed。
```bash
git add praxis_virtualcell/workflows/predict_delta_expression.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "feat(phase10b1): Task 6 build_runtime 注册 CaseRunner + bacteria growth 端到端真实 FBA

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: 受影响测试更新 + mock 字节等价 + 真实请求字节等价 + 全量回归

**Files:** Modify 受影响测试(执行时定位);Test `tests/phase10/test_t10_2_module_contracts.py`

- [ ] **Step 1: 补 mock 字节等价 + 真实请求字节等价测试**

往 `test_t10_2_module_contracts.py` 追加:
```python
import hashlib
import json as _json


def _canon(obj):
    return hashlib.sha256(_json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def test_real_request_rerun_byte_equal():
    outs = [run_query(dict(_BACT_GROWTH), config=_CFG) for _ in range(3)]
    assert len({_canon(o["structured_report"]) for o in outs}) == 1
    assert len({_canon(o["trace"]) for o in outs}) == 1


def test_mock_request_unchanged_by_adapter():
    # AHR(donor_predictor)仍走 3 mock,reliability 不 abstain、models_used 是 mock
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    used = out["structured_report"]["provenance"]["models_used"]
    assert "CaseRunner" not in used                       # mock 请求不碰 adapter
```

- [ ] **Step 2: 跑全量定位受影响测试**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider 2>&1 | tail -30`
Expected: phase10 新测试全 PASS;可能有少数现有测试因"bacteria/yeast gene growth 从 abstain→真实预测"而 FAIL(如 `test_offline_workflow.py` 断言 bacteria abstain 的用例)。记录 FAIL 清单。

- [ ] **Step 3: 逐个核对并更新受影响测试**

对每个 FAIL:确认失败是**"接入真实 GEM 使 bacteria/yeast gene growth 从 abstain 变真实预测"**(预期语义提升)——核对该请求确是 gene→growth(gem_fba)、结果是合理的真实 FBA(如 essential 基因 delta 负)。更新断言为真实预测结果。**若发现 mock 请求(donor_predictor/expression)行为改变、或非 gem_fba 路径异常 = 真实回归,停下排查,不改测试迁就。**

- [ ] **Step 4: 全量回归复绿**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider 2>&1 | tail -3`
Expected: 0 failed。

- [ ] **Step 5: ruff + commit**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && .venv/bin/ruff check praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` + 受影响测试文件 → All checks passed。
```bash
git add -A praxis_virtualcell/tests
git commit -m "test(phase10b1): Task 7 字节等价(mock 不变+真实请求)+ 受影响测试更新(bacteria/yeast growth abstain→predict)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: T10.2 契约收尾 + B1 勾账

**Files:** Test `tests/phase10/test_t10_2_module_contracts.py`(补 provenance/诚实标注断言);台账由控制器另做

- [ ] **Step 1: 补 gem_fba 模块契约测试**

追加(T10.2 契约:真实 case runner 的 provenance 诚实):
```python
def test_gem_fba_provenance_honest():
    out = run_query(dict(_BACT_GROWTH), config=_CFG)
    prov = out["structured_report"]["provenance"]
    # 真实预测 provenance 可追溯:采纳 CaseRunner、有规则来源
    assert "CaseRunner" in prov["models_used"]
    assert prov["rules_referenced"]                      # 非空(route reason 等)


def test_yeast_growth_also_real_fba():
    req = {"species": "yeast", "perturbation_type": "gene", "perturbation_targets": ["YBR166C"],
           "input_modality": "scRNA", "output_modality": "growth",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    assert out["reliability_decision"]["abstain"] is False
    assert "CaseRunner" in out["structured_report"]["provenance"]["models_used"]
```

- [ ] **Step 2: 跑 T10.2 套件 + 全量**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -v` → 全 PASS。
Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider 2>&1 | tail -3` → 0 failed。
(注:yeast_gem 需要 SBML 数据;若 yeast 测试因缺数据 skip/fail,如实报告——B1 至少 bacteria/ecoli 路径必须真绿,yeast 视数据可用性,不可用则标 skip 并记录留 B4 数据批。)

- [ ] **Step 3: ruff + commit(测试)**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && .venv/bin/ruff check praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` → All checks passed。
```bash
git add praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "test(phase10b1): Task 8 T10.2 gem_fba 模块契约(provenance 诚实 + yeast/ecoli 真实 FBA)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
(台账勾账由控制器在两审通过后另做,implementer 不碰 UPGRADE-PROGRESS.md。)

---

## Self-Review(计划 vs spec 覆盖)

- **spec §4.1 CaseRunnerPredictorAgent** → Task 4 ✅
- **spec §4.2 engine→runner 分发** → Task 3 ✅
- **spec §4.3 CaseReport→delta 映射(gem_fba ratio-1)** → Task 3(map_case_delta)✅
- **spec §4.4 ModelApplicability 按 engine 分诊 + request_to_module_input 抽出** → Task 2(抽出)+ Task 5(分诊)✅
- **spec §4.5 build_runtime 注册** → Task 6 ✅
- **spec §4.6 数据流(mock/真实两路径)** → Task 6(真实)+ Task 7(mock 不变)✅
- **spec §五 影响(bacteria/yeast growth abstain→predict)** → Task 7 受影响测试更新 ✅
- **spec §六 测试(端到端/字节等价/mock 不变/映射单元/受影响更新)** → Task 4/6/7/8 ✅
- **spec §七 完成标准** → Task 8 收尾 + 全量 0 failed ✅
- **UnsupportedEngine** → Task 1 ✅

无占位;类型/命名一致(`CaseRunner`/`dispatch_runner`/`map_case_delta`/`request_to_module_input`/`_REAL_ENGINES`/`UnsupportedEngine` 跨 task 一致)。
