# P10.B3 M7 应激模块诚实接入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 M7 应激的真实子路径(embedding 的 drug_signature/drug_dose + state_scoring 的 cell_state 窄门 human+IFN-β)接进 offline 主链;emt/fate/spatial_niche 作诚实 limitation(不接、诚实 abstain)。

**Architecture:** 纯扩 B1/B2 的 `case_dispatch` adapter——dispatch_runner 加 embedding(带 `dose` 字段→drug_dose、否则→drug_signature,均 human-guarded)+ state_scoring(cell_state,human+IFN-β 门,复用 B2 的 `_is_ifn_beta`)分支;map_case_delta 加 per_drug/dose_response/per_cell_type 判别键;REAL_ENGINES 加 embedding+state_scoring。复用 B1 诚实机制 + B2 窄门套路,不碰 reliability/critic。

**Tech Stack:** Python、LINCS/Kang 真数据(已 commit)、pytest。测试口径永远显式 `praxis_virtualcell/tests`。提交前必跑 `ruff check`。

**上游:** spec `docs/superpowers/specs/2026-07-09-phase10b3-stress-module-mainline-design.md`。

**红线:** 不碰 reliability/critic 裁决;真实预测确定性;全 human 数据引擎(embedding/state_scoring)均 species 守卫(B2 物种泄漏教训);emt/fate/spatial 绝不接成扰动 delta 预测器(类别错误);核心+根 tests/ 零触碰;不 push;trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。

**已核实确切期望值(端到端真跑):**
- human drug `["geldanamycin"]`(无 dose)→ drug_signature accept、per_drug moa_enrichment=2.646 → delta `[2.646]`。
- human drug `["geldanamycin"]` + `dose` 字段 → drug_dose accept、dose_response spearman=0.9 → delta `[0.9]`。
- human ligand `["IFNB1"]` state → cell_state accept、cohens_d=2.485 → delta `[2.485]`。
- human drug `["notadrug123"]` → abstain(`drug_not_in_db:notadrug123`,runner 自带)。

---

## File Structure

- **Modify** `praxis_virtualcell/predictors/case_dispatch.py` — REAL_ENGINES + dispatch_runner(embedding/state_scoring 分支)+ map_case_delta(per_drug/dose_response/per_cell_type)。
- **Modify** `praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` — B3 单元 + 端到端 + limitation abstain。

---

## Task 1: embedding / drug_signature 接入(MOA 签名)

**Files:** Modify `praxis_virtualcell/predictors/case_dispatch.py`;Test `tests/phase10/test_t10_2_module_contracts.py`

**开工前先 Read `case_dispatch.py`** 确认当前(B2 后)`REAL_ENGINES={"gem_fba","pathway_scoring"}`、dispatch_runner 的 gem_fba/pathway_scoring 分支、map_case_delta 的判别键结构、`_is_ifn_beta`/`_IFN_BETA_ALIASES`。

- [ ] **Step 1: 写失败测试**(追加到测试文件末尾)

```python
def test_pathway_engines_include_embedding():
    from praxis_virtualcell.predictors.case_dispatch import REAL_ENGINES
    assert "embedding" in REAL_ENGINES


def test_dispatch_runner_embedding_signature():
    from praxis_virtualcell.predictors.embedding.drug_signature import run_drug_response_case
    raw = {"species": "human", "perturbation_object": "drug"}
    assert dispatch_runner("embedding", raw) is run_drug_response_case


def test_dispatch_runner_embedding_mouse_unsupported():
    # LINCS 是 human 数据 → mouse+drug 诚实 UnsupportedEngine(防物种泄漏)
    with pytest.raises(UnsupportedEngine):
        dispatch_runner("embedding", {"species": "mouse", "perturbation_object": "drug"})


def test_map_case_delta_embedding_signature():
    report = SimpleNamespace(raw_output={"enrichment_threshold": 1.5, "per_drug": [
        {"drug": "geldanamycin", "in_db": True, "moa_enrichment": 2.646},
        {"drug": "notadrug", "in_db": False, "moa_enrichment": None}]})
    assert map_case_delta("embedding", report) == [2.646]   # 不在库跳过
```

- [ ] **Step 2: 跑测试验证失败**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "embedding_signature or embedding_mouse or engines_include_embedding" -v`
Expected: FAIL(embedding 不在 REAL_ENGINES;dispatch/map 无分支)。

- [ ] **Step 3: 最小实现**(改 `case_dispatch.py`)

① `REAL_ENGINES` 加 embedding:
```python
REAL_ENGINES = frozenset({"gem_fba", "pathway_scoring", "embedding"})
```
② `dispatch_runner` 在 pathway_scoring 分支后加 embedding(human-guarded;本 Task 只接 drug_signature,drug_dose 下个 Task 加):
```python
    elif engine == "embedding":
        if raw_req.get("species") == "human":
            from praxis_virtualcell.predictors.embedding.drug_signature import run_drug_response_case
            return run_drug_response_case
        # 非 human:LINCS 是 human 数据 → 落末尾 UnsupportedEngine → 诚实 abstain
```
③ `map_case_delta` 在 pathway_scoring 分支后加 embedding(per_drug 判别键):
```python
    if engine == "embedding":
        if "per_drug" in report.raw_output:   # drug_signature:各在库药的 MOA 富集分数
            return [round(d["moa_enrichment"], 4) for d in report.raw_output["per_drug"]
                    if d.get("in_db") and d.get("moa_enrichment") is not None]
        raise UnsupportedEngine(f"embedding map_case_delta 未支持 raw_output 形状: {sorted(report.raw_output)}")
```

- [ ] **Step 4: 跑测试验证通过 + 回归**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "embedding or dispatch_runner or map_case_delta or pathway or ifn" -v`
Expected: 全 PASS(B1/B2 分支仍绿)。

- [ ] **Step 5: ruff + commit**

Run: `.venv/bin/ruff check praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` → All checks passed。
```bash
git add praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "feat(phase10b3): Task 1 embedding/drug_signature 接入(MOA 签名 dispatch + per_drug delta,human-guarded)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: embedding / drug_dose 接入(剂量响应,dose 字段判别)

**Files:** Modify `praxis_virtualcell/predictors/case_dispatch.py`;Test `tests/phase10/test_t10_2_module_contracts.py`

- [ ] **Step 1: 写失败测试**(追加)

```python
def test_dispatch_runner_embedding_dose():
    from praxis_virtualcell.predictors.embedding.drug_dose import run_drug_dose_case
    # 带 dose 字段 → 剂量响应意图 → drug_dose
    raw = {"species": "human", "perturbation_object": "drug", "dose": "10uM"}
    assert dispatch_runner("embedding", raw) is run_drug_dose_case


def test_dispatch_runner_embedding_no_dose_is_signature():
    from praxis_virtualcell.predictors.embedding.drug_signature import run_drug_response_case
    # 无 dose 字段 → MOA 签名 → drug_signature(回归 Task1 行为)
    raw = {"species": "human", "perturbation_object": "drug"}
    assert dispatch_runner("embedding", raw) is run_drug_response_case


def test_map_case_delta_embedding_dose():
    report = SimpleNamespace(raw_output={"drug": "geldanamycin", "dose_response": {
        "n_doses": 6, "spearman": 0.9, "recalls": [0.04, 0.06], "insufficient": False}})
    assert map_case_delta("embedding", report) == [0.9]    # dose-recall Spearman 单调性
```

- [ ] **Step 2: 跑测试验证失败**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "embedding_dose or embedding_no_dose" -v`
Expected: `test_dispatch_runner_embedding_dose` FAIL(现无 dose 判别,恒返回 drug_signature);`test_map_case_delta_embedding_dose` FAIL(无 dose_response 分支)。

- [ ] **Step 3: 最小实现**

① `dispatch_runner` 的 embedding 分支加 dose 判别(在 `if species=="human":` 内,drug_signature 之前):
```python
    elif engine == "embedding":
        if raw_req.get("species") == "human":
            if raw_req.get("dose") is not None:
                from praxis_virtualcell.predictors.embedding.drug_dose import run_drug_dose_case
                return run_drug_dose_case
            from praxis_virtualcell.predictors.embedding.drug_signature import run_drug_response_case
            return run_drug_response_case
```
② `map_case_delta` 的 embedding 分支加 dose_response 判别键(在 per_drug 后、embedding 的 raise 前):
```python
        if "dose_response" in report.raw_output:   # drug_dose:剂量-recall 单调性 Spearman
            return [round(report.raw_output["dose_response"]["spearman"], 4)]
```

- [ ] **Step 4: 跑测试验证通过**

Run: 同 Step 2 + `-k "embedding"`。Expected: 全 PASS(drug_signature/drug_dose 判别都对)。

- [ ] **Step 5: ruff + commit**

Run: `.venv/bin/ruff check praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` → All checks passed。
```bash
git add praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "feat(phase10b3): Task 2 embedding/drug_dose 接入(dose 字段判别 + dose_response spearman delta)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: state_scoring / cell_state 接入(窄门 human+IFN-β)

**Files:** Modify `praxis_virtualcell/predictors/case_dispatch.py`;Test `tests/phase10/test_t10_2_module_contracts.py`

- [ ] **Step 1: 写失败测试**(追加)

```python
def test_pathway_engines_include_state_scoring():
    from praxis_virtualcell.predictors.case_dispatch import REAL_ENGINES
    assert "state_scoring" in REAL_ENGINES


def test_dispatch_runner_state_scoring_ifn():
    from praxis_virtualcell.predictors.state.cell_state import run_cellstate_case
    raw = {"species": "human", "perturbation_object": "ligand", "perturbation_targets": ["IFNB1"]}
    assert dispatch_runner("state_scoring", raw) is run_cellstate_case


def test_dispatch_runner_state_scoring_non_ifn_unsupported():
    # cell_state 是固定 Kang IFN-β 数据 → 非 IFN-β(如 emt 的 ZEB1)/mouse(fate)诚实 UnsupportedEngine
    for raw in ({"species": "human", "perturbation_object": "gene", "perturbation_targets": ["ZEB1"]},
                {"species": "mouse", "perturbation_object": "gene", "perturbation_targets": ["Gata1"]}):
        with pytest.raises(UnsupportedEngine):
            dispatch_runner("state_scoring", raw)


def test_map_case_delta_state_scoring():
    report = SimpleNamespace(raw_output={"cohens_d": 2.485, "marker_coverage": 1.0,
        "per_cell_type": [{"cell_type": "B cells", "cohens_d": 3.472}]})
    assert map_case_delta("state_scoring", report) == [2.485]   # 整体 ISG 组间效应量
```

- [ ] **Step 2: 跑测试验证失败**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "state_scoring" -v`
Expected: FAIL(state_scoring 不在 REAL_ENGINES;dispatch/map 无分支)。

- [ ] **Step 3: 最小实现**

① `REAL_ENGINES` 加 state_scoring:
```python
REAL_ENGINES = frozenset({"gem_fba", "pathway_scoring", "embedding", "state_scoring"})
```
② `dispatch_runner` 在 embedding 分支后加 state_scoring(human+IFN-β 门,复用 `_is_ifn_beta`):
```python
    elif engine == "state_scoring":
        if raw_req.get("species") == "human" and _is_ifn_beta(raw_req.get("perturbation_targets")):
            from praxis_virtualcell.predictors.state.cell_state import run_cellstate_case
            return run_cellstate_case
        # 非 human 或非 IFN-β(emt 的 gene→state、fate 的 mouse state)→ 落 UnsupportedEngine → 诚实 abstain(不接刻画工具)
```
③ `map_case_delta` 在 embedding 分支后加 state_scoring(per_cell_type 判别键):
```python
    if engine == "state_scoring":
        if "per_cell_type" in report.raw_output:   # cell_state:整体 ISG 组间 Cohen's d
            return [round(report.raw_output["cohens_d"], 4)]
        raise UnsupportedEngine(f"state_scoring map_case_delta 未支持 raw_output 形状: {sorted(report.raw_output)}")
```

- [ ] **Step 4: 跑测试验证通过 + 全 B3 单元回归**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "state_scoring or embedding or pathway or ifn or dispatch_runner or map_case_delta" -v`
Expected: 全 PASS。

- [ ] **Step 5: ruff + commit**

Run: `.venv/bin/ruff check praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` → All checks passed。
```bash
git add praxis_virtualcell/predictors/case_dispatch.py praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "feat(phase10b3): Task 3 state_scoring/cell_state 窄门 human+IFN-β 接入(per_cell_type cohens_d delta)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: 端到端真实预测 + emt/fate/spatial limitation 诚实 abstain

**Files:** Test `tests/phase10/test_t10_2_module_contracts.py`(端到端,不碰生产代码)

- [ ] **Step 1: 写端到端测试**(追加)

```python
def test_human_drug_signature_real_e2e():
    req = {"species": "human", "perturbation_type": "drug", "perturbation_targets": ["geldanamycin"],
           "input_modality": "scRNA", "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is False
    assert "CaseRunner" in sr["provenance"]["models_used"]
    assert sr["prediction"]["delta"] == [2.646]          # HSP90i MOA 富集


def test_human_drug_dose_real_e2e():
    req = {"species": "human", "perturbation_type": "drug", "perturbation_targets": ["geldanamycin"],
           "dose": "10uM", "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is False
    assert sr["prediction"]["delta"] == [0.9]            # dose-recall Spearman


def test_human_ifn_cellstate_real_e2e():
    req = {"species": "human", "perturbation_type": "ligand", "perturbation_targets": ["IFNB1"],
           "input_modality": "scRNA", "output_modality": "state", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    sr = out["structured_report"]
    assert out["reliability_decision"]["abstain"] is False
    assert "CaseRunner" in sr["provenance"]["models_used"]
    assert sr["prediction"]["delta"] == [2.485]          # ISG 组间 Cohen's d


def test_drug_not_in_db_abstains_honestly():
    req = {"species": "human", "perturbation_type": "drug", "perturbation_targets": ["notadrug123"],
           "input_modality": "scRNA", "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    assert out["reliability_decision"]["abstain"] is True
    assert out["structured_report"]["prediction"] is None
    assert "CaseRunner" in out["structured_report"]["provenance"]["models_rejected"]


def test_limitation_paths_abstain_honestly():
    # emt(human gene→state,非 IFN)、fate(mouse state)、mouse+drug(物种守卫)→ 均诚实 abstain,不虚构固定数据
    cases = [
        {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["ZEB1"], "output_modality": "state"},
        {"species": "mouse", "perturbation_type": "gene", "perturbation_targets": ["Gata1"], "output_modality": "state"},
        {"species": "mouse", "perturbation_type": "drug", "perturbation_targets": ["geldanamycin"], "output_modality": "delta_expression"},
    ]
    for c in cases:
        req = {**c, "input_modality": "scRNA", "task_type": "predict_delta_expression"}
        out = run_query(dict(req), config=_CFG)
        assert out["reliability_decision"]["abstain"] is True, c
        assert out["structured_report"]["prediction"] is None, c
```

- [ ] **Step 2: 跑测试验证通过**(真跑 LINCS/Kang 查询,几秒)

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py -k "drug_signature_real or drug_dose_real or ifn_cellstate_real or drug_not_in_db or limitation_paths" -v`
Expected: 5 passed。**若数值/abstain 不符,不改测试迁就——停下报告实际值排查**(尤其 limitation 路径必须真 abstain,若某个返回了固定数据的"真实预测"= 过度声称漏网,停下)。

- [ ] **Step 3: ruff + commit**

Run: `.venv/bin/ruff check praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py` → All checks passed。
```bash
git add praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py
git commit -m "test(phase10b3): Task 4 端到端真实(drug 签名/剂量/IFN-β 状态)+ emt/fate/mouse limitation 诚实 abstain

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: 字节等价 + mock 不变 + 受影响测试 + 全量回归

**Files:** Test `tests/phase10/test_t10_2_module_contracts.py`;可能 Modify 受影响既有测试(执行时定位)

- [ ] **Step 1: 补字节等价 + mock 不变测试**(追加)

```python
def test_b3_real_requests_rerun_byte_equal():
    for req in (
        {"species": "human", "perturbation_type": "drug", "perturbation_targets": ["geldanamycin"],
         "input_modality": "scRNA", "output_modality": "delta_expression", "task_type": "predict_delta_expression"},
        {"species": "human", "perturbation_type": "ligand", "perturbation_targets": ["IFNB1"],
         "input_modality": "scRNA", "output_modality": "state", "task_type": "predict_delta_expression"}):
        outs = [run_query(dict(req), config=_CFG) for _ in range(3)]
        assert len({_canon(o["structured_report"]) for o in outs}) == 1
        assert len({_canon(o["trace"]) for o in outs}) == 1


def test_b3_mock_expression_gene_unchanged():
    # human gene→delta_expression 仍走 donor_predictor 3 mock(embedding/state_scoring 只吃 drug/state)
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression", "task_type": "predict_delta_expression"}
    out = run_query(dict(req), config=_CFG)
    used = out["structured_report"]["provenance"]["models_used"]
    assert "CaseRunner" not in used
    assert set(used) <= {"MockLinear", "MockCPA", "MockGEARS"}
```

- [ ] **Step 2: 跑全量定位受影响测试**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider 2>&1 | tail -30`
Expected: 新测试全 PASS。**可能有既有测试因 human drug/state 从 mock→真实/abstain 而 FAIL**,记录清单。(用别的命令得到一堆 ML/远端 checkpoint failed 是环境依赖,以规范命令为准,不算受影响。)

- [ ] **Step 3: 逐个核对受影响测试**

对每个 FAIL:确认属"接入真实 runner(drug/IFN-β state 真实)或诚实 abstain(emt/fate/mouse/spatial limitation)"的语义提升——核对请求路径 + 结果合理。更新断言。**若发现 mock 的 gene→expression(donor_predictor)行为变、或某 limitation 路径返回了固定数据"真实预测" = 真实回归/过度声称漏网,停下报 BLOCKED,不改测试迁就。**

- [ ] **Step 4: 全量回归复绿**

Run: `cd /Volumes/T7/PRAXIS-virtualcell && PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider 2>&1 | tail -3`
Expected: 0 failed。

- [ ] **Step 5: ruff + commit**

Run: `.venv/bin/ruff check praxis_virtualcell/tests/phase10/test_t10_2_module_contracts.py`(+ 受影响测试文件)→ All checks passed。
```bash
git add -A praxis_virtualcell/tests
git commit -m "test(phase10b3): Task 5 字节等价(drug/IFN-β 真实)+ mock 不变 + 受影响测试更新 + 全量回归

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
(台账勾账 + emt/fate/spatial/M6 的 limitation 记录由控制器另做,implementer 不碰 UPGRADE-PROGRESS.md。)

---

## Self-Review(计划 vs spec 覆盖)

- **spec §3.1 drug_signature** → Task 1 ✅
- **spec §3.2 drug_dose(dose 判别)** → Task 2 ✅
- **spec §3.3 cell_state 窄门 IFN-β** → Task 3 ✅
- **spec §二 架构(REAL_ENGINES+dispatch+map 三处 + human 守卫 + IFN 门)** → Task 1-3 ✅
- **spec §一/五 emt/fate/spatial limitation 诚实 abstain** → Task 4(limitation_paths)+ Task 5 ✅
- **spec §六 测试(3 正例真实 + limitation abstain + 字节等价 + mock 不变)** → Task 4/5 ✅
- **spec §八 完成标准** → Task 1-5 + 控制器勾账 ✅

命名一致:dispatch_runner/map_case_delta/REAL_ENGINES/`_is_ifn_beta`/判别键(per_drug/dose_response/per_cell_type)跨 task 一致。无占位。全 human-guarded(防物种泄漏);emt/fate/spatial 不接(类别错误 limitation);delta 语义靠 provenance_boundary 透传。
