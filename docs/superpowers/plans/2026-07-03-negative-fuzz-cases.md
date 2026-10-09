# Negative / fuzz 测试体系 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans。Steps 用 checkbox 跟踪。

**Goal:** 固化 3 层拒绝路径的声明式 negative fixtures + runner,守 KPI「无静默 accept」,与 golden 正向互补。

**Architecture:** negative yaml 按 `layer`(normalize/validate/route)声明坏输入+期望拒绝;runner 分派断言 SchemaError / schema_valid=False+错误串 / disposition≠accept。纯确定性、零 skip。

**Tech Stack:** Python / pytest 参数化 / PyYAML。

**铁律:** 只读断言现有拒绝行为,不改 normalize/validate/route 逻辑;若某路径实际不拒绝=真实 gap,停下报告不改测试迁就。每 task 全量 `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests` 0 failed 后 commit + push origin main。commit 前删 `._*`,末尾 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。

**数据契约(已 grounding):** normalize_request 抛 SchemaError;validate_candidate 返 `{schema_valid, missing_fields, errors}`(errors 如 `unsupported_species:martian`);route→RouteDecision.disposition。

---

## Task 1: negative runner + 14 用例数据(TDD)

**Files:**
- Create: `praxis_virtualcell/tests/test_negative_cases.py`
- Create: `praxis_virtualcell/tests/negative_cases/schema_rejections.yaml`
- Create: `praxis_virtualcell/tests/negative_cases/routing_rejections.yaml`

- [ ] **Step 1: 写 runner(先失败:无数据 count<12)**

写 `praxis_virtualcell/tests/test_negative_cases.py`:

```python
"""Negative / fuzz:固化 3 层拒绝路径,守 KPI「无静默 accept」。数据在 negative_cases/*.yaml。
铁律:只读断言现有拒绝行为;若某路径实际不拒绝=真实 gap,停下报告不改测试迁就。"""
from pathlib import Path

import pytest
import yaml

from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import SchemaError, normalize_request
from praxis_virtualcell.workflows.run_virtualcell_query import validate_candidate

_NEG_DIR = Path(__file__).parent / "negative_cases"


def _load_cases():
    cases = []
    for f in sorted(_NEG_DIR.glob("*.yaml")):
        if f.name.startswith("._"):
            continue
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        cases.extend(doc.get("cases", []))
    return cases


_CASES = _load_cases()


def test_negative_case_count():
    assert len(_CASES) >= 12, f"negative 用例过少({len(_CASES)}),疑 glob 落空"


@pytest.mark.parametrize("case", _CASES, ids=[c["case_id"] for c in _CASES] or ["_empty"])
def test_negative(case):
    layer, inp, exp = case["layer"], case["input"], case["expect"]
    if layer == "normalize":
        with pytest.raises(SchemaError):
            normalize_request(inp)
    elif layer == "validate":
        v = validate_candidate(inp)
        assert v["schema_valid"] is False, f"{case['case_id']}: 应 schema_valid=False"
        if "error_contains" in exp:
            assert any(exp["error_contains"] in e for e in v["errors"]), \
                f"{case['case_id']}: errors {v['errors']} 未含 {exp['error_contains']}"
        if "missing_contains" in exp:
            assert exp["missing_contains"] in v["missing_fields"], \
                f"{case['case_id']}: missing {v['missing_fields']} 未含 {exp['missing_contains']}"
    elif layer == "route":
        dec = route(normalize_request(inp))
        assert dec.disposition == exp["disposition"], \
            f"{case['case_id']}: disposition {dec.disposition} != {exp['disposition']}"
    else:
        pytest.fail(f"{case['case_id']}: 未知 layer={layer}")
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_negative_cases.py -q`
Expected: FAIL(test_negative_case_count:0 < 12)

- [ ] **Step 3: 写 schema 层数据(normalize + validate)**

写 `praxis_virtualcell/tests/negative_cases/schema_rejections.yaml`:

```yaml
# normalize 层:抛 SchemaError;validate 层:schema_valid=False。期望值均已 grounding。
cases:
  - case_id: normalize_unknown_species
    layer: normalize
    description: 未知物种 → SchemaError
    input: {species: martian, perturbation_object: gene, target_output: expression, perturbation_targets: [X]}
    expect: {schema_error: true}
  - case_id: normalize_unknown_object
    layer: normalize
    description: 未知扰动对象 → SchemaError
    input: {species: human, perturbation_object: teleport, target_output: expression, perturbation_targets: [X]}
    expect: {schema_error: true}
  - case_id: normalize_unknown_output
    layer: normalize
    description: 未知目标输出 → SchemaError
    input: {species: human, perturbation_object: gene, target_output: vibes, perturbation_targets: [X]}
    expect: {schema_error: true}
  - case_id: normalize_empty_gene_targets
    layer: normalize
    description: gene 类空 targets → SchemaError(不静默补默认)
    input: {species: human, perturbation_object: gene, target_output: expression, perturbation_targets: []}
    expect: {schema_error: true}
  - case_id: normalize_non_dict_input
    layer: normalize
    description: 非 dict 输入 → SchemaError
    input: "just a string"
    expect: {schema_error: true}
  - case_id: validate_unknown_species
    layer: validate
    description: parse→confirm:未知物种进 errors
    input: {species: martian, perturbation_type: gene, perturbation_targets: [X], task_type: predict_delta_expression}
    expect: {schema_valid: false, error_contains: "unsupported_species"}
  - case_id: validate_unknown_ptype
    layer: validate
    description: 未知扰动类型进 errors
    input: {species: human, perturbation_type: teleport, perturbation_targets: [X], task_type: predict_delta_expression}
    expect: {schema_valid: false, error_contains: "unsupported_perturbation_type"}
  - case_id: validate_missing_species
    layer: validate
    description: 缺物种 → missing_fields + clarification
    input: {perturbation_type: gene, perturbation_targets: [X], task_type: predict_delta_expression}
    expect: {schema_valid: false, missing_contains: "species"}
  - case_id: validate_empty_targets
    layer: validate
    description: 缺扰动目标 → missing_fields
    input: {species: human, perturbation_type: gene, perturbation_targets: [], task_type: predict_delta_expression}
    expect: {schema_valid: false, missing_contains: "perturbation_targets"}
  - case_id: validate_bad_task
    layer: validate
    description: 不支持的任务 → errors
    input: {species: human, perturbation_type: gene, perturbation_targets: [X], task_type: cure_cancer}
    expect: {schema_valid: false, error_contains: "unsupported_task"}
```

- [ ] **Step 4: 写 route 层数据(良构但不适用 → 非 accept)**

写 `praxis_virtualcell/tests/negative_cases/routing_rejections.yaml`:

```yaml
# route 层:良构但不适用,治理弃权/降级/告警,绝不 accept。期望值均已 grounding。
cases:
  - case_id: route_wrong_species_gene_abstain
    layer: route
    description: 错物种基因(bacteria + 人类 TP53)→ abstain(治理经路由弃权,不编造)
    input: {species: bacteria, perturbation_object: gene, target_output: expression, perturbation_targets: [TP53]}
    expect: {disposition: abstain}
  - case_id: route_unmappable_drug_caution
    layer: route
    description: 无法映射的药名 → embedding/caution(诚实:会试但签名噪声大,非 accept)
    input: {species: human, perturbation_object: drug, target_output: expression, perturbation_targets: [notarealdrug]}
    expect: {disposition: caution}
  - case_id: route_yeast_communication_abstain
    layer: route
    description: 酵母细胞通讯无适用引擎 → abstain
    input: {species: yeast, perturbation_object: ligand, target_output: communication, perturbation_targets: [X]}
    expect: {disposition: abstain}
  - case_id: route_yeast_gene_state_abstain
    layer: route
    description: 酵母细胞状态无适用引擎 → abstain
    input: {species: yeast, perturbation_object: gene, target_output: state, perturbation_targets: [YBR166C]}
    expect: {disposition: abstain}
```

- [ ] **Step 5: 跑确认通过 + ruff + 全量无回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_negative_cases.py -q`
Expected: PASS(14 negative + count = 15 passed)

Run: `.venv/bin/ruff check praxis_virtualcell/tests/test_negative_cases.py`
Expected: All checks passed!

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider -o console_output_style=classic 2>&1 | tail -1`
Expected: `270 passed, 25 skipped`(255 基线 + 15),**确认 0 failed**(看完整行,不只看 passed)

- [ ] **Step 6: commit + push**

```bash
find docs praxis_virtualcell praxis_vc_api praxis_vc_react -name '._*' -delete
git add praxis_virtualcell/tests/test_negative_cases.py praxis_virtualcell/tests/negative_cases/
git commit -m "test(v0.7): Negative/fuzz 固化—14 拒绝用例(schema/validate/route 三层)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push origin main
```

---

## Task 2: KPI「无静默 accept」聚合断言(TDD)

**Files:**
- Modify: `praxis_virtualcell/tests/test_negative_cases.py`(加 KPI 聚合测试)

- [ ] **Step 1: 追加 KPI 测试**

在 `test_negative_cases.py` 末尾追加:

```python
def test_negative_never_silently_accepts():
    """KPI:没有任何 negative case 得到静默 accept/成功。
    normalize 层必抛、validate 层 schema_valid=False、route 层 disposition!=accept。"""
    offenders = []
    for c in _CASES:
        layer, inp = c["layer"], c["input"]
        if layer == "normalize":
            try:
                normalize_request(inp)
                offenders.append(f"{c['case_id']}(normalize 未拒绝)")
            except SchemaError:
                pass
        elif layer == "validate":
            if validate_candidate(inp)["schema_valid"] is not False:
                offenders.append(f"{c['case_id']}(validate 竟 valid)")
        elif layer == "route":
            if route(normalize_request(inp)).disposition == "accept":
                offenders.append(f"{c['case_id']}(route 竟 accept)")
    assert offenders == [], f"静默 accept 违规:{offenders}"
```

- [ ] **Step 2: 跑确认通过(数据已就绪,直接绿)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_negative_cases.py -q`
Expected: PASS(新增 test_negative_never_silently_accepts)

- [ ] **Step 3: 全量无回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider -o console_output_style=classic 2>&1 | tail -1`
Expected: `271 passed, 25 skipped`,**0 failed**

- [ ] **Step 4: commit + push**

```bash
find docs praxis_virtualcell praxis_vc_api praxis_vc_react -name '._*' -delete
git add praxis_virtualcell/tests/test_negative_cases.py
git commit -m "test(v0.7): negative KPI 聚合断言—无静默 accept(3 层全覆盖)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push origin main
```

---

## 验收(全部完成后)
- `pytest praxis_virtualcell/tests/test_negative_cases.py` 全绿:14 拒绝 + count + KPI。
- 全量 ≥271 passed,0 failed;CI 口径无回归;每 task 已 push。

## 停止条件(硬门)
1. 某拒绝路径实际不拒绝(route accept / validate valid / normalize 不抛)→ 真实 gap,停下报告(不改测试迁就);
2. pytest 回归无法自解;3. git push 失败/CI 红;4. Task 1–2 完成→切片 2 收尾,简短汇报后继续切片 3(⚠️需 AskUserQuestion 拍板)。
