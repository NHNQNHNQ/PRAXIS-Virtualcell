# P10.B2 M3/M4 代谢模块做到满 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 M3/M4 代谢对的余下真实子路径(gem_fba 的 medium/drug + pathway_scoring)接进 offline 主链,让微生物碳源切换/抗生素靶抑制 growth、哺乳类代谢通路 tendency 都跑真实 FBA/评分。

**Architecture:** 纯扩 B1 的 `case_dispatch` adapter 分发层——`dispatch_runner` 按 perturbation_object 细分 gem_fba(gene/medium/drug)+ 加 pathway_scoring 分支;`map_case_delta` 按 raw_output 判别键(knockouts/carbon_sources/antibiotics/pathway_shifts)分支;`REAL_ENGINES` 加 pathway_scoring。CaseRunner/ModelApplicability(单一真源 import)/reliability/provenance 全不改;B1 的诚实透传机制(abstain→rejected、model_cautions)自动覆盖三条新路径。

**Tech Stack:** Python、cobra(iML1515/e_coli_core)、pertpy Kang 2018、pytest。测试口径永远显式 `praxis_virtualcell/tests`。提交前必跑 `ruff check`。

**上游:** spec `docs/superpowers/specs/2026-07-09-phase10b2-metabolic-modules-mainline-design.md`。

**红线:** 不碰 reliability/critic 裁决逻辑(honest abstain 靠既有 `if not used`);真实预测确定性;adapter 诚实透传不伪造;核心+根 tests/ 零触碰;不 push;trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。

**已核实的确切期望值(端到端真跑,供断言):**
- bacteria medium `["acetate"]` → disposition accept、`carbon_sources[0].ratio_vs_glucose=0.1983` → delta `[-0.8017]`。
- bacteria drug `["trimethoprim"]`(靶 DHFR)→ accept、growth_arrest、`ratio_vs_wt=0.0` → delta `[-1.0]`。
- bacteria drug `["ampicillin"]`(非代谢靶)→ **abstain**、flag `non_metabolic_target:ampicillin`。
- human gene flux `["STAT1"]` → metabolic_tendency disposition **downgrade**(弱效应 max_d=0.281)、`pathway_shifts` cohens_d=[0.101,0.281] → delta `[0.101, 0.281]`、flag `weak_pathway_effect:max_d=0.281`。

---

## File Structure

- **Modify** `praxis_virtualcell/predictors/case_dispatch.py` — dispatch_runner 细分 + map_case_delta 按 raw_output 分支 + REAL_ENGINES 加 pathway_scoring。
- **Modify** `praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` — B2 单元 + 端到端 + 契约测试。

---

## Task 1: gem_fba + medium 接入(dispatch 细分 + map_case_delta carbon_sources)

**Files:** Modify `praxis_virtualcell/predictors/case_dispatch.py`;Test `praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py`

- [ ] **Step 1: 写失败测试**(追加到测试文件末尾)

```python
def test_dispatch_runner_gem_fba_medium():
    from praxis_virtualcell.predictors.mechanistic.medium_shift import run_medium_shift_case
    raw = {"species": "bacteria", "perturbation_object": "medium"}
    assert dispatch_runner("gem_fba", raw) is run_medium_shift_case


def test_dispatch_runner_gem_fba_medium_yeast_unsupported():
    # 无 yeast medium runner → 诚实抛 UnsupportedEngine(会被 CaseRunner 转 abstain)
    with pytest.raises(UnsupportedEngine):
        dispatch_runner("gem_fba", {"species": "yeast", "perturbation_object": "medium"})


def test_map_case_delta_gem_fba_medium():
    report = SimpleNamespace(raw_output={"reference": "glucose minimal", "glucose_growth": 0.87392,
        "carbon_sources": [{"carbon": "acetate", "in_model": True, "ratio_vs_glucose": 0.1983},
                           {"carbon": "unobtainium", "in_model": False, "ratio_vs_glucose": None}]})
    assert map_case_delta("gem_fba", report) == [-0.8017]   # 不在模型的碳源跳过
```

- [ ] **Step 2: 跑测试验证失败**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "gem_fba_medium" -v`
Expected: FAIL — medium 现走 gene 分支落空抛 UnsupportedEngine;map_case_delta 读 knockouts KeyError。

- [ ] **Step 3: 最小实现**(改 `case_dispatch.py`)

`dispatch_runner` 改为按 obj 细分 gem_fba(保留 gene 现状,加 medium bacteria-guarded):
```python
def dispatch_runner(engine: str, raw_req: dict):
    """engine + 请求上下文 → 具体 run_*_case(返回可调用)。"""
    species = raw_req.get("species")
    obj = raw_req.get("perturbation_object")
    if engine == "gem_fba":
        if obj in _GENE_LIKE:
            if species == "bacteria":
                from praxis_virtualcell.predictors.mechanistic.ecoli_gem import run_ecoli_growth_case
                return run_ecoli_growth_case
            if species == "yeast":
                from praxis_virtualcell.predictors.mechanistic.yeast_gem import run_yeast_growth_case
                return run_yeast_growth_case
        elif obj == "medium" and species == "bacteria":
            from praxis_virtualcell.predictors.mechanistic.medium_shift import run_medium_shift_case
            return run_medium_shift_case
    raise UnsupportedEngine(f"B 未接入 case runner: engine={engine} object={obj} species={species}")
```
`map_case_delta` 重构为 gem_fba 内按 raw_output 判别键分支(保 B1 knockouts + 加 carbon_sources):
```python
def map_case_delta(engine: str, report) -> list[float]:
    """CaseReport.raw_output → delta 向量(确定性,继承 raw_output 的 round)。按 raw_output 判别键选映射。"""
    raw = report.raw_output
    if engine == "gem_fba":
        if "knockouts" in raw:      # gene KO growth:ratio-1(essential→-1.0;None 跳过)
            return [round(k["ratio"] - 1.0, 4) for k in raw["knockouts"] if k["ratio"] is not None]
        if "carbon_sources" in raw:  # medium 切换:相对葡萄糖生长变化;不在模型跳过
            return [round(r["ratio_vs_glucose"] - 1.0, 4) for r in raw["carbon_sources"] if r["in_model"]]
        raise UnsupportedEngine(f"gem_fba map_case_delta 未支持 raw_output 形状: {sorted(raw)}")
    raise UnsupportedEngine(f"map_case_delta 未支持 engine={engine}")
```

- [ ] **Step 4: 跑测试验证通过**

Run: 同 Step 2 + B1 回归 `-k "gem_fba_medium or map_case_delta or dispatch_runner"`。Expected: 全 PASS(B1 的 knockouts/unsupported 测试仍绿)。

- [ ] **Step 5: ruff + commit**

Run: `.venv/bin/ruff check praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` → All checks passed。
```bash
git add praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "feat(phase10b2): Task 1 gem_fba+medium 接入(碳源切换 dispatch + carbon_sources delta)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: gem_fba + drug 接入(dispatch drug + map_case_delta antibiotics)

**Files:** Modify `praxis_virtualcell/predictors/case_dispatch.py`;Test `tests/phase10/test_t10_2_module_contracts.py`

- [ ] **Step 1: 写失败测试**(追加)

```python
def test_dispatch_runner_gem_fba_drug():
    from praxis_virtualcell.predictors.mechanistic.antibiotic import run_antibiotic_case
    raw = {"species": "bacteria", "perturbation_object": "drug"}
    assert dispatch_runner("gem_fba", raw) is run_antibiotic_case


def test_map_case_delta_gem_fba_drug():
    report = SimpleNamespace(raw_output={"wt_growth": 0.877, "antibiotics": [
        {"antibiotic": "trimethoprim", "target_rxn": "DHFR", "in_model": True, "ratio_vs_wt": 0.0},
        {"antibiotic": "ampicillin", "target_rxn": "non-metabolic", "known": True, "in_model": False}]})
    # in_model 且有 ratio_vs_wt 的项:ratio-1;非代谢/未知项跳过
    assert map_case_delta("gem_fba", report) == [-1.0]
```

- [ ] **Step 2: 跑测试验证失败**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "gem_fba_drug" -v`
Expected: FAIL — drug 落空抛 UnsupportedEngine;map_case_delta 无 antibiotics 分支抛 UnsupportedEngine。

- [ ] **Step 3: 最小实现**

`dispatch_runner` 的 gem_fba 分支加 drug(在 medium 分支后):
```python
        elif obj == "drug" and species == "bacteria":
            from praxis_virtualcell.predictors.mechanistic.antibiotic import run_antibiotic_case
            return run_antibiotic_case
```
`map_case_delta` 的 gem_fba 分支加 antibiotics(在 carbon_sources 后、raise 前):
```python
        if "antibiotics" in raw:     # 抗生素靶抑制:相对 WT 生长变化;未知/非代谢/不在模型跳过
            return [round(r["ratio_vs_wt"] - 1.0, 4) for r in raw["antibiotics"]
                    if r.get("in_model") and r.get("ratio_vs_wt") is not None]
```

- [ ] **Step 4: 跑测试验证通过**

Run: 同 Step 2。Expected: 2 passed。

- [ ] **Step 5: ruff + commit**

Run: `.venv/bin/ruff check praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` → All checks passed。
```bash
git add praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "feat(phase10b2): Task 2 gem_fba+drug 接入(抗生素靶抑制 dispatch + antibiotics delta)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: pathway_scoring 接入(REAL_ENGINES + dispatch + map_case_delta pathway_shifts)

**Files:** Modify `praxis_virtualcell/predictors/case_dispatch.py`;Test `tests/phase10/test_t10_2_module_contracts.py`

- [ ] **Step 1: 写失败测试**(追加)

```python
def test_pathway_scoring_in_real_engines():
    from praxis_virtualcell.predictors.case_dispatch import REAL_ENGINES
    assert "pathway_scoring" in REAL_ENGINES


def test_dispatch_runner_pathway_scoring():
    from praxis_virtualcell.predictors.state.metabolic_tendency import run_metabolic_tendency_case
    raw = {"species": "human", "perturbation_object": "gene"}
    assert dispatch_runner("pathway_scoring", raw) is run_metabolic_tendency_case


def test_map_case_delta_pathway_scoring():
    report = SimpleNamespace(raw_output={"max_abs_cohens_d": 0.281, "pathway_shifts": [
        {"panel": "glycolysis", "cohens_d": 0.101}, {"panel": "oxphos", "cohens_d": 0.281}]})
    assert map_case_delta("pathway_scoring", report) == [0.101, 0.281]
```

- [ ] **Step 2: 跑测试验证失败**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "pathway_scoring" -v`
Expected: FAIL — pathway_scoring 不在 REAL_ENGINES;dispatch/map 无分支。

- [ ] **Step 3: 最小实现**

`REAL_ENGINES` 加 pathway_scoring:
```python
REAL_ENGINES = frozenset({"gem_fba", "pathway_scoring"})
```
`dispatch_runner` 加 pathway_scoring 分支(在 gem_fba 整块的 `if engine == "gem_fba":` 之后,用 `elif`):
```python
    elif engine == "pathway_scoring":
        from praxis_virtualcell.predictors.state.metabolic_tendency import run_metabolic_tendency_case
        return run_metabolic_tendency_case
```
`map_case_delta` 加 pathway_scoring 分支(在 gem_fba 整块之后、末尾 raise 之前):
```python
    if engine == "pathway_scoring":  # 代谢通路 tendency:各通路 Cohen's d 效应量作 delta 分量
        return [round(s["cohens_d"], 4) for s in report.raw_output["pathway_shifts"]]
```

- [ ] **Step 4: 跑测试验证通过 + B1/B2 单元全回归**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "pathway_scoring or dispatch_runner or map_case_delta" -v`
Expected: 全 PASS(含 B1 的 gene/unsupported、B2 的 medium/drug)。

- [ ] **Step 5: ruff + commit**

Run: `.venv/bin/ruff check praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` → All checks passed。
```bash
git add praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "feat(phase10b2): Task 3 pathway_scoring 接入(REAL_ENGINES+dispatch+cohens_d delta)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: 三子路径端到端真实预测 + 负例诚实 abstain

**Files:** Test `tests/phase10/test_t10_2_module_contracts.py`(端到端,复用 `_CFG`/`run_query`)

- [ ] **Step 1: 写端到端测试**(追加)

```python
def test_bacteria_medium_shift_real_fba():
    req = {"species": "bacteria", "perturbation_type": "medium", "perturbation_targets": ["acetate"],
           "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is False
    assert "CaseRunner" in sr["provenance"]["models_used"]
    assert sr["prediction"]["delta"] == [-0.8017]        # 乙酸 0.1983×葡萄糖 → 真实 FBA


def test_bacteria_antibiotic_real_fba():
    req = {"species": "bacteria", "perturbation_type": "drug", "perturbation_targets": ["trimethoprim"],
           "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is False
    assert sr["prediction"]["delta"] == [-1.0]            # DHFR 抑制 growth 0


def test_human_pathway_tendency_real_scoring():
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["STAT1"],
           "input_modality": "scRNA", "output_modality": "flux", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is False
    assert "CaseRunner" in sr["provenance"]["models_used"]
    assert sr["prediction"]["delta"] == [0.101, 0.281]    # 两通路 Cohen's d
    # 弱效应 downgrade 经 model_cautions 诚实标注(不伪装强)
    assert any("weak_pathway_effect" in f for f in sr["provenance"]["model_cautions"]["CaseRunner"])


def test_bacteria_antibiotic_non_metabolic_abstains():
    # 非代谢靶(ampicillin)→ 机制 abstain → 主链如实弃权 + 原因透出
    req = {"species": "bacteria", "perturbation_type": "drug", "perturbation_targets": ["ampicillin"],
           "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is True
    assert sr["prediction"] is None
    assert "CaseRunner" in sr["provenance"]["models_rejected"]
    assert any("non_metabolic_target" in f for f in sr["provenance"]["model_cautions"]["CaseRunner"])
```

- [ ] **Step 2: 跑测试验证通过**(真跑 cobra FBA / 评分,几秒)

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "medium_shift_real or antibiotic_real or pathway_tendency_real or non_metabolic_abstains" -v`
Expected: 4 passed。**若数值/ disposition 不符,不改测试迁就——停下报告实际值排查。**

- [ ] **Step 3: ruff + commit**

Run: `.venv/bin/ruff check praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` → All checks passed。
```bash
git add praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "test(phase10b2): Task 4 三子路径端到端真实预测 + 非代谢靶诚实 abstain

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: 字节等价 + mock 不变 + 受影响测试 + 全量回归 + T10.2 契约收尾

**Files:** Test `tests/phase10/test_t10_2_module_contracts.py`;可能 Modify 受影响既有测试(执行时定位)

- [ ] **Step 1: 补字节等价 + mock 不变测试**(追加)

```python
def test_b2_real_requests_rerun_byte_equal():
    for req in (
        {"species": "bacteria", "perturbation_type": "medium", "perturbation_targets": ["acetate"],
         "input_modality": "scRNA", "output_modality": "growth", "task_type": "predict_delta_expression"},
        {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["STAT1"],
         "input_modality": "scRNA", "output_modality": "flux", "task_type": "predict_delta_expression"}):
        outs = [run_query(dict(req), config=_CFG) for _ in range(3)]
        assert len({_canon(o["structured_report"]) for o in outs}) == 1
        assert len({_canon(o["trace"]) for o in outs}) == 1


def test_b2_mock_expression_request_unchanged():
    # human gene→EXPRESSION 仍走 donor_predictor mock(pathway_scoring 只吃 flux,不碰 expression)
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    assert "CaseRunner" not in out["structured_report"]["provenance"]["models_used"]
```

- [ ] **Step 2: 跑全量定位受影响测试**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider 2>&1 | tail -30`
Expected: 新测试全 PASS。**可能有既有测试因 human+flux 从 mock([0.3])→真实 pathway_scoring、或 bacteria medium/drug 从 abstain→真实 而 FAIL。** 记录 FAIL 清单。

- [ ] **Step 3: 逐个核对受影响测试**

对每个 FAIL:确认失败是**"接入真实 runner 使 human flux(mock→pathway)/ bacteria medium·drug(abstain→真实 FBA)语义提升"**——核对请求确是 flux/medium/drug(pathway_scoring/gem_fba)、结果是合理真实预测(delta 有值、disposition 诚实)。更新断言为真实结果。**若发现:mock 的 expression 请求(donor_predictor)行为变、或非 flux/medium/drug 路径异常 = 真实回归,停下排查,不改测试迁就。**

- [ ] **Step 4: 全量回归复绿**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider 2>&1 | tail -3`
Expected: 0 failed。

- [ ] **Step 5: ruff + commit**

Run: `.venv/bin/ruff check praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py`（+ 受影响测试文件)→ All checks passed。
```bash
git add -A praxis_virtualcell/tests
git commit -m "test(phase10b2): Task 5 字节等价+mock不变+受影响测试更新(flux/medium/drug abstain·mock→real)+全量0 failed

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
(台账勾账由控制器在两审通过后另做,implementer 不碰 UPGRADE-PROGRESS.md。)

---

## Self-Review(计划 vs spec 覆盖)

- **spec §3.1 gem_fba medium** → Task 1 ✅
- **spec §3.2 gem_fba drug** → Task 2 ✅
- **spec §3.3 pathway_scoring** → Task 3 ✅
- **spec §四 case_dispatch 三处改**(REAL_ENGINES/dispatch_runner/map_case_delta)→ Task 1-3 ✅
- **spec §六 影响(flux mock→real、medium/drug abstain→real)** → Task 5 受影响测试 ✅
- **spec §七 测试(3 正例真实 + 2 负例诚实 abstain + 字节等价 + mock 不变)** → Task 4/5 ✅
- **spec §九 完成标准**(三子路径真跑 / mock 不变 / 字节稳 / 分支单测 / 全量 0 failed)→ Task 1-5 ✅

命名一致:`dispatch_runner`/`map_case_delta`/`REAL_ENGINES`/`_GENE_LIKE`/raw_output 判别键(knockouts/carbon_sources/antibiotics/pathway_shifts)跨 task 一致。无占位。medium/drug bacteria-guarded(无 yeast runner→诚实 UnsupportedEngine→abstain)。
