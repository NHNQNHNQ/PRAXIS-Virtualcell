# P10.C2 provenance 完整性硬门 + per-call hash + 越界 cell type abstain 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给主链每个 model call 记 per-call hash(name/version/input/output/evidence),并在 `runtime.py` 后处理段加三个 fail-closed governance gate(per-call hash 完整性 / provenance 完整性 / cell_type 越界),全部复用 C1 模式——不碰 reliability/critic 裁决数值,只 override 对外 abstain。

**Architecture:** 纯确定性函数落 `governance/`,`runtime.py` 后处理段(C1 gate 之后)调用 + override。per-call hash 由 `predictors/base.py` 写进 result.provenance,由 `ProvenanceAgent` 汇总成 `report.provenance.per_call_hashes`。三 gate 共用 `governance/gate_util.py::apply_governance_gate` helper(C1 gate 保持内联不动)。

**Tech Stack:** Python 3.13,pytest,hashlib canonical sha256,无 torch/LLM。

**测试口径铁律**:全程 `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider`,**绝不裸跑 pytest**(仓库根 tests/ 有 praxis2 子项目会一堆 fail,红线外无关)。子代理环境缺 torch → GEARS remote 测试 skip 正常。

**红线**(每 task 守):reliability/critic 裁决逻辑与数值零改;ModelApplicability/REAL_ENGINES/route/registry 不改;核心内核 + 根 tests/ 零触碰;`llm_used_for_prediction` 恒 false;commit trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`;**commit 绝不含前端 WIP**(base/fonts/themes/tokens.css、.claude/、.playwright-mcp/、string.jpeg);不 push。测试新增 import 一律放文件顶部(防 ruff E402)。

---

## 文件结构(创建/修改)

**新建**:
- `praxis_virtualcell/governance/provenance_hash.py` — per-call hash 计算 + 完整性校验
- `praxis_virtualcell/governance/gate_util.py` — 三 gate 共用 override helper
- `praxis_virtualcell/governance/provenance_completeness.py` — report 级完整性契约校验
- `praxis_virtualcell/governance/cell_type_domain.py` — cell_type 越界判据(独立复用 reliability 逻辑)
- `praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py` — C2 全部测试

**修改**:
- `praxis_virtualcell/predictors/base.py` — `model_version` 类属性 + `handle` 三分支补 `per_call`(prepare_input 提到 try 外)
- `praxis_virtualcell/predictors/mock_linear.py` / `mock_cpa.py` / `mock_gears.py` — 声明 `model_version = "mock:<name>"`
- `praxis_virtualcell/predictors/case_runner_agent.py` — `run_prediction` provenance 加 `"model_version": engine`
- `praxis_virtualcell/agents/provenance_agent.py` — 汇总 `per_call_hashes`(只加一键,不碰现有 11 字段)
- `praxis_virtualcell/core/runtime.py` — 后处理段(C1 gate 之后)加 Gate A/B/C

---

## Task 0: 基线坐实(接线前提)

**Files:**
- Test: `praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py`(create)

- [ ] **Step 1: 跑全量基线,确认 784/40/0**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider -q`
Expected: `784 passed, 40 skipped`(0 failed)。记录数字;若不符先停,报告控制器。

- [ ] **Step 2: 写基线 sentinel 测试(gate 不误伤正常请求 + 现有 provenance 基础字段齐)**

创建文件,import 全部放顶部:

```python
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_CFG = RuntimeConfig(mode=Mode.OFFLINE)
_ACCEPT = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}


def test_baseline_accept_report_healthy():
    """接线前提坐实:正常 accept 请求 abstain=False + provenance 基础字段齐。
    接线后三 gate 设计为对一致/正常请求不触发,本断言仍须成立(gate 不误伤)。"""
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    assert sr["abstain"] is False
    prov = sr["provenance"]
    for f in ("rules_referenced", "models_used", "n_messages"):
        assert f in prov, f"provenance 缺基础字段 {f}"
```

- [ ] **Step 3: 跑测试确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py -p no:cacheprovider -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py
git commit -m "test(phase10c2): Task 0 基线坐实 —— accept 报告健康 + provenance 基础字段齐(gate 不误伤前提)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 1: per-call hash 基础设施 + 全 predictor 接线

**Files:**
- Create: `praxis_virtualcell/governance/provenance_hash.py`
- Modify: `praxis_virtualcell/predictors/base.py`
- Modify: `praxis_virtualcell/predictors/mock_linear.py`, `mock_cpa.py`, `mock_gears.py`, `case_runner_agent.py`
- Modify: `praxis_virtualcell/agents/provenance_agent.py`
- Test: `praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py`

- [ ] **Step 1: 写 provenance_hash 单元测试**

追加到测试文件(import 放顶部):

```python
from praxis_virtualcell.governance.provenance_hash import (
    compute_call_provenance, check_call_provenance)


def test_compute_call_provenance_deterministic():
    a = compute_call_provenance("MockLinear", "mock:MockLinear", {"targets": ["AHR"]},
                                {"delta": [0.0]}, ["mock"])
    b = compute_call_provenance("MockLinear", "mock:MockLinear", {"targets": ["AHR"]},
                                {"delta": [0.0]}, ["mock"])
    assert a == b                                  # 同输入同 hash(确定性)
    assert set(a) == {"model_name", "model_version", "input_hash", "output_hash", "evidence_source"}
    assert a["model_name"] == "MockLinear"
    assert a["model_version"] == "mock:MockLinear"
    assert len(a["input_hash"]) == 64 and len(a["output_hash"]) == 64


def test_compute_call_provenance_input_sensitive():
    a = compute_call_provenance("X", "v1", {"targets": ["AHR"]}, {"delta": [0.1]}, [])
    b = compute_call_provenance("X", "v1", {"targets": ["TP53"]}, {"delta": [0.1]}, [])
    assert a["input_hash"] != b["input_hash"]      # 不同输入不同 hash


def test_check_call_provenance_complete_and_missing():
    ok = compute_call_provenance("X", "v1", {"a": 1}, {"b": 2}, [])
    assert check_call_provenance(ok) == []                       # 完整
    assert "model_version" in check_call_provenance({**ok, "model_version": None})
    assert "model_name" in check_call_provenance({})             # 全缺
    assert check_call_provenance("not_a_dict") == ["model_name", "model_version",
                                                   "input_hash", "output_hash"]
```

- [ ] **Step 2: 跑测试确认 FAIL(模块不存在)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py -p no:cacheprovider -k provenance -v`
Expected: FAIL(ModuleNotFoundError: provenance_hash)

- [ ] **Step 3: 实现 provenance_hash.py**

```python
"""per-call provenance hash:给每个 model call 记 name/version/input-hash/output-hash/evidence,
并校验完整性(Gate A 用)。确定性 canonical sha256,无 LLM。"""
from __future__ import annotations

import hashlib
import json

_REQUIRED = ("model_name", "model_version", "input_hash", "output_hash")


def _canon_sha256(obj) -> str:
    """canonical json sha256(与 runtime.py trace_id 同模式,确定性)。"""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def compute_call_provenance(model_name: str, model_version: str | None,
                            model_input, output, evidence) -> dict:
    """产 per_call 记录。input/output 走 canonical sha256(确定性)。"""
    return {
        "model_name": model_name,
        "model_version": model_version,
        "input_hash": _canon_sha256(model_input),
        "output_hash": _canon_sha256(output),
        "evidence_source": list(evidence) if evidence else [],
    }


def check_call_provenance(per_call) -> list[str]:
    """返回缺失/为空的必需键清单(空=完整)。非 dict → 全部缺。"""
    if not isinstance(per_call, dict):
        return list(_REQUIRED)
    return [k for k in _REQUIRED if not per_call.get(k)]
```

- [ ] **Step 4: 跑测试确认 PASS**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py -p no:cacheprovider -k provenance -v`
Expected: 4 PASS

- [ ] **Step 5: 给 base.py 加 model_version 属性 + handle 三分支补 per_call**

修改 `praxis_virtualcell/predictors/base.py`:顶部 import 加 `from praxis_virtualcell.governance.provenance_hash import compute_call_provenance`;类加 `model_version: str | None = None`;加 helper + 改 handle(prepare_input 提到 try 外):

```python
    model_version: str | None = None

    def _call_version(self, out: dict) -> str | None:
        """per_call model_version:优先引擎动态 version(run_prediction 产出),否则类属性。"""
        return (out.get("provenance") or {}).get("model_version") or self.model_version
```

handle 改为(保留现有 retrieve-before-predict 门 + 状态逻辑,仅在每个 _emit 的 provenance 里 merge per_call):

```python
    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        if not bus.has_message_type("brain_retrieved"):
            raise RetrieveBeforePredictError(
                f"{self.name} 在 brain 检索前被调用(retrieve-before-predict 门)")
        req = message.payload["request"]
        bc = message.payload["brain_context"]
        score, reject = self.assess_applicability(req, bc)
        if reject is not None:
            pc = compute_call_provenance(self.name, self.model_version, {}, None, [reject])
            self._emit(bus, message, PredictorResultMessage(
                agent_name=self.name, status="rejected", prediction=None, uncertainty=None,
                applicability_score=score, evidence=[reject], rejection_reason=reject,
                provenance={"rules": bc.get("rules_referenced", []), "per_call": pc}))
            return
        model_input = self.prepare_input(req, bc)
        try:
            out = self.run_prediction(model_input)
        except Exception as e:  # noqa: BLE001 — mock 阶段把异常归为 failed
            pc = compute_call_provenance(self.name, self.model_version, model_input, None, [])
            self._emit(bus, message, PredictorResultMessage(
                agent_name=self.name, status="failed", prediction=None, uncertainty=None,
                applicability_score=score, evidence=[], rejection_reason=None,
                provenance={"error": str(e), "per_call": pc}))
            return
        status, reject_reason = self._result_status(out)
        version = self._call_version(out)
        if status != "success":
            pc = compute_call_provenance(self.name, version, model_input, None,
                                         out.get("evidence", []))
            self._emit(bus, message, PredictorResultMessage(
                agent_name=self.name, status=status, prediction=None,
                uncertainty=out.get("uncertainty"), applicability_score=score,
                evidence=out.get("evidence", []), rejection_reason=reject_reason,
                provenance={**out.get("provenance", {}), "per_call": pc}))
            return
        pc = compute_call_provenance(self.name, version, model_input, out["prediction"],
                                     out.get("evidence", []))
        self._emit(bus, message, PredictorResultMessage(
            agent_name=self.name, status="success", prediction=out["prediction"],
            uncertainty=out.get("uncertainty"), applicability_score=score,
            evidence=out.get("evidence", []), rejection_reason=None,
            provenance={**out.get("provenance", {}), "per_call": pc}))
```

**注**:`prepare_input` 提到 try 外(现有 mock/CaseRunner 实现都是简单 dict 构造不抛异常);若某 predictor 的 prepare_input 抛异常,原先归 failed、现直接 propagate —— 现状无此实现,不引入回归。

- [ ] **Step 6: 各 predictor 声明 model_version**

`mock_linear.py`:类内加 `model_version = "mock:MockLinear"`;`mock_cpa.py`:`model_version = "mock:MockCPA"`;`mock_gears.py`:`model_version = "mock:MockGEARS"`。

`case_runner_agent.py`:`run_prediction` 的 return provenance 加 `"model_version": engine`:

```python
            "provenance": {**report.provenance_boundary, "case_id": report.case_id,
                           "engine": engine, "model_version": engine},
```

- [ ] **Step 7: ProvenanceAgent 汇总 per_call_hashes**

修改 `praxis_virtualcell/agents/provenance_agent.py`:在 provenance dict 里加一键(读透传的 `p["results"]`,不碰现有 11 字段):

```python
            # C2:per-call hash 汇总(每个 result 的 per_call → {agent_name: per_call})。
            # 只汇总,不裁决;供 Gate A 校验 models_used 完整性。
            "per_call_hashes": {r.get("agent_name"): (r.get("provenance") or {}).get("per_call")
                                for r in p.get("results", [])
                                if (r.get("provenance") or {}).get("per_call")},
```

- [ ] **Step 8: 写接线测试(per_call 进 report + 确定性字节等价保留)**

追加(import run_query/_CFG/_ACCEPT 已在顶部):

```python
def test_per_call_hashes_in_report_for_used_models():
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    pch = sr["provenance"]["per_call_hashes"]
    assert sr["models_used"], "accept 请求应有 models_used"
    for name in sr["models_used"]:
        assert name in pch, f"{name} 缺 per_call_hashes"
        pc = pch[name]
        assert pc["model_name"] == name
        assert pc["model_version"]                      # 非空(mock: 或 engine)
        assert len(pc["input_hash"]) == 64 and len(pc["output_hash"]) == 64


def test_per_call_hash_offline_byte_equal_rerun():
    import hashlib
    import json
    def _h(o): return hashlib.sha256(
        json.dumps(o, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    outs = [run_query(dict(_ACCEPT), config=_CFG)["structured_report"] for _ in range(3)]
    assert len({_h(o) for o in outs}) == 1, "per_call hash 后 structured_report 三跑仍须字节等价"
```

- [ ] **Step 9: 跑 C2 测试 + 全量回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py -p no:cacheprovider -v`
Expected: 全 PASS
Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider -q`
Expected: 全绿(passed 数 ≥ 784 + 新增;0 failed)。若既有测试因 per_call 新增而 fail(如深比 provenance dict),报告控制器判定(spec §2 勘察预期无此类,但需实证)。

- [ ] **Step 10: ruff + Commit**

Run: `.venv/bin/ruff check praxis_virtualcell/governance/provenance_hash.py praxis_virtualcell/predictors/base.py praxis_virtualcell/agents/provenance_agent.py praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py`
Expected: All checks passed

```bash
git add praxis_virtualcell/governance/provenance_hash.py praxis_virtualcell/predictors/base.py \
  praxis_virtualcell/predictors/mock_linear.py praxis_virtualcell/predictors/mock_cpa.py \
  praxis_virtualcell/predictors/mock_gears.py praxis_virtualcell/predictors/case_runner_agent.py \
  praxis_virtualcell/agents/provenance_agent.py \
  praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py
git commit -m "feat(phase10c2): Task 1 per-call hash 基础设施 —— 全 predictor 记 name/version/input/output hash + ProvenanceAgent 汇总(纯增量,确定性字节等价保留)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Gate A — per-call hash 完整性 fail-closed + gate_util helper

**Files:**
- Create: `praxis_virtualcell/governance/gate_util.py`
- Modify: `praxis_virtualcell/core/runtime.py`(后处理段,C1 gate 之后)
- Test: `praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py`

- [ ] **Step 1: 写 gate_util 单元测试**

追加(import 顶部):

```python
from praxis_virtualcell.governance.gate_util import apply_governance_gate


def test_apply_gate_overrides_when_not_already_abstain():
    rep = {"abstain": False, "prediction": {"delta": [0.1]}, "provenance": {}}
    gated = apply_governance_gate(rep, "some_reason", "some_gate", {"detail": 1})
    assert gated is True
    assert rep["abstain"] is True and rep["prediction"] is None
    assert "some_reason" in rep["abstain_reasons"]
    g = rep["provenance"]["some_gate"]
    assert g["gate_abstained"] is True and g["reliability_original_abstain"] is False
    assert g["detail"] == 1


def test_apply_gate_records_but_no_override_when_already_abstain():
    rep = {"abstain": True, "prediction": None, "provenance": {}}
    gated = apply_governance_gate(rep, "r", "g", {})
    assert gated is False                                  # 原已 abstain,不重复 override
    assert rep["provenance"]["g"]["gate_abstained"] is False
    assert rep["provenance"]["g"]["reliability_original_abstain"] is True
```

- [ ] **Step 2: 跑测试确认 FAIL**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py -p no:cacheprovider -k apply_gate -v`
Expected: FAIL(ModuleNotFoundError: gate_util)

- [ ] **Step 3: 实现 gate_util.py**

```python
"""三个 C2 governance gate 共用的 override helper。C1 gate 保持内联不动。
一致原则(同 C1):只 override report 对外 abstain/prediction/abstain_reasons,原判记 provenance
供审计;reliability/critic 裁决数值不经此路径(gate 只读已组装 report)。确定性,无 LLM。"""
from __future__ import annotations


def apply_governance_gate(report: dict, reason: str, prov_key: str, detail: dict) -> bool:
    """gate 命中时调用。返回是否真触发了 override(原未 abstain → True)。
    - 原未 abstain:override 对外 abstain=True/prediction=None/abstain_reasons+=reason。
    - 原已 abstain:不重复 override,仅记 provenance(gate_abstained=False)。
    两种情况都记 provenance[prov_key](detail + gate_abstained + reliability_original_abstain)。"""
    original = report.get("abstain", False)
    gated = not original
    if gated:
        report["abstain"] = True
        report["prediction"] = None
        report.setdefault("abstain_reasons", []).append(reason)
    report.setdefault("provenance", {})[prov_key] = {
        **detail, "gate_abstained": gated, "reliability_original_abstain": original}
    return gated
```

- [ ] **Step 4: 跑测试确认 PASS**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py -p no:cacheprovider -k apply_gate -v`
Expected: 2 PASS

- [ ] **Step 5: 写 Gate A 端到端测试(缺 hash → abstain;完整 → 零 override)**

追加:

```python
def test_gate_a_healthy_report_no_override():
    """正常 accept 请求 per_call 完整 → Gate A 不触发(无 provenance_hash_gate 键 / abstain 不变)。"""
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    assert sr["abstain"] is False
    assert "provenance_hash_gate" not in sr["provenance"] or \
        sr["provenance"]["provenance_hash_gate"]["gate_abstained"] is False


def test_gate_a_triggers_on_incomplete_call_provenance(monkeypatch):
    """monkeypatch ProvenanceAgent 使某 used model 的 per_call 缺 version → Gate A fail-closed abstain。"""
    from praxis_virtualcell.governance import provenance_hash as PH
    orig = PH.compute_call_provenance

    def broken(name, version, mi, out, ev):
        pc = orig(name, version, mi, out, ev)
        pc["model_version"] = None                        # 制造缺失
        return pc
    monkeypatch.setattr("praxis_virtualcell.predictors.base.compute_call_provenance", broken)
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    assert sr["abstain"] is True
    assert "incomplete_call_provenance" in sr["abstain_reasons"]
    g = sr["provenance"]["provenance_hash_gate"]
    assert g["gate_abstained"] is True and g["missing"]
```

- [ ] **Step 6: 跑测试确认 FAIL(gate 未接线)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py -p no:cacheprovider -k gate_a -v`
Expected: `test_gate_a_triggers...` FAIL(abstain 仍 False)

- [ ] **Step 7: 接 Gate A 进 runtime.py**

顶部 import 加 `from praxis_virtualcell.governance.gate_util import apply_governance_gate` 和 `from praxis_virtualcell.governance.provenance_hash import check_call_provenance`。在 C1 gate 块(`if module_plan is not None:` ... `check_module_plan` 块)**之后**、`if llm_cross_module is not None:` 之前插入:

```python
        # P10.C2 Gate A:per-call hash 完整性 fail-closed。models_used 的 per_call 缺
        # name/version/input_hash/output_hash 任一 → 对外 abstain(reliability 裁决数值不变)。
        pch = report.get("provenance", {}).get("per_call_hashes", {})
        hash_missing = {n: miss for n in report.get("models_used", [])
                        if (miss := check_call_provenance(pch.get(n, {})))}
        if hash_missing:
            apply_governance_gate(report, "incomplete_call_provenance",
                                  "provenance_hash_gate", {"missing": hash_missing})
```

- [ ] **Step 8: 跑 gate_a 测试 + 全量回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py -p no:cacheprovider -v`
Expected: 全 PASS
Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider -q`
Expected: 全绿(0 failed)

- [ ] **Step 9: ruff + Commit**

Run: `.venv/bin/ruff check praxis_virtualcell/governance/gate_util.py praxis_virtualcell/core/runtime.py praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py`

```bash
git add praxis_virtualcell/governance/gate_util.py praxis_virtualcell/core/runtime.py \
  praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py
git commit -m "feat(phase10c2): Task 2 Gate A per-call hash 完整性 fail-closed —— models_used 缺 hash 字段真触发对外 abstain(gate_util helper,reliability 数值不变)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Gate B — provenance 完整性硬门(防御性类不变量)

**Files:**
- Create: `praxis_virtualcell/governance/provenance_completeness.py`
- Modify: `praxis_virtualcell/core/runtime.py`(Gate A 之后)
- Test: `praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py`

- [ ] **Step 1: 写 check_report_provenance 单元测试**

追加(import 顶部):

```python
from praxis_virtualcell.governance.provenance_completeness import check_report_provenance


def test_check_report_provenance_complete():
    rep = {"models_used": [], "models_rejected": [], "reliability": "low",
           "provenance": {"n_messages": 3, "rules_referenced": [], "models_used": []}}
    assert check_report_provenance(rep) == []


def test_check_report_provenance_missing_top_and_prov_keys():
    rep = {"models_used": [], "provenance": {"n_messages": 3}}
    miss = check_report_provenance(rep)
    assert "models_rejected" in miss and "reliability" in miss
    assert "provenance.rules_referenced" in miss and "provenance.models_used" in miss


def test_check_report_provenance_provenance_not_dict():
    assert "provenance" in check_report_provenance({"models_used": [], "models_rejected": [],
                                                    "reliability": "low", "provenance": None})
```

- [ ] **Step 2: 跑测试确认 FAIL**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py -p no:cacheprovider -k report_provenance -v`
Expected: FAIL(ModuleNotFoundError)

- [ ] **Step 3: 实现 provenance_completeness.py**

```python
"""report 级 provenance 完整性契约(Gate B)。防御性类不变量:现状字段恒由代码构造,
罕触发;作 fail-closed 断言防未来重构漏挂。非'多模块结果比对',非高频缺失检测。"""
from __future__ import annotations

_TOP_REQUIRED = ("models_used", "models_rejected", "reliability", "provenance")
_PROV_REQUIRED = ("n_messages", "rules_referenced", "models_used")


def check_report_provenance(report: dict) -> list[str]:
    """返回缺失/非法的必需键清单(空=完整)。顶层键须存在;provenance 须为 dict 且含子键。"""
    missing = [k for k in _TOP_REQUIRED if k not in report]
    prov = report.get("provenance")
    if not isinstance(prov, dict):
        if "provenance" not in missing:
            missing.append("provenance")
        return missing
    missing.extend(f"provenance.{k}" for k in _PROV_REQUIRED if k not in prov)
    return missing
```

- [ ] **Step 4: 跑测试确认 PASS**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py -p no:cacheprovider -k report_provenance -v`
Expected: 3 PASS

- [ ] **Step 5: 写 Gate B 端到端测试(正常不触发 = 活体验证防御 gate)**

追加:

```python
def test_gate_b_healthy_report_no_trigger():
    """活体验证:正常请求 provenance 契约完整 → Gate B 不触发(防御性 gate 罕触发的诚实证明)。"""
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    assert "provenance_completeness_gate" not in sr["provenance"] or \
        sr["provenance"]["provenance_completeness_gate"]["gate_abstained"] is False
    assert sr["abstain"] is False
```

- [ ] **Step 6: 跑测试确认 PASS(Gate B 未接线但正常请求本就完整,断言成立)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py -p no:cacheprovider -k gate_b -v`
Expected: PASS(此测试接线前后都应 PASS)

- [ ] **Step 7: 接 Gate B 进 runtime.py(Gate A 之后)**

顶部 import 加 `from praxis_virtualcell.governance.provenance_completeness import check_report_provenance`。在 Gate A 块之后插入:

```python
        # P10.C2 Gate B:provenance 完整性硬门(防御性类不变量,罕触发)。必需契约缺键 →
        # fail-closed 对外 abstain。字段恒由代码构造,正常不触发;防未来重构漏挂。
        prov_missing = check_report_provenance(report)
        if prov_missing:
            apply_governance_gate(report, "incomplete_provenance",
                                  "provenance_completeness_gate", {"missing": prov_missing})
```

- [ ] **Step 8: 全量回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider -q`
Expected: 全绿(0 failed)。**特别确认现有 abstain 请求(如 bacteria b0720)不被 Gate B 误触发**(其 report 仍有 models_used/models_rejected/reliability/provenance 基础字段)。

- [ ] **Step 9: ruff + Commit**

Run: `.venv/bin/ruff check praxis_virtualcell/governance/provenance_completeness.py praxis_virtualcell/core/runtime.py praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py`

```bash
git add praxis_virtualcell/governance/provenance_completeness.py praxis_virtualcell/core/runtime.py \
  praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py
git commit -m "feat(phase10c2): Task 3 Gate B provenance 完整性硬门 —— 防御性类不变量 fail-closed(缺必需契约键触发 abstain,活体验证正常请求不误伤)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Gate C — cell_type 越界 abstain

**Files:**
- Create: `praxis_virtualcell/governance/cell_type_domain.py`
- Modify: `praxis_virtualcell/core/runtime.py`(Gate B 之后)
- Test: `praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py`

- [ ] **Step 1: 写 check_cell_type_domain 单元测试**

追加(import 顶部):

```python
from praxis_virtualcell.governance.cell_type_domain import check_cell_type_domain

_APPMAP = {"MockGEARS": {"supported_cell_types": ["K562", "A549"]},
           "MockCPA": {"supported_cell_types": ["K562"]},
           "NoDeclare": {}}                                    # 无声明


def test_cell_type_domain_all_out_of_domain():
    bc = {"model_applicability": _APPMAP}
    req = {"cell_type": "HeLa"}
    assert check_cell_type_domain(req, bc, ["MockGEARS", "MockCPA"]) == ["MockGEARS", "MockCPA"]


def test_cell_type_domain_in_domain_no_violation():
    bc = {"model_applicability": _APPMAP}
    assert check_cell_type_domain({"cell_type": "K562"}, bc, ["MockGEARS", "MockCPA"]) == []


def test_cell_type_domain_partial_declare_no_trigger():
    """有 predictor 无声明 supported_cell_types → 不判越界(窄门,同 reliability 语义)。"""
    bc = {"model_applicability": _APPMAP}
    # NoDeclare 无声明 → declaring 只含 MockGEARS;若 MockGEARS 越界但 NoDeclare 未声明,
    # declaring 全越界仍触发?按 reliability 判据:declaring=[MockGEARS],全越界 → 触发。
    assert check_cell_type_domain({"cell_type": "HeLa"}, bc, ["MockGEARS", "NoDeclare"]) == ["MockGEARS"]


def test_cell_type_domain_no_cell_type_or_no_used():
    bc = {"model_applicability": _APPMAP}
    assert check_cell_type_domain({}, bc, ["MockGEARS"]) == []          # 无 cell_type
    assert check_cell_type_domain({"cell_type": "HeLa"}, bc, []) == []  # 无 used
    assert check_cell_type_domain({"cell_type": "HeLa"}, {}, ["MockGEARS"]) == []  # 无 appmap
```

- [ ] **Step 2: 跑测试确认 FAIL**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py -p no:cacheprovider -k cell_type_domain -v`
Expected: FAIL(ModuleNotFoundError)

- [ ] **Step 3: 实现 cell_type_domain.py(独立复用 reliability.py:113-118 判据)**

```python
"""cell_type 越界判据(Gate C)。独立复用 reliability.py 的 declaring/unsupported 逻辑
(不 import reliability,避免耦合裁决路径)。窄门:仅'有声明 supported_cell_types 的 used
predictor 且全部越界'才判 violation —— 与 reliability downgrade 同源,避免误伤无声明 predictor。
Gate C 在 reliability 已有 downgrade 之上叠加'全越界→对外 abstain';reliability 数值不变。"""
from __future__ import annotations


def check_cell_type_domain(request: dict, brain_context: dict, models_used: list) -> list[str]:
    """返回越界(声明了 supported_cell_types 且 req cell_type 不在其中)的 used predictor 清单。
    空 = 不触发(无 cell_type / 无 used / 无声明 / 在库 / 部分声明未全越界)。"""
    req_ct = request.get("cell_type")
    if not req_ct or not models_used:
        return []
    appmap = brain_context.get("model_applicability") or {}
    declaring = [n for n in models_used
                 if appmap.get(n, {}).get("supported_cell_types") is not None]
    unsupported = [n for n in declaring if req_ct not in appmap[n]["supported_cell_types"]]
    if declaring and len(unsupported) == len(declaring):
        return unsupported
    return []
```

- [ ] **Step 4: 跑测试确认 PASS**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py -p no:cacheprovider -k cell_type_domain -v`
Expected: 4 PASS

- [ ] **Step 5: 写 Gate C 端到端测试(越界 cell_type → abstain)**

追加。需构造一个 human gene 请求带越界 cell_type,且 used predictor 声明 supported_cell_types。参考 `test_week6_reliability_critic.py` 现有 cell_type 用例的请求形态:

```python
def test_gate_c_out_of_domain_cell_type_abstains():
    """human gene 请求 + 越界 cell_type(如 HeLa,不在任何声明的 supported_cell_types)→
    若所有 used predictor 都声明且全越界 → Gate C 对外 abstain。"""
    req = dict(_ACCEPT)
    req["cell_type"] = "HeLa_out_of_domain"
    out = run_query(req, config=_CFG)
    sr = out["structured_report"]
    # 断言:若 used predictor 有声明 supported_cell_types(model_applicability.yaml 里 gene KO
    # predictor 声明了 K562/A549/...),HeLa 越界 → Gate C 触发
    if sr["provenance"].get("cell_type_gate", {}).get("gate_abstained"):
        assert sr["abstain"] is True
        assert "cell_type_out_of_domain" in sr["abstain_reasons"]
    # 反向:cell_type 在库(K562)→ 不触发
    req2 = dict(_ACCEPT); req2["cell_type"] = "K562"
    sr2 = run_query(req2, config=_CFG)["structured_report"]
    assert sr2["provenance"].get("cell_type_gate", {}).get("gate_abstained", False) is False
```

**注**:implementer 须先跑 `_ACCEPT` + 越界 cell_type 确认真有 used predictor 声明 supported_cell_types(否则 declaring 空、Gate C 不触发,测试变 vacuous)。若 `_ACCEPT` 的 used predictor(mock)未在 model_applicability.yaml 声明,改用 `test_week6_reliability_critic.py` 里能触发 downgrade:cell_type 的请求形态(那里已验证 declaring 非空)。**这是 Task 4 的实证前提,先坐实再写断言。**

- [ ] **Step 6: 接 Gate C 进 runtime.py(Gate B 之后)**

顶部 import 加 `from praxis_virtualcell.governance.cell_type_domain import check_cell_type_domain`。runtime 后处理段能拿到 request 与 brain_context:从 `app.payload`(`app.payload["request"]` / `app.payload["brain_context"]`)。在 Gate B 块之后插入:

```python
        # P10.C2 Gate C:cell_type 越界 abstain。全部被采纳 predictor 声明 supported_cell_types
        # 且 req cell_type 全越界 → 对外 abstain。reliability 的 downgrade:cell_type 数值语义保留,
        # Gate C 只叠加对外 abstain(不改 reliability)。
        ct_violations = check_cell_type_domain(
            app.payload["request"], app.payload["brain_context"], report.get("models_used", []))
        if ct_violations:
            apply_governance_gate(report, "cell_type_out_of_domain",
                                  "cell_type_gate", {"out_of_domain_predictors": ct_violations})
```

- [ ] **Step 7: 跑 gate_c 测试 + 全量回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py -p no:cacheprovider -v`
Expected: 全 PASS
Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider -q`
Expected: 全绿。**特别确认现有 test_week6_reliability_critic cell_type downgrade 用例仍 PASS**(reliability downgrade 数值语义未变;若那些用例的 used predictor 全越界现在被 Gate C 升级成 abstain,需报告控制器判定是否符合预期——downgrade 用例可能预期 abstain=False,Gate C 会改成 True)。**这是关键接缝,implementer 必须实证并报告。**

- [ ] **Step 8: ruff + Commit**

Run: `.venv/bin/ruff check praxis_virtualcell/governance/cell_type_domain.py praxis_virtualcell/core/runtime.py praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py`

```bash
git add praxis_virtualcell/governance/cell_type_domain.py praxis_virtualcell/core/runtime.py \
  praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py
git commit -m "feat(phase10c2): Task 4 Gate C cell_type 越界 abstain —— 全越界升级对外 abstain(独立复用 reliability 判据,downgrade 数值语义保留)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: 多 gate 交互 + 裁决数值不变红线 + 确定性收尾

**Files:**
- Test: `praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py`

- [ ] **Step 1: 写裁决数值不变红线测试**

追加。gate 触发 abstain 时,reliability 提取字段(reliability/failed_checks/model_disagreement)须与"gate 不触发时同请求"一致(gate 不改裁决数值,只 override 对外 abstain)。用 Gate A monkeypatch 触发:

```python
def test_c2_gate_preserves_reliability_numeric_fields(monkeypatch):
    """Gate 触发 abstain 后,reliability 提取字段(reliability/failed_checks/model_disagreement)
    与接线前捕获值一致 —— gate 只 override 对外,不改裁决数值(红线)。"""
    base = run_query(dict(_ACCEPT), config=_CFG)["structured_report"]
    base_fields = {k: base.get(k) for k in ("reliability", "failed_checks", "model_disagreement")}
    from praxis_virtualcell.governance import provenance_hash as PH
    orig = PH.compute_call_provenance
    def broken(name, version, mi, out, ev):
        pc = orig(name, version, mi, out, ev); pc["input_hash"] = None; return pc
    monkeypatch.setattr("praxis_virtualcell.predictors.base.compute_call_provenance", broken)
    gated = run_query(dict(_ACCEPT), config=_CFG)["structured_report"]
    assert gated["abstain"] is True                          # gate 触发
    for k, v in base_fields.items():
        assert gated.get(k) == v, f"{k} 被 gate 改动(违红线):{v} -> {gated.get(k)}"
```

- [ ] **Step 2: 写多 gate 交互测试(reasons 累加 + provenance 键独立)**

追加。同时触发 Gate A(monkeypatch 缺 hash)与 Gate C(越界 cell_type):

```python
def test_multi_gate_reasons_accumulate_and_keys_independent(monkeypatch):
    from praxis_virtualcell.governance import provenance_hash as PH
    orig = PH.compute_call_provenance
    def broken(name, version, mi, out, ev):
        pc = orig(name, version, mi, out, ev); pc["output_hash"] = None; return pc
    monkeypatch.setattr("praxis_virtualcell.predictors.base.compute_call_provenance", broken)
    req = dict(_ACCEPT); req["cell_type"] = "HeLa_out_of_domain"
    sr = run_query(req, config=_CFG)["structured_report"]
    assert sr["abstain"] is True
    # Gate A 一定触发;abstain_reasons 至少含 incomplete_call_provenance
    assert "incomplete_call_provenance" in sr["abstain_reasons"]
    # 各 gate provenance 键独立存在(互不覆盖)
    assert "provenance_hash_gate" in sr["provenance"]
    # 首个触发 gate override 后,后续 gate reliability_original_abstain=True(不重复 override)
    if "cell_type_gate" in sr["provenance"]:
        assert sr["provenance"]["cell_type_gate"]["reliability_original_abstain"] is True
```

- [ ] **Step 3: 写确定性 + llm_used_for_prediction 恒 false 测试**

追加:

```python
def test_c2_deterministic_no_llm():
    out = run_query(dict(_ACCEPT), config=_CFG)
    sr = out["structured_report"]
    prov = sr["provenance"]
    # 若有 llm_used_for_prediction 字段须恒 False(OFFLINE 全程无 LLM 参与预测)
    assert prov.get("llm_used_for_prediction", False) is False
```

**注**:若现有 report/provenance 无 `llm_used_for_prediction` 键,改断言现有等价的 OFFLINE 无 LLM 不变量(参考 C1 的 `test_c1_llm` 写法,implementer 先查现有键名对齐)。

- [ ] **Step 4: 跑全部 C2 测试**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py -p no:cacheprovider -v`
Expected: 全 PASS

- [ ] **Step 5: 全量回归 + 确定性双跑**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider -q`
Expected: 全绿(0 failed),记录最终 passed/skipped 数。
Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_1_runtime_determinism.py -p no:cacheprovider -v`
Expected: `test_offline_rerun_byte_equal` 仍 PASS(C2 后确定性不破)

- [ ] **Step 6: ruff + Commit**

Run: `.venv/bin/ruff check praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py`

```bash
git add praxis_virtualcell/tests/phase10/test_t10_4_provenance_gates.py
git commit -m "test(phase10c2): Task 5 多 gate 交互 + 裁决数值不变红线 + 确定性收尾 —— reasons 累加/provenance 键独立/reliability 数值不改/llm 恒 false + 全量回归绿

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review(计划对 spec 的覆盖核对)

**1. Spec 覆盖**:
- spec §3 per-call hash 基础设施 → Task 1 ✓
- spec §4.1 Gate A → Task 2 ✓
- spec §4.2 Gate B → Task 3 ✓
- spec §4.3 Gate C → Task 4 ✓
- spec §4.4 多 gate 交互 + 下游一致性 → Task 5 ✓
- spec §5 Task 0 基线 → Task 0 ✓
- spec §7 裁决数值不变红线 + 确定性 → Task 5 ✓

**2. 占位符扫描**:每步含实际测试/实现代码 + 精确命令。Task 4 Step 5/7 明标"implementer 须实证 cell_type 触发前提 + 报告 downgrade 用例接缝"——非占位符,是 spec §5 风险 3/4 要求的实证门。

**3. 类型/命名一致性**:`compute_call_provenance`/`check_call_provenance`(provenance_hash)、`apply_governance_gate`(gate_util)、`check_report_provenance`(provenance_completeness)、`check_cell_type_domain`(cell_type_domain)全程一致;provenance 键 `per_call_hashes`/`provenance_hash_gate`/`provenance_completeness_gate`/`cell_type_gate` 全程一致;abstain_reasons `incomplete_call_provenance`/`incomplete_provenance`/`cell_type_out_of_domain` 全程一致。

**4. 关键接缝(收官前 opus final review 必查)**:
- Task 1 per_call 无条件加会否破坏现有深比 report 的测试(spec §2 勘察预期无,Task 1 Step 9 实证)。
- Task 4 Gate C 会否把现有 cell_type downgrade 用例升级成 abstain(Task 4 Step 7 实证 + 报告控制器判定)。
- 多 gate override 顺序(C1→A→B→C)下 reliability_original_abstain 各 gate 各自捕获的正确性(Task 5 Step 2)。
