# Golden case 固化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans。Steps 用 checkbox 跟踪。

**Goal:** 把代表 case 固化为声明式 `golden_cases/*.yaml` + 通用 runner,建立路由/治理回归安全网,KPI:golden pass 100%、unsafe accept=0。

**Architecture:** golden 数据(yaml)声明 `input`+`expect`;runner 用纯 `route(normalize_request(input))` 断言 engine/disposition/caution/data_gated,加 KPI(no-unsafe-accept)与 count 守卫;`workflow: offline` 的 case 额外跑离线 run_query 验证 report.md/provenance 生成。纯确定性、零 skip(PyYAML 是核心依赖)。

**Tech Stack:** Python / pytest 参数化 / PyYAML。

**铁律:** 只读断言现有 route/workflow 行为,不改 route_table/species_schema 逻辑;若 route 输出与期望不符→真实 bug,停下报告不改 golden 迁就。每 task 全量 `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests` 绿后 commit + push origin main。commit 前删 `._*`,末尾 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。

**数据契约(已实跑验证):** `normalize_request(input)` 需 `species/perturbation_object/target_output/perturbation_targets`(medium 类可空 targets,带 `medium` 字段);`route()` 返回 `RouteDecision(engine, disposition, caution_flags:list, data_gated:bool)`。18 用例期望值见 spec §3。

---

## Task 1: 路由 golden(runner + 18 用例数据,TDD)

**Files:**
- Create: `praxis_virtualcell/tests/test_golden_cases.py`
- Create: `praxis_virtualcell/tests/golden_cases/routing_representative.yaml`
- Create: `praxis_virtualcell/tests/golden_cases/routing_safety.yaml`

- [ ] **Step 1: 写 runner(先失败:无数据 count<16)**

写 `praxis_virtualcell/tests/test_golden_cases.py`:

```python
"""Golden case 固化:声明式路由 golden(纯 route() 断言,无重依赖,零 skip)。
KPI:golden pass 100% + unsafe accept=0。数据在 golden_cases/*.yaml。
铁律:只读断言现有 route 行为;route 输出与期望不符=真实 bug,不改 golden 迁就。"""
from pathlib import Path

import pytest
import yaml

from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request

_GOLDEN_DIR = Path(__file__).parent / "golden_cases"


def _load_cases():
    cases = []
    for f in sorted(_GOLDEN_DIR.glob("*.yaml")):
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        cases.extend(doc.get("cases", []))
    return cases


_CASES = _load_cases()


def test_case_count():
    assert len(_CASES) >= 16, f"golden 用例过少({len(_CASES)}),疑 glob 落空或数据缺失"


@pytest.mark.parametrize("case", _CASES, ids=[c["case_id"] for c in _CASES] or ["_empty"])
def test_route_matches(case):
    dec = route(normalize_request(case["input"]))
    exp = case["expect"]
    assert dec.engine == exp["engine"], f"{case['case_id']}: engine {dec.engine} != {exp['engine']}"
    assert dec.disposition == exp["disposition"], \
        f"{case['case_id']}: disposition {dec.disposition} != {exp['disposition']}"
    if "caution_flags" in exp:
        assert set(dec.caution_flags) == set(exp["caution_flags"]), \
            f"{case['case_id']}: caution_flags {dec.caution_flags} != {exp['caution_flags']}"
    if "data_gated" in exp:
        assert dec.data_gated == exp["data_gated"], \
            f"{case['case_id']}: data_gated {dec.data_gated} != {exp['data_gated']}"


def test_no_unsafe_accept():
    """KPI:凡期望非 accept 的 case,实际不得 accept(不许把该弃权/降级硬报为可信)。"""
    unsafe = [c["case_id"] for c in _CASES
              if c["expect"]["disposition"] != "accept"
              and route(normalize_request(c["input"])).disposition == "accept"]
    assert unsafe == [], f"unsafe accept(应非 accept 却 accept):{unsafe}"
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_golden_cases.py -q`
Expected: FAIL(test_case_count:0 < 16;test_route_matches 空参数集 skip)

- [ ] **Step 3: 写 representative 数据**

写 `praxis_virtualcell/tests/golden_cases/routing_representative.yaml`:

```yaml
# 代表 case:5 应用 × 4 物种覆盖;expect 为 route() 实跑验证值。
cases:
  - case_id: human_gene_expression
    description: 人类基因扰动→表达,原生 scRNA predictor
    input: {species: human, perturbation_object: gene, target_output: expression, perturbation_targets: [AHR]}
    expect: {engine: donor_predictor, disposition: accept}
    workflow: offline
    request:
      species: human
      perturbation_type: gene
      perturbation_targets: [AHR]
      task_type: predict_delta_expression
      input_modality: scRNA
      output_modality: delta_expression
  - case_id: mouse_gene_expression
    description: 小鼠基因→表达,human predictor 迁移需 ortholog(caution)
    input: {species: mouse, perturbation_object: gene, target_output: expression, perturbation_targets: [Gata1]}
    expect: {engine: donor_predictor, disposition: caution, caution_flags: [ortholog_required]}
  - case_id: ecoli_gene_growth
    description: 大肠杆菌基因敲除→生长,机制 GEM
    input: {species: bacteria, perturbation_object: gene, target_output: growth, perturbation_targets: [b0720]}
    expect: {engine: gem_fba, disposition: accept}
  - case_id: yeast_gene_growth
    description: 酵母基因敲除→生长,机制 GEM
    input: {species: yeast, perturbation_object: gene, target_output: growth, perturbation_targets: [YBR166C]}
    expect: {engine: gem_fba, disposition: accept}
  - case_id: ecoli_medium_growth
    description: 大肠杆菌碳源切换→生长,机制 GEM
    input: {species: bacteria, perturbation_object: medium, target_output: growth, perturbation_targets: [], medium: acetate}
    expect: {engine: gem_fba, disposition: accept}
  - case_id: bacteria_drug_growth
    description: 抗生素(靶代谢)→生长抑制,机制 GEM
    input: {species: bacteria, perturbation_object: drug, target_output: growth, perturbation_targets: [trimethoprim]}
    expect: {engine: gem_fba, disposition: accept}
  - case_id: human_drug_expression
    description: 人类药物扰动→表达,LINCS 签名(caution)
    input: {species: human, perturbation_object: drug, target_output: expression, perturbation_targets: [vorinostat]}
    expect: {engine: embedding, disposition: caution}
  - case_id: human_gene_state
    description: 人类基因→细胞状态,marker state scoring
    input: {species: human, perturbation_object: gene, target_output: state, perturbation_targets: [SNAI1]}
    expect: {engine: state_scoring, disposition: accept}
  - case_id: mammalian_flux
    description: 哺乳类代谢通量→pathway tendency(caution)
    input: {species: human, perturbation_object: gene, target_output: flux, perturbation_targets: [PKM]}
    expect: {engine: pathway_scoring, disposition: caution}
  - case_id: human_communication
    description: 人类配体→细胞通讯,ligand-receptor 共表达
    input: {species: human, perturbation_object: ligand, target_output: communication, perturbation_targets: [TNF]}
    expect: {engine: communication, disposition: accept}
  - case_id: mouse_gene_state
    description: 小鼠基因→状态/命运,ortholog(caution)
    input: {species: mouse, perturbation_object: gene, target_output: state, perturbation_targets: [Gata1]}
    expect: {engine: state_scoring, disposition: caution, caution_flags: [ortholog_required]}
  - case_id: human_spatial_niche
    description: 人类微环境→状态,空间 niche
    input: {species: human, perturbation_object: medium, target_output: state, perturbation_targets: [], medium: niche}
    expect: {engine: spatial_niche, disposition: accept}
```

- [ ] **Step 4: 写 safety 数据(必须非 accept)**

写 `praxis_virtualcell/tests/golden_cases/routing_safety.yaml`:

```yaml
# Safety case:治理必须拒绝/降级/弃权,绝不 accept。守 KPI unsafe-accept=0。
cases:
  - case_id: bacteria_gene_expression_reject
    description: 铁律—哺乳类 scRNA predictor 不适用微生物表达→abstain
    input: {species: bacteria, perturbation_object: gene, target_output: expression, perturbation_targets: [b0720]}
    expect: {engine: reject, disposition: abstain}
  - case_id: yeast_gene_expression_reject
    description: 酵母表达无适用 scRNA predictor→abstain
    input: {species: yeast, perturbation_object: gene, target_output: expression, perturbation_targets: [YBR166C]}
    expect: {engine: reject, disposition: abstain}
  - case_id: mammalian_growth_downgrade
    description: 哺乳类 growth 无机制 GEM 接入→downgrade(data-gated),不假装
    input: {species: human, perturbation_object: gene, target_output: growth, perturbation_targets: [MYC]}
    expect: {engine: gem_fba, disposition: downgrade, data_gated: true}
  - case_id: human_ligand_expression_downgrade
    description: 配体签名模型未接入→downgrade(data-gated)
    input: {species: human, perturbation_object: ligand, target_output: expression, perturbation_targets: [TNF]}
    expect: {engine: embedding, disposition: downgrade, data_gated: true}
  - case_id: bacteria_state_reject
    description: 微生物细胞状态无适用引擎→abstain
    input: {species: bacteria, perturbation_object: gene, target_output: state, perturbation_targets: [b0720]}
    expect: {engine: reject, disposition: abstain}
  - case_id: bacteria_communication_reject
    description: 微生物细胞通讯无适用引擎→abstain
    input: {species: bacteria, perturbation_object: ligand, target_output: communication, perturbation_targets: [FLIC]}
    expect: {engine: reject, disposition: abstain}
```

- [ ] **Step 5: 跑确认通过 + 全量无回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_golden_cases.py -q`
Expected: PASS(18 route + count + no_unsafe_accept = 20 passed)

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: ≥253 passed(233 基线 + 20),0 failed

- [ ] **Step 6: commit + push**

```bash
find docs praxis_virtualcell praxis_vc_api praxis_vc_react -name '._*' -delete
git add praxis_virtualcell/tests/test_golden_cases.py praxis_virtualcell/tests/golden_cases/
git commit -m "test(v0.7): Golden case 固化—18 声明式路由用例 + KPI unsafe-accept=0

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push origin main
```

---

## Task 2: workflow-offline 报告校验(report.md + provenance,TDD)

**Files:**
- Modify: `praxis_virtualcell/tests/test_golden_cases.py`(加 workflow-offline 测试)

- [ ] **Step 1: 追加失败测试**

在 `test_golden_cases.py` 末尾追加:

```python
_WF_CASES = [c for c in _CASES if c.get("workflow") == "offline"]


@pytest.mark.parametrize("case", _WF_CASES, ids=[c["case_id"] for c in _WF_CASES] or ["_none"])
def test_workflow_offline_report(case):
    """workflow: offline 的 case 跑离线 run_query,验证 report.md/provenance 生成(§4.3)。"""
    from praxis_virtualcell.core.config import Mode, RuntimeConfig
    from praxis_virtualcell.io.report_markdown import render_report_md
    from praxis_virtualcell.workflows.run_virtualcell_query import run_query
    cfg = RuntimeConfig(mode=Mode.OFFLINE, llm_enabled=False)
    out = run_query(case["request"], config=cfg)
    assert out["structured_report"].get("provenance"), "provenance 应非空"
    assert isinstance(out["structured_report"].get("abstain"), bool)
    job = {"report": out["structured_report"], "request": case["request"],
           "provenance": out["provenance"], "mode": out["mode"]}
    md = render_report_md(job)
    for sec in ("## 1. Question", "## 5. Governance Verdict", "## 9. Reproducibility"):
        assert sec in md, f"report.md 缺段:{sec}"


def test_has_workflow_offline_case():
    assert len(_WF_CASES) >= 1, "至少 1 个 workflow: offline case 覆盖离线报告链"
```

- [ ] **Step 2: 跑确认(应直接通过——数据已含 workflow: offline)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_golden_cases.py -q`
Expected: PASS(新增 test_workflow_offline_report[human_gene_expression] + test_has_workflow_offline_case)

> 注:Task 1 数据里 human_gene_expression 已带 `workflow: offline` + `request`,故本测试直接绿。若 `_WF_CASES` 为空(数据漏 flag)则 test_has_workflow_offline_case 失败——即红→补 flag→绿。

- [ ] **Step 3: 全量无回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: ≥255 passed,0 failed

- [ ] **Step 4: commit + push**

```bash
find docs praxis_virtualcell praxis_vc_api praxis_vc_react -name '._*' -delete
git add praxis_virtualcell/tests/test_golden_cases.py
git commit -m "test(v0.7): golden workflow-offline 校验 report.md/provenance 生成链

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push origin main
```

---

## 验收(全部完成后)

- `pytest praxis_virtualcell/tests/test_golden_cases.py` 全绿:18 路由 + KPI(unsafe-accept=0)+ count + workflow-offline。
- 全量 `praxis_virtualcell/tests` ≥255 passed,0 failed;CI 口径无回归。
- 每 task 已 push,CI 保持绿。

## 停止条件(硬门)
1. route() 输出与 golden 期望不符→真实 route bug,停下报告(不改 golden 迁就);
2. pytest 回归无法自解;
3. git push 失败/CI 红;
4. Task 1–2 完成→切片 1 收尾,简短汇报后继续切片 2。
