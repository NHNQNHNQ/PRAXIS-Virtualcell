# P10.C1 跨模块一致性治理(诚实窄门版)实现 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: 用 superpowers:subagent-driven-development 逐 task 执行(每 task fresh implementer[sonnet] + spec 合规审 + 代码质量审两审)。收官前控制器做 opus final review。步骤用 checkbox 跟踪。

**Goal:** 把死码 `governance/module_consistency.py::check_module_plan` 接进 `core/runtime.py` 后处理阶段,module_plan 内部一致(绝大多数正常流程)时零动作保字节等价,检出严重不一致时经 governance gate 真触发对外 abstain(reliability/critic 裁决零改)。

**Architecture:** runtime 在 report 组装后的后处理段(module_plan+report 信号全齐处)调 `check_module_plan(module_plan)`;violations 为空→零动作(不加 provenance、字节等价);非空→记录 `provenance.cross_module_consistency` + 若 reliability 原未 abstain 则 override report 对外 `abstain`/`prediction`/`abstain_reasons`(reliability 提取字段与所有裁决数值原样保留,原 abstain 记 provenance 供审计)。确定性、无 LLM。

**Tech Stack:** Python;既有 `governance/module_consistency.check_module_plan`(纯函数,不改其 4 规则);`core/runtime.py` 后处理段;`workflows/run_virtualcell_query.run_query`;pytest。

---

## 权威依据(spec)
`docs/superpowers/specs/2026-07-11-phase10c1-cross-module-consistency-design.md`(commit 2b0c3fd,用户已批准)。核心红线:reliability/critic 裁决逻辑与数值零改;check_module_plan 4 规则不改;OFFLINE 一致场景字节等价;无 LLM;方向/时间尺度/细胞背景/证据强度对如实 limitation。

## 勘察坐实的现状(写 plan 前已核对)
- `core/runtime.py:104-137` 后处理段:`report = rep.payload["report"]`(:105),`if module_plan is not None: report.setdefault("provenance", {})["module_plan"] = module_plan`(:108-109),后续挂 evidence_level/learning_queue/llm_*,`return report`(:137)。**C1 gate 插在 :109 之后**。
- `agents/report.py:18-34` report 顶层字段:`abstain`(:20 从 rd 提取)、`prediction`(:22 None if abstain)、`abstain_reasons`(:26)、`reliability`/`model_disagreement`/`failed_checks`(reliability 产物提取)、`provenance`(:33)。**report 顶层无完整 reliability_decision 子结构**。
- `governance/module_consistency.py:24-52` `check_module_plan(plan: dict) -> list[str]`,纯确定性,返回违规字符串列表(空=一致),4 规则(verdict vs route/mismatch accept/engine 白名单/overall)。全库仅 `tests/test_module_consistency.py` 引用,主链不调用。

## File Structure
- **Modify** `praxis_virtualcell/core/runtime.py`:顶部 import `check_module_plan`;后处理段(:109 后)加 C1 gate(约 10 行)。
- **Test(新建)** `praxis_virtualcell/tests/phase10/test_t10_5_cross_module_consistency.py`:Task 0 基线 + 接线一致 + gate 触发 + 裁决数值不变 + 字节等价。
- **不改**:`governance/module_consistency.py`(只调用)、`agents/report.py`、`agents/reliability.py`、`agents/critic.py`。

---

## Task 0:基线验证 —— 现有 module_plan 全部无违规(接线前提)

**Files:** Test 新建 `praxis_virtualcell/tests/phase10/test_t10_5_cross_module_consistency.py`。

**目的:** 坐实"现有正常流程产的 module_plan 都 check_module_plan 无违规"。若有违规,接线会误 abstain 破坏字节等价 → **停止 BLOCKED 报告控制器**(接线前提不成立)。

- [ ] **Step 1:写基线测试**(import 全放文件顶部,防 E402)

```python
import hashlib
import json as _json

import pytest

from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.governance.module_consistency import check_module_plan
from praxis_virtualcell.workflows.run_virtualcell_query import run_query

_CFG = RuntimeConfig(mode=Mode.OFFLINE)

# 覆盖各真实/mock/advisory/abstain 路径的代表性请求(module_plan 应全部内部一致)
_BASELINE_REQS = [
    # bacteria gene KO(gem_fba 真实)
    {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b0720"],
     "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"},
    # human gene expression(donor_predictor,Mac mock)
    {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
     "input_modality": "scRNA", "output_modality": "delta_expression",
     "task_type": "predict_delta_expression"},
    # M1 膜系统 gene-set(B4 advisory,downgrade)
    {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["SLC2A1"],
     "input_modality": "scRNA", "output_modality": "delta_expression",
     "task_type": "predict_delta_expression"},
    # abstain 边界(基因不在任何模型)
    {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b9999"],
     "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"},
]


@pytest.mark.parametrize("req", _BASELINE_REQS)
def test_c1_baseline_existing_module_plans_have_no_violations(req):
    """接线前提:现有正常流程产的 module_plan 都 check_module_plan 无违规。
    若失败=接线会误 abstain 破坏字节等价 → 停止 BLOCKED(需先修 module_plan 产出)。"""
    out = run_query(dict(req), config=_CFG)
    module_plan = out["structured_report"].get("provenance", {}).get("module_plan")
    if module_plan is None:
        pytest.skip("该请求无 module_plan(abstain/不可路由),不适用一致性基线")
    violations = check_module_plan(module_plan)
    assert violations == [], f"现有 module_plan 有违规(接线前提不成立):{violations}"
```

- [ ] **Step 2:运行确认通过(坐实基线)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_5_cross_module_consistency.py -k baseline -p no:cacheprovider -v`
Expected: PASS(有 module_plan 的请求全部无违规;abstain 边界可能 skip)。**若任何 FAIL:停止,报告控制器现有 module_plan 违规详情(接线前提不成立)。**

- [ ] **Step 3:ruff + commit**

Run: `.venv/bin/ruff check praxis_virtualcell/tests/phase10/test_t10_5_cross_module_consistency.py`
```bash
git add praxis_virtualcell/tests/phase10/test_t10_5_cross_module_consistency.py
git commit -m "$(cat <<'EOF'
test(phase10c1): Task 0 基线验证 —— 现有 module_plan 全部 check_module_plan 无违规(接线前提坐实)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 1:接线 + 一致场景零动作(字节等价)

**Files:** Modify `praxis_virtualcell/core/runtime.py`;Test 追加。

- [ ] **Step 1:写一致场景测试**(追加)

```python
def test_c1_consistent_plan_zero_action_byte_equal(monkeypatch):
    """一致 module_plan(check_module_plan 返回空)→ 零动作:不 abstain、provenance 不加
    cross_module_consistency 键、report 与未接 gate 时字节完全一致(保 §6 字节等价)。"""
    from praxis_virtualcell.core import runtime as RT
    # 显式锁一致(check 返回空),排除环境干扰
    monkeypatch.setattr(RT, "check_module_plan", lambda plan: [])
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert "cross_module_consistency" not in sr.get("provenance", {})   # 一致场景无痕迹
    assert sr["abstain"] is False                                       # 未被 gate 误 abstain


def test_c1_consistent_offline_byte_equal_3runs():
    """C1 接线后,一致场景现有请求 3 跑 structured_report + trace 字节等价不变(确定性红线)。"""
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    outs = [run_query(dict(req), config=_CFG) for _ in range(3)]
    canon = lambda o: hashlib.sha256(
        _json.dumps(o, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    assert len({canon(o["structured_report"]) for o in outs}) == 1
    assert len({canon(o["trace"]) for o in outs}) == 1
```

- [ ] **Step 2:运行确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_5_cross_module_consistency.py -k "consistent" -p no:cacheprovider`
Expected: FAIL(`AttributeError: module ... has no attribute 'check_module_plan'` —— runtime 尚未 import,monkeypatch 目标不存在)。

- [ ] **Step 3:实现接线**(改 `core/runtime.py`)

顶部 import 区加(与既有 governance/agents import 同组,字母序):
```python
from praxis_virtualcell.governance.module_consistency import check_module_plan
```
在 `if module_plan is not None: report.setdefault("provenance", {})["module_plan"] = module_plan`(:108-109)**之后**加 C1 gate:
```python
        # P10.C1:跨模块一致性 governance gate。module_plan 存在时校验内部一致性(check_module_plan
        # 纯确定性 4 规则)。一致(violations 空)→ 零动作保字节等价;检出违规 → 记录 provenance +
        # 若 reliability 原未 abstain 则真触发对外 abstain(reliability/critic 裁决零改数值不变:
        # 只 override report 对外 abstain/prediction/abstain_reasons,reliability 提取字段原样保留,
        # 原 abstain 记 provenance 供审计)。确定性、无 LLM。
        if module_plan is not None:
            violations = check_module_plan(module_plan)
            if violations:
                reliability_abstain = report.get("abstain", False)   # 原判(override 前捕获)
                gate_abstained = not reliability_abstain
                if gate_abstained:
                    report["abstain"] = True
                    report["prediction"] = None
                    report.setdefault("abstain_reasons", []).append("cross_module_inconsistency")
                report.setdefault("provenance", {})["cross_module_consistency"] = {
                    "violations": violations,
                    "gate_abstained": gate_abstained,
                    "reliability_original_abstain": reliability_abstain,
                }
```

- [ ] **Step 4:运行确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_5_cross_module_consistency.py -k "consistent" -p no:cacheprovider`
Expected: PASS(一致场景零动作 + 字节等价)。

- [ ] **Step 5:全量回归(接线不破坏现有一致流程)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider`
Expected: 全 PASS(基线 774 + C1 新增,0 failed)。**若既有测试 FAIL:说明现有某 module_plan 有违规触发了 gate(接线前提不成立)→ 停止 BLOCKED 报告控制器。**

- [ ] **Step 6:ruff + commit**

```bash
.venv/bin/ruff check praxis_virtualcell/core/runtime.py praxis_virtualcell/tests/phase10/test_t10_5_cross_module_consistency.py
git add praxis_virtualcell/core/runtime.py praxis_virtualcell/tests/phase10/test_t10_5_cross_module_consistency.py
git commit -m "$(cat <<'EOF'
feat(phase10c1): Task 1 module_consistency 接进 runtime 后处理 —— 一致场景零动作保字节等价

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2:governance gate 真触发 abstain(违规场景)+ 裁决数值不变

**Files:** Test 追加(gate 逻辑 Task 1 已随接线写入,本 task 补违规场景测试 + 裁决数值不变断言)。

- [ ] **Step 1:写违规场景测试**(追加;monkeypatch check_module_plan 注入违规,不依赖真实产违规的 module_plan)

```python
def test_c1_violation_triggers_gate_abstain(monkeypatch):
    """检出违规(check_module_plan 非空)且 reliability 原未 abstain → gate 真触发对外 abstain:
    abstain=True + prediction=None + abstain_reasons 含 cross_module_inconsistency +
    provenance.cross_module_consistency 记录(gate_abstained=True + 原 abstain=False)。"""
    from praxis_virtualcell.core import runtime as RT
    monkeypatch.setattr(RT, "check_module_plan",
                        lambda plan: ["verdict_more_optimistic_than_route[test]: accept < caution"])
    # 选一个 reliability 原本不 abstain 的请求(bacteria b0720 essential → 真实 FBA 预测,不 abstain)
    req = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b0720"],
           "input_modality": "scRNA", "output_modality": "growth",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert sr["abstain"] is True                                        # gate 触发 abstain
    assert sr["prediction"] is None                                     # 预测清空
    assert "cross_module_inconsistency" in sr["abstain_reasons"]        # 原因记录
    cmc = sr["provenance"]["cross_module_consistency"]
    assert cmc["gate_abstained"] is True
    assert cmc["reliability_original_abstain"] is False                 # reliability 原判保留可审计
    assert cmc["violations"]                                            # 违规明细留痕


def test_c1_gate_preserves_reliability_numeric_fields(monkeypatch):
    """裁决数值不变红线:gate 触发时,reliability 产物数值字段(reliability/model_disagreement/
    failed_checks)与未触发 gate(同请求、check 返回空)时完全一致——gate 只改 abstain 布尔+prediction。"""
    from praxis_virtualcell.core import runtime as RT
    req = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b0720"],
           "input_modality": "scRNA", "output_modality": "growth",
           "task_type": "predict_delta_expression"}
    # 基准:check 返回空(无 gate)
    monkeypatch.setattr(RT, "check_module_plan", lambda plan: [])
    base = run_query(dict(req), config=_CFG)["structured_report"]
    # gate 触发:check 返回违规
    monkeypatch.setattr(RT, "check_module_plan", lambda plan: ["engine_out_of_whitelist[test]"])
    gated = run_query(dict(req), config=_CFG)["structured_report"]
    # reliability 产物数值字段逐一不变(裁决数值零改)
    for f in ("reliability", "model_disagreement", "failed_checks"):
        assert base.get(f) == gated.get(f), f"gate 改动了 reliability 产物字段 {f}(违裁决数值不变)"


def test_c1_violation_when_reliability_already_abstain(monkeypatch):
    """reliability 原已 abstain(如全基因不在模型)+ 违规 → gate 不重复触发(gate_abstained=False),
    但仍记录 violations 供审计;abstain 保持 True(reliability 原判)。"""
    from praxis_virtualcell.core import runtime as RT
    monkeypatch.setattr(RT, "check_module_plan", lambda plan: ["some_violation"])
    req = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b9999"],
           "input_modality": "scRNA", "output_modality": "growth",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    module_plan = sr.get("provenance", {}).get("module_plan")
    if module_plan is None:
        pytest.skip("该 abstain 请求无 module_plan(不可路由),gate 不触及")
    assert sr["abstain"] is True                                        # reliability 原判保持
    cmc = sr["provenance"]["cross_module_consistency"]
    assert cmc["gate_abstained"] is False                               # gate 未重复触发
    assert cmc["reliability_original_abstain"] is True                  # 原判 = abstain
```

- [ ] **Step 2:运行确认通过**(gate 逻辑 Task 1 已实现,本 task 测试应直接 PASS)

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_5_cross_module_consistency.py -k "violation or preserves" -p no:cacheprovider -v`
Expected: PASS(gate 触发 abstain / 裁决数值不变 / reliability 原 abstain 时不重复)。
**若 `test_c1_gate_preserves_reliability_numeric_fields` FAIL:说明 gate 改动了 reliability 产物字段 → 停止排查(违裁决数值不变红线)。**

- [ ] **Step 3:ruff + commit**

```bash
.venv/bin/ruff check praxis_virtualcell/tests/phase10/test_t10_5_cross_module_consistency.py
git add praxis_virtualcell/tests/phase10/test_t10_5_cross_module_consistency.py
git commit -m "$(cat <<'EOF'
test(phase10c1): Task 2 governance gate 真触发 abstain(违规场景)+ 裁决数值不变红线

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3:确定性 + 全量回归收尾

**Files:** Test 追加(llm_used_for_prediction 恒 false + 全量回归数确认);无源码改动。

- [ ] **Step 1:写确定性断言测试**(追加)

```python
def test_c1_llm_never_used_for_prediction():
    """C1 gate 全程确定性无 LLM:llm_used_for_prediction 恒 false(gate 触发场景亦然)。"""
    from praxis_virtualcell.core import runtime as RT
    import pytest as _pytest  # noqa: F811 — 局部确保可用(顶部已 import pytest)
    req = {"species": "bacteria", "perturbation_type": "gene", "perturbation_targets": ["b0720"],
           "input_modality": "scRNA", "output_modality": "growth",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    assert out["llm_used_for_prediction"] is False
```
(注:若 `run_query` 顶层无 `llm_used_for_prediction` 键,implementer 按实际返回结构调整断言路径——从 out 顶层或 structured_report 取,不臆造;确认该键真实存在再断言。)

- [ ] **Step 2:运行 + 全量回归**

Run(定向):`PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_5_cross_module_consistency.py -p no:cacheprovider -v` → 全 PASS。
Run(全量):`PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider` → **相较基线 774 净增 C1 测试,0 failed**;OFFLINE 一致流程字节不变。

- [ ] **Step 3:ruff + commit**

```bash
.venv/bin/ruff check praxis_virtualcell/tests/phase10/test_t10_5_cross_module_consistency.py
git add praxis_virtualcell/tests/phase10/test_t10_5_cross_module_consistency.py
git commit -m "$(cat <<'EOF'
test(phase10c1): Task 3 确定性收尾 —— C1 gate 无 LLM(llm_used_for_prediction 恒 false)+ 全量回归

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review(对照 spec)

- **spec §3 范围**:module_consistency 接线(Task 1)+ gate 真触发 abstain(Task 2)✅;limitation(方向/时间尺度/细胞背景/证据强度对)不实现、spec 已如实标注,无需 task ✅。
- **spec §4.2 接线位置**:runtime :109 后(Task 1 Step 3)✅。
- **spec §4.3 违规响应**:一致零动作(Task 1)/ 违规记录 provenance + gate override 对外 abstain、reliability 提取字段保留、原 abstain 记 provenance(Task 2)✅。
- **spec §5 Task 0 基线**:Task 0 ✅;BLOCKED 条件明确(现有 module_plan 有违规)。
- **spec §6 红线**:reliability/critic 裁决数值零改(Task 2 `test_c1_gate_preserves_reliability_numeric_fields`)✅;一致场景字节等价(Task 1 `test_c1_consistent_offline_byte_equal_3runs`)✅;无 LLM(Task 3)✅;check_module_plan 4 规则不改(只 import 调用)✅。
- **spec §7 测试**:基线/接线一致/gate 触发/裁决数值不变/字节等价/确定性 全覆盖 ✅。
- **类型一致性**:`check_module_plan(plan: dict) -> list[str]`(module_consistency 现有签名)在 runtime 调用一致;runtime gate 读写的 report 字段(abstain/prediction/abstain_reasons/provenance)与 report.py 输出结构一致;monkeypatch 目标 `RT.check_module_plan`(runtime 模块级 import 名)与实现 import 一致 ✅。
- **占位符扫描**:无 TBD;Task 3 Step 1 的 llm_used_for_prediction 键路径已注明"按实际返回结构确认",非占位而是防御性提示 ✅。
