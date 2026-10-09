# Phase 8 网站 7 步 + Linux Release 实施计划(→ v1.3 public release)

> **For agentic workers:** REQUIRED SUB-SKILL: 用 superpowers:subagent-driven-development 逐 task 实现。步骤用 `- [ ]` 复选框跟踪。
> 本计划由 autopilot 控制器对着**真实代码**展开(读了 module_plan.py / modules.py / main.py / runtime_service.py / api_schema.py / report_markdown.py / job_store.py / core/runtime.py / App.tsx / api.ts / 三个测试文件),无臆测。

**Goal:** 完成 v1.3 公开发布最后一相——把八模块路由结果贯通到后端只读端点、report.md、7 步网站前端,并用 Linux/Docker smoke(在 .53 真跑)证明可发行。

**Architecture:** 纯增量,不推倒 PRAXIS 内核。后端只加**只读端点 + 展示层字段**(module_plan 已在 `structured_report["provenance"]["module_plan"]`,只暴露不重算);report.md 加一个 Module Routing 附加段(仿现有"证据记录/验证计划"子段,不打乱 9 段编号);前端把 3 步扩成 7 步纯展示流程(不碰科学决策)。所有科学裁决仍由确定性 runtime 完成。

**Tech Stack:** Python 3.11+ / FastAPI / pydantic / pytest+TestClient(后端 TDD);React 19 + Vite + TypeScript + oxlint(前端 build-verified,**不引入测试栈**);Docker / bash(Linux release smoke)。

---

## 决策与边界(展开前已定,写进每个 task)

**三项用户决策(2026-07-06):**
1. **网站深度 = 完整 7 步流程重构**:`App.tsx` 状态机 3 步 → 7 步,新增 view 组件。
2. **前端不引入测试栈**:前端 view 无单元测试;质量靠 `tsc build` + `oxlint` + 后端端点契约 TDD + 手动验证清单。因此**前端 task 用 build-verified 模板**(改代码 → build → lint → 手验清单 → commit),后端/smoke task 用**标准 TDD 模板**(先写失败测试)。
3. **Linux/Docker smoke = 本次在 .53 真跑绿**:`test_linux_docker_smoke.py` 标 `@pytest.mark.integration`,mac 本地 skip(计入 skipped);Phase 8 完成闸门要求在 .53(`zkyd@10.102.106.53`,远端 `/home/zkyd/data1/mzy/PRAXIS-virtualcell`)真跑 `docker build`+`run`+smoke 10 条绿。

**已在 v0.6/v0.8 落地、本 Phase 不重做**(Linux 调研查证,附 commit):打包 `pyproject.toml`/`MANIFEST.in`/wheel offline smoke(9eea1dd);`deploy/vc/{Dockerfile,start.sh,check_install.sh}` + INSTALL/USER-GUIDE/EXAMPLES(93c8ea6);cell_catalog 12 预设 + `/api/options` + ConfirmView 下拉(b95b0df/6e444d3);report.md renderer 全链路(858fcb4);`test_packaging.py`(2)/`test_deploy_*.py`(4)已绿。**本 Phase 只做剩余增量。**

**7 步流程设计**(纯前端展示,不碰核心;不新增任何"重算科学决策"的端点):

| 步 | Step state | 内容 | 数据来源 |
|---|---|---|---|
| 1 | `ask` | 自然语言输入(现有 AskView) | POST /api/parse |
| 2 | `parse_review` | 核对解析结果 candidate_request/assumptions/missing(**新** ParseReviewView) | 上一步 parse 结果(前端 state) |
| 3 | `confirm` | 编辑 species/cell_type/perturbation/targets + cell preset(现有 ConfirmView,改为进 module_context 而非直接 run) | GET /api/options |
| 4 | `module_context` | 展示**预期**涉及的模块(该 species 的模块目录 + cell preset 的 supported_modules,静态,不跑管线)(**新** ModuleContextView) | GET /api/modules + cell preset.modules |
| 5 | `run_confirm` | 最终汇总 + LLM 报告开关 + Run 按钮 → createJob(**新** RunConfirmView) | POST /api/jobs |
| 6 | `result` | 报告主体(summary/prediction/governance)+ **Module Routing 实际结果块**(run 后真实 module_plan) | GET /api/reports/{id} + /module-plan |
| 7 | `advanced` | 高级:agent trace + provenance(现有 ResultView 后两 tab 独立成步)(**新** AdvancedView 或复用) | GET /api/reports/{id}/trace + /provenance |

> ⚠️ 设计取舍(留痕供 review):module_plan 是 run_query 的产物,不能在 run 前"预览真实路由"而不跑管线。为守红线(前端只读、不碰核心、不加重算端点),步 4 用**静态模块目录 + cell preset 的 supported_modules** 做"预期模块"展示,步 6 才展示 run 后的**实际** module_plan。若用户要"运行前预览真实路由",需另立子计划加核心端点——本计划不做。

**红线(§RED-LINES,每个 task 守):**
1. OFFLINE 零 LLM:默认 `mode=OFFLINE`/`llm_enabled=False`,`assert_llm_boundaries` 三 flag 恒 False;新端点/新段/前端全程零 LLM。
2. LLM 不越权;module_plan/provenance/prediction 只读暴露,不重算、不改裁决。
3. 只在 `praxis_virtualcell/tests` 工作,不碰根 `tests/`(~1398 继承测试)。
4. 不迁就:测试与现有行为不符 → 特征化 pin 真值;真 bug 则 BLOCKED,绝不改源码逻辑迁就测试。
5. 增量复用不推倒:module 展示层不引入新词汇/治理权威(单一真相源仍在 modules.py / route_table / reliability);cell_catalog 是只读展示。
6. 提交纪律:每 task 一提交,删 `._*`,加 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`,在 `feat/v0.9-phase0-module-core` 提交;`push_authorized=true` 但只 push 分支不 push tag;Task 8.10 需 push→.53 pull 真跑。

**房规(每个实现 subagent):** venv=`.venv`;测试口径 `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`;前端在 `praxis_vc_react/` 下 `npm run build` + `npm run lint`;commit 前删 `._*`;不动根 `tests/`。

---

## File Structure

**后端(新增/修改,TDD):**
- Modify `praxis_virtualcell/catalogs/cell_catalog.yaml` — 每 preset 加可选 `modules: [<id>...]`
- Modify `praxis_virtualcell/catalogs/__init__.py` — `load_cell_presets` 加 modules 白名单校验
- Modify `praxis_vc_api/services/runtime_service.py` — 加 `modules()` / `module_plan(job_id)`
- Modify `praxis_vc_api/main.py` — 加 `GET /api/modules` / `GET /api/reports/{id}/module-plan`
- Modify `praxis_virtualcell/io/report_markdown.py` — 加"模块路由(Module Routing)"附加段
- Test `praxis_virtualcell/tests/test_cell_catalog.py`(扩)/ `test_api.py`(扩)/ `test_report_markdown.py`(扩到 30)/ `test_modules_api.py`(新,可选拆分)

**前端(修改/新增,build-verified 无测试):**
- Modify `praxis_vc_react/src/api.ts` — 加 `getModules()` / `getModulePlan()` + 类型
- Modify `praxis_vc_react/src/App.tsx` — Step 3→7 状态机
- Create `praxis_vc_react/src/views/ParseReviewView.tsx`
- Create `praxis_vc_react/src/views/ModuleContextView.tsx`
- Create `praxis_vc_react/src/views/RunConfirmView.tsx`
- Modify `praxis_vc_react/src/views/ConfirmView.tsx` — 出口改为进 module_context
- Modify `praxis_vc_react/src/views/ResultView.tsx` — 加 Module Routing 块 + advanced 拆分
- Modify `praxis_vc_react/src/App.css` — 新步骤/进度条样式

**Linux release(TDD + .53):**
- Create `praxis_virtualcell/tests/test_linux_docker_smoke.py` — 10 条,标 integration

---

## Task 8.1: cell_catalog 加 module 元数据 + loader 白名单校验(TDD)

**Files:**
- Modify: `praxis_virtualcell/catalogs/cell_catalog.yaml`
- Modify: `praxis_virtualcell/catalogs/__init__.py:14-21`
- Test: `praxis_virtualcell/tests/test_cell_catalog.py`

**背景(真实代码):** `load_cell_presets()` 现在只校验 `species ∈ SUPPORTED_SPECIES`。module 是**可选展示字段**;单一真相源是 `biological_modules.modules.MODULE_ORDER`(8 值)。

- [ ] **Step 1: 写失败测试**(追加到 `test_cell_catalog.py` 末尾)

```python
def test_preset_modules_within_whitelist():
    """预设若声明 modules,每个必须 ∈ MODULE_ORDER(防展示层与单一真相源漂移)。"""
    from praxis_virtualcell.biological_modules.modules import MODULE_ORDER
    for p in load_cell_presets():
        mods = p.get("modules") or []
        assert isinstance(mods, list), f"{p['id']} modules 非 list"
        for m in mods:
            assert m in MODULE_ORDER, f"{p['id']} module 越白名单: {m}"


def test_every_preset_has_modules():
    """本 Phase 起每个预设都标注 supported_modules(前端 module_context 步消费)。"""
    for p in load_cell_presets():
        assert p.get("modules"), f"{p['id']} 缺 modules 标注"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_cell_catalog.py -q`
Expected: FAIL(`test_every_preset_has_modules` 因现 yaml 无 modules 字段而 fail;`test_preset_modules_within_whitelist` pass 因当前为空)

- [ ] **Step 3: 给 12 个预设加 modules 字段**(编辑 `cell_catalog.yaml`,每行末尾加 `modules`)

规则(依 modules.py 的 engines 映射,守铁律 bacteria/yeast 不套 M8 自噬/M6 niche):
- human/mouse 代谢+基因类:`[genetic_hub, mitochondrial_energy_metabolism, cytoplasmic_metabolism, stress_processor]`
- 例(human_k562 基因扰动):`modules: [genetic_hub, cytoplasmic_metabolism, stress_processor]`
- bacteria(E. coli,代谢为主):`modules: [mitochondrial_energy_metabolism, cytoplasmic_metabolism, biosynthetic_network]`(M3 在 bacteria 显示为 Energy metabolism/redox,**不套 M8**)
- yeast:`modules: [genetic_hub, mitochondrial_energy_metabolism, cytoplasmic_metabolism]`(**不套 M6 组织 niche**)

逐条示例(完整替换,保留原字段):
```yaml
  - {id: human_k562, species: human, cell_type: K562, label: "K562 — human CML (Norman perturb-seq)", example_perturbation_type: gene, example_targets: [AHR, GATA1], modules: [genetic_hub, cytoplasmic_metabolism, stress_processor]}
  - {id: human_pbmc, species: human, cell_type: PBMC, label: "PBMC — human immune (Kang IFN-β)", example_perturbation_type: gene, example_targets: [STAT1], modules: [genetic_hub, stress_processor]}
  - {id: human_a549, species: human, cell_type: A549, label: "A549 — human lung adenocarcinoma", example_perturbation_type: drug, example_targets: [vorinostat], modules: [stress_processor, cytoplasmic_metabolism]}
  - {id: human_hek293t, species: human, cell_type: HEK293T, label: "HEK293T — human embryonic kidney", example_perturbation_type: gene, example_targets: [TP53], modules: [genetic_hub, stress_processor]}
  - {id: human_ipsc, species: human, cell_type: iPSC, label: "iPSC — human induced pluripotent", example_perturbation_type: gene, example_targets: [SNAI1], modules: [genetic_hub, cytoskeletal_framework]}
  - {id: mouse_tcell, species: mouse, cell_type: T cell, label: "T cell — mouse (ortholog 迁移)", example_perturbation_type: gene, example_targets: [Gata1], modules: [genetic_hub, stress_processor]}
  - {id: mouse_hematopoietic, species: mouse, cell_type: hematopoietic, label: "Hematopoietic — mouse (Paul15 分化)", example_perturbation_type: gene, example_targets: [Gata1], modules: [genetic_hub, cytoplasmic_metabolism]}
  - {id: mouse_fibroblast, species: mouse, cell_type: fibroblast, label: "Fibroblast — mouse", example_perturbation_type: gene, example_targets: [Myc], modules: [genetic_hub, cytoskeletal_framework]}
  - {id: yeast_scerevisiae, species: yeast, cell_type: S. cerevisiae, label: "S. cerevisiae — yeast GEM (Yeast8)", example_perturbation_type: gene, example_targets: [YBR166C], modules: [genetic_hub, mitochondrial_energy_metabolism, cytoplasmic_metabolism]}
  - {id: yeast_carbon, species: yeast, cell_type: S. cerevisiae, label: "S. cerevisiae — 碳源切换 (medium)", example_perturbation_type: medium, example_targets: [], modules: [mitochondrial_energy_metabolism, cytoplasmic_metabolism]}
  - {id: ecoli_iml1515, species: bacteria, cell_type: E. coli, label: "E. coli — iML1515 GEM (KO 生长)", example_perturbation_type: gene, example_targets: [b0720], modules: [mitochondrial_energy_metabolism, cytoplasmic_metabolism, biosynthetic_network]}
  - {id: ecoli_antibiotic, species: bacteria, cell_type: E. coli, label: "E. coli — 抗生素 (靶代谢 FBA)", example_perturbation_type: drug, example_targets: [trimethoprim], modules: [mitochondrial_energy_metabolism, cytoplasmic_metabolism]}
```

- [ ] **Step 4: loader 加 modules 白名单校验**(编辑 `catalogs/__init__.py` 的 `load_cell_presets`)

在现有 species 校验后加:
```python
def load_cell_presets() -> list[dict]:
    """读 cell_catalog.yaml 的 presets。校验 species ∈ SUPPORTED_SPECIES + modules ∈ MODULE_ORDER
    (防与单一真相源漂移)。"""
    from praxis_virtualcell.biological_modules.modules import MODULE_ORDER
    doc = yaml.safe_load(_CATALOG.read_text(encoding="utf-8")) or {}
    presets = doc.get("presets", [])
    bad = [p["id"] for p in presets if p.get("species") not in SUPPORTED_SPECIES]
    if bad:
        raise ValueError(f"cell_catalog 预设 species 越白名单:{bad}")
    bad_mod = [(p["id"], m) for p in presets for m in (p.get("modules") or [])
               if m not in MODULE_ORDER]
    if bad_mod:
        raise ValueError(f"cell_catalog 预设 module 越白名单:{bad_mod}")
    return presets
```

- [ ] **Step 5: 跑测试确认通过 + 全量回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_cell_catalog.py praxis_virtualcell/tests/test_api.py -q`
Expected: PASS(cell_catalog 6 条全绿;test_options 仍绿——modules 是附加字段不破坏)

- [ ] **Step 6: 提交**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/catalogs/cell_catalog.yaml praxis_virtualcell/catalogs/__init__.py praxis_virtualcell/tests/test_cell_catalog.py
git commit -m "feat(phase8): cell_catalog 加 module 元数据 + loader 白名单校验

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8.2: `GET /api/modules` 八模块目录端点(TDD)

**Files:**
- Modify: `praxis_vc_api/services/runtime_service.py`
- Modify: `praxis_vc_api/main.py:43-46`(仿 options 端点)
- Test: `praxis_virtualcell/tests/test_api.py`

**背景(真实代码):** `modules.py` 有 `MODULE_ORDER`(8)+ `MODULES[id]={code,display_name,engines,pillars}` + `display_name(id, species=)`(bacteria M3 别名)。端点只读暴露,单一真相源不动。

- [ ] **Step 1: 写失败测试**(追加 `test_api.py`)

```python
def test_modules_catalog(client):
    d = client.get("/api/modules").json()
    mods = d["modules"]
    assert len(mods) == 8
    codes = [m["code"] for m in mods]
    assert codes == ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"]  # MODULE_ORDER 顺序
    m2 = next(m for m in mods if m["code"] == "M2")
    assert m2["id"] == "genetic_hub" and m2["display_name"] == "Genetic Hub"
    assert "donor_predictor" in m2["engines"]
    assert "pillars" in m2 and isinstance(m2["pillars"], list)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_api.py::test_modules_catalog -q`
Expected: FAIL(404,端点不存在)

- [ ] **Step 3: runtime_service 加 modules()**(追加到 `runtime_service.py`)

```python
def modules() -> dict:
    """八模块目录(只读展示)。单一真相源 = biological_modules.modules,前端 module_context 步消费。"""
    from praxis_virtualcell.biological_modules import modules as M
    return {"modules": [
        {"id": mid, "code": M.MODULES[mid]["code"],
         "display_name": M.MODULES[mid]["display_name"],
         "engines": list(M.MODULES[mid]["engines"]),
         "pillars": list(M.MODULES[mid]["pillars"])}
        for mid in M.MODULE_ORDER
    ]}
```

- [ ] **Step 4: main.py 加端点**(在 `/api/options` 后)

```python
@app.get("/api/modules")
def modules():
    """八模块目录(只读):M1–M8 的 id/code/display_name/engines/pillars。单一真相源 modules.py。"""
    return svc.modules()
```

- [ ] **Step 5: 跑测试确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_api.py -q`
Expected: PASS(含新 test_modules_catalog)

- [ ] **Step 6: 提交**

```bash
find . -name '._*' -delete
git add praxis_vc_api/services/runtime_service.py praxis_vc_api/main.py praxis_virtualcell/tests/test_api.py
git commit -m "feat(phase8): GET /api/modules 八模块目录只读端点

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8.3: `GET /api/reports/{job_id}/module-plan` 端点(TDD)

**Files:**
- Modify: `praxis_vc_api/services/runtime_service.py`
- Modify: `praxis_vc_api/main.py`(仿 provenance 端点 94-100)
- Test: `praxis_virtualcell/tests/test_api.py`

**背景(硬确认路径):** module_plan 落在 `structured_report["provenance"]["module_plan"]`(runtime.py:103;job_store 落 report.json)。`_is_routable` 旁路才产(applicable 非空 且 targets 非空),故**须 fail-closed**:缺则返回空 dict,不 500。job 不存在 → 404(仿现有端点 catch FileNotFoundError)。

- [ ] **Step 1: 写失败测试**(追加 `test_api.py`)

```python
def test_module_plan_endpoint(client):
    # 可路由请求(human + 有 targets)→ 应产 module_plan
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": ["AHR"],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    jid = client.post("/api/jobs", json={"request": req, "mode": "offline"}).json()["job_id"]
    r = client.get(f"/api/reports/{jid}/module-plan")
    assert r.status_code == 200
    mp = r.json()["module_plan"]
    assert mp.get("primary") and "entries" in mp and "overall_verdict" in mp


def test_module_plan_missing_is_empty_not_500(client):
    # 不可路由请求(空 targets → abstain,无 module_plan)→ 空 dict,不崩
    req = {"species": "human", "perturbation_type": "gene", "perturbation_targets": [],
           "input_modality": "scRNA", "output_modality": "delta_expression",
           "task_type": "predict_delta_expression"}
    jid = client.post("/api/jobs", json={"request": req, "mode": "offline"}).json()["job_id"]
    r = client.get(f"/api/reports/{jid}/module-plan")
    assert r.status_code == 200
    assert r.json()["module_plan"] == {}


def test_module_plan_404(client):
    assert client.get("/api/reports/nope/module-plan").status_code == 404
```

- [ ] **Step 2: 跑测试确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_api.py -k module_plan -q`
Expected: FAIL(404 端点不存在)

> ⚠️ 实现前**亲验**:跑一个 human+AHR job,`JobStore(runs).load(jid)["report"]["provenance"]` 里是否有 `module_plan` 键。若实际路径不同(如顶层 provenance),以实读为准调整 `module_plan()` 取值路径——**不改 runtime/job_store 源码**,只在 service 层适配。

- [ ] **Step 3: runtime_service 加 module_plan()**

```python
def module_plan(job_id: str) -> dict:
    """从落盘 job 的 structured_report.provenance 提取 module_plan(只读)。
    缺失(abstain/不可路由 job)→ 空 dict,fail-closed 不重算。job 不存在 → FileNotFoundError。"""
    job = JobStore(RUNS_DIR).load(job_id)   # 缺 → FileNotFoundError
    report = job.get("report") or {}
    prov = report.get("provenance") or job.get("provenance") or {}
    return {"module_plan": prov.get("module_plan") or {}}
```

- [ ] **Step 4: main.py 加端点**(在 provenance 端点后)

```python
@app.get("/api/reports/{job_id}/module-plan")
def module_plan(job_id: str):
    """该 job 的实际模块路由结果(只读):primary/secondary/entries/overall_verdict。
    不可路由 job 返回空 module_plan,不重算。"""
    try:
        return svc.module_plan(job_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="job not found") from e
```

- [ ] **Step 5: 跑测试确认通过 + API 全量**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_api.py -q`
Expected: PASS(全部 API 测试含 3 条新)

- [ ] **Step 6: 提交**

```bash
find . -name '._*' -delete
git add praxis_vc_api/services/runtime_service.py praxis_vc_api/main.py praxis_virtualcell/tests/test_api.py
git commit -m "feat(phase8): GET /api/reports/{id}/module-plan 只读端点(fail-closed)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8.4: report.md 加"模块路由"附加段 + 首批段测试(TDD)

**Files:**
- Modify: `praxis_virtualcell/io/report_markdown.py`(在 §3 Routing Decision 后加子段)
- Test: `praxis_virtualcell/tests/test_report_markdown.py`

**背景(真实代码):** renderer 现 9 段 + 2 子段(证据记录/验证计划,均 `###` 附加不占编号)。module_plan **完全没进 report.md**。仿现有子段风格加"### 模块路由(Module Routing)",读 `prov.get("module_plan")`,缺则标 N/A 不崩,**不打乱 9 段编号**。`prov = report.get("provenance") or job.get("provenance")` 已在文件顶部。

- [ ] **Step 1: 写失败测试**(追加 `test_report_markdown.py`;新 fixture）

```python
_WITH_MODULE_PLAN = {
    "mode": "offline",
    "request": {"request_id": "mp_ahr", "species": "human", "cell_type": "K562",
                "perturbation_type": "gene", "perturbation_targets": ["AHR"],
                "task_type": "predict_delta_expression"},
    "report": {
        "request_id": "mp_ahr", "abstain": False, "reliability": "high",
        "prediction": {"delta": [0.3]}, "models_used": ["MockLinear"],
        "models_rejected": [], "models_failed": [], "abstain_reasons": [],
        "downgrade_reasons": [], "failed_checks": [], "model_disagreement": None,
        "critic_violations": [], "caution_flags": {}, "learned_reliability": None,
        "provenance": {"n_messages": 20, "rules_referenced": [], "rules_hit": [],
                       "ortholog_cautions": {}, "rejection_reasons": {},
                       "module_plan": {
                           "species": "human", "primary": "genetic_hub",
                           "secondary": ["stress_processor"], "overall_verdict": "accept",
                           "entries": [
                               {"module": "genetic_hub", "display_name": "Genetic Hub",
                                "role": "primary", "engine": "donor_predictor",
                                "route_disposition": "accept", "species_support": "supported",
                                "species_verdict": "accept", "verdict": "accept",
                                "mismatch": None, "caution_flags": [], "available_models": []},
                               {"module": "stress_processor", "display_name": "Stress Processor",
                                "role": "secondary", "engine": "state_scoring",
                                "route_disposition": "caution", "species_support": "supported",
                                "species_verdict": "accept", "verdict": "caution",
                                "mismatch": None, "caution_flags": [], "available_models": []}],
                           "notes": []}},
    },
}


def test_module_routing_section_present():
    md = render_report_md(_WITH_MODULE_PLAN)
    assert "模块路由" in md or "Module Routing" in md
    assert "genetic_hub" in md or "Genetic Hub" in md   # primary 出现
    assert "stress_processor" in md or "Stress Processor" in md  # secondary 出现
    assert "primary" in md and "secondary" in md


def test_module_routing_missing_shows_na():
    """无 module_plan(abstain/旧 job)→ 标 N/A,不崩,9 段仍在。"""
    md = render_report_md(_ACCEPT)   # _ACCEPT 无 module_plan
    assert "模块路由" in md or "Module Routing" in md
    assert "N/A" in md
    for s in _SECTIONS:
        assert s in md


def test_module_routing_does_not_break_nine_sections():
    md = render_report_md(_WITH_MODULE_PLAN)
    for s in _SECTIONS:
        assert s in md, f"缺段:{s}"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_report_markdown.py -k module_routing -q`
Expected: FAIL(段不存在)

- [ ] **Step 3: 实现 Module Routing 子段**(在 report_markdown.py §3 Routing Decision 段末尾 `w("")` 后、§4 前插入)

```python
    # 模块路由(Phase 8:module_plan 展示层。读现有 provenance.module_plan,缺则 N/A,不重算/不打乱 9 段编号)
    mp = prov.get("module_plan") or {}
    w("### 模块路由(Module Routing)")
    w("")
    if not mp:
        w(f"- primary module: `{_NA}`(无 module_plan:abstain/不可路由 job 或旧记录)")
    else:
        w(f"- primary module: `{mp.get('primary', _NA)}` · "
          f"secondary: `{_fmt_list(mp.get('secondary'))}` · "
          f"overall_verdict: **{mp.get('overall_verdict', _NA)}**")
        entries = mp.get("entries") or []
        if entries:
            w("- 模块裁决(module · role · verdict · mismatch):")
            for e in entries:
                w(f"  - `{e.get('module', _NA)}` · {e.get('role', _NA)} · "
                  f"**{e.get('verdict', _NA)}**"
                  + (f" · mismatch=`{e.get('mismatch')}`" if e.get('mismatch') else ""))
    w("")
    w("_模块路由是治理层之上的逻辑视图(读 module_plan artifact);M1–M8 映射现有 engine,"
      "verdict 取 route/species/mismatch 最保守,不重写裁决。_")
    w("")
```

- [ ] **Step 4: 跑测试确认通过 + 现有 report 测试不回归**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_report_markdown.py -q`
Expected: PASS(原 12 + 新 3,共 15;`test_reproducible_byte_identical`/`test_no_llm_import_in_module` 仍绿)

- [ ] **Step 5: 提交**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/io/report_markdown.py praxis_virtualcell/tests/test_report_markdown.py
git commit -m "feat(phase8): report.md 加模块路由段(读 module_plan,缺则 N/A 不崩)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8.5: report tests 扩到 30(module/evidence/多物种/provenance 一致)(TDD)

**Files:**
- Test: `praxis_virtualcell/tests/test_report_markdown.py`(现 15 → 30)

**背景:** 路线图目标"report tests 30"。现 15(12 原 + 3 Task8.4)。补 15 条,**纯测试新增,不改 renderer**(若发现 renderer 真缺陷 → BLOCKED 报告,不迁就)。覆盖:module routing 各态、evidence level E0–E5、多物种参数化、learning_queue 排序、provenance 键一致、mismatch 展示。

- [ ] **Step 1: 补齐测试到 30**(追加,给完整代码)

```python
import pytest  # 若文件未 import(现无),在文件顶部加


@pytest.mark.parametrize("species", ["human", "mouse", "yeast", "bacteria"])
def test_report_all_species_render_nine_sections(species):
    job = {"mode": "offline",
           "request": {"request_id": f"sp_{species}", "species": species, "cell_type": "X",
                       "perturbation_type": "gene", "perturbation_targets": ["G1"],
                       "task_type": "predict_delta_expression"},
           "report": {"request_id": f"sp_{species}", "abstain": False, "reliability": "medium",
                      "prediction": {"delta": [0.1]}, "models_used": ["MockLinear"],
                      "models_rejected": [], "models_failed": [], "abstain_reasons": [],
                      "downgrade_reasons": [], "failed_checks": [], "model_disagreement": None,
                      "critic_violations": [], "caution_flags": {}, "learned_reliability": None,
                      "provenance": {"n_messages": 10, "rules_referenced": [], "rules_hit": [],
                                     "ortholog_cautions": {}, "rejection_reasons": {}}}}
    md = render_report_md(job)
    for s in _SECTIONS:
        assert s in md
    if species != "human":
        assert species in md  # 非 human 进 Limitations


def test_non_human_species_downgrade_note_in_limitations():
    for sp in ("mouse", "yeast", "bacteria"):
        job = {"mode": "offline", "request": {"species": sp, "perturbation_targets": ["G"],
               "perturbation_type": "gene", "task_type": "predict_delta_expression"},
               "report": {"abstain": False, "reliability": "medium", "prediction": {"delta": [0.1]},
                          "models_used": ["MockLinear"], "provenance": {}}}
        md = render_report_md(job)
        assert "跨物种" in md or "ortholog" in md.lower()


def test_module_routing_caution_entry_verdict_shown():
    md = render_report_md(_WITH_MODULE_PLAN)
    assert "caution" in md  # secondary stress_processor verdict=caution


def test_module_routing_mismatch_rendered():
    job = {"mode": "offline", "request": {"species": "bacteria", "perturbation_targets": ["b0720"],
           "perturbation_type": "gene", "task_type": "predict_delta_expression"},
           "report": {"abstain": False, "reliability": "medium", "prediction": {"delta": [0.1]},
                      "models_used": ["MockLinear"],
                      "provenance": {"module_plan": {"species": "bacteria", "primary": "cytoplasmic_metabolism",
                          "secondary": [], "overall_verdict": "caution",
                          "entries": [{"module": "cytoplasmic_metabolism", "display_name": "Cytoplasmic Metabolism",
                              "role": "primary", "engine": "gem_fba", "route_disposition": "accept",
                              "species_support": "supported", "species_verdict": "accept",
                              "verdict": "caution", "mismatch": "biological_mismatch"}], "notes": []}}}}
    md = render_report_md(job)
    assert "mismatch" in md and "biological_mismatch" in md


def test_evidence_level_e2_in_domain_accept():
    job = dict(_WITH_MODULE_PLAN)
    job = {**_WITH_MODULE_PLAN,
           "report": {**_WITH_MODULE_PLAN["report"],
                      "provenance": {**_WITH_MODULE_PLAN["report"]["provenance"],
                                     "evidence_level": {"level": "E2", "ood_signal": "in_domain",
                                                        "rationale": ["matched_perturbation_data"],
                                                        "aligned_with_disposition": True}}}}
    md = render_report_md(job)
    assert "E2" in md and "in_domain" in md


@pytest.mark.parametrize("level", ["E0", "E1", "E3", "E5"])
def test_evidence_levels_render(level):
    job = {"mode": "offline", "request": {"species": "human", "perturbation_targets": ["AHR"],
           "perturbation_type": "gene", "task_type": "predict_delta_expression"},
           "report": {"abstain": False, "reliability": "medium", "prediction": {"delta": [0.1]},
                      "models_used": ["MockLinear"],
                      "provenance": {"evidence_level": {"level": level, "ood_signal": "unknown",
                                     "rationale": [], "aligned_with_disposition": True}}}}
    md = render_report_md(job)
    assert level in md


def test_learning_queue_sorted_top5_only():
    items = [{"candidate": f"c{i}", "module": "genetic_hub", "information_gain": float(i),
              "drivers": ["d"]} for i in range(7)]
    job = {"mode": "offline", "request": {"species": "human", "perturbation_targets": ["AHR"],
           "perturbation_type": "gene", "task_type": "predict_delta_expression"},
           "report": {"abstain": False, "reliability": "medium", "prediction": {"delta": [0.1]},
                      "models_used": ["MockLinear"],
                      "provenance": {"learning_queue": {"items": items, "notes": []}}}}
    md = render_report_md(job)
    assert "c0" in md  # 前 5 项渲染(renderer 取 items[:5];此测钉现有 top-5 行为)


def test_provenance_module_plan_and_evidence_coexist():
    job = {**_WITH_MODULE_PLAN,
           "report": {**_WITH_MODULE_PLAN["report"],
                      "provenance": {**_WITH_MODULE_PLAN["report"]["provenance"],
                                     "evidence_level": {"level": "E3", "ood_signal": "unknown",
                                                        "rationale": [], "aligned_with_disposition": True},
                                     "learning_queue": {"items": [], "notes": []}}}}
    md = render_report_md(job)
    assert ("模块路由" in md or "Module Routing" in md)
    assert "E3" in md
    assert "证据记录" in md or "Evidence Record" in md


def test_report_md_ends_with_newline():
    assert render_report_md(_WITH_MODULE_PLAN).endswith("\n")


def test_report_md_no_llm_in_module_plan_path():
    md = render_report_md(_WITH_MODULE_PLAN)
    assert "llm_used_for_prediction: `False`" in md


def test_empty_module_plan_entries_no_crash():
    job = {"mode": "offline", "request": {"species": "human", "perturbation_targets": ["AHR"],
           "perturbation_type": "gene", "task_type": "predict_delta_expression"},
           "report": {"abstain": False, "reliability": "high", "prediction": {"delta": [0.1]},
                      "models_used": ["MockLinear"],
                      "provenance": {"module_plan": {"species": "human", "primary": "genetic_hub",
                          "secondary": [], "overall_verdict": "accept", "entries": [], "notes": []}}}}
    md = render_report_md(job)
    assert "genetic_hub" in md  # primary 仍展示,即使 entries 空


def test_downgrade_with_module_plan_verdict_consistency():
    md = render_report_md(_WITH_MODULE_PLAN)
    # overall_verdict=accept 出现在模块路由段
    assert "overall_verdict: **accept**" in md


def test_reproducible_with_module_plan():
    assert render_report_md(_WITH_MODULE_PLAN) == render_report_md(_WITH_MODULE_PLAN)


def test_module_routing_section_after_routing_decision():
    md = render_report_md(_WITH_MODULE_PLAN)
    assert md.index("## 3. Routing Decision") < md.index("模块路由") < md.index("## 4. Result Summary")


def test_all_four_species_with_module_plan_no_crash():
    for sp in ("human", "mouse", "yeast", "bacteria"):
        job = {"mode": "offline", "request": {"species": sp, "perturbation_targets": ["G"],
               "perturbation_type": "gene", "task_type": "predict_delta_expression"},
               "report": {"abstain": False, "reliability": "medium", "prediction": {"delta": [0.1]},
                          "models_used": ["MockLinear"],
                          "provenance": {"module_plan": {"species": sp, "primary": "cytoplasmic_metabolism",
                              "secondary": [], "overall_verdict": "accept",
                              "entries": [{"module": "cytoplasmic_metabolism",
                                  "display_name": "Cytoplasmic Metabolism", "role": "primary",
                                  "engine": "gem_fba", "route_disposition": "accept",
                                  "species_support": "supported", "species_verdict": "accept",
                                  "verdict": "accept", "mismatch": None}], "notes": []}}}}
        md = render_report_md(job)
        assert "cytoplasmic_metabolism" in md
```

- [ ] **Step 2: 跑全量 report 测试并数条数**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_report_markdown.py -q`
Expected: PASS,collected ≥ 30(含 parametrize 展开)。若某测试 fail 揭示 renderer 真缺陷 → **BLOCKED 报告控制器,不改测试迁就**。

- [ ] **Step 3: 提交**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/tests/test_report_markdown.py
git commit -m "test(phase8): report tests 扩到 30(module/evidence/多物种/provenance 一致)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8.6: 前端 api.ts 加 module 端点封装 + 类型(build-verified)

**Files:**
- Modify: `praxis_vc_react/src/api.ts`
- Test: 无(前端不 TDD;验收 = `npm run build` + `npm run lint`)

**背景(真实代码):** `api.ts` 有 `req<T>` 助手 + 8 端点封装。`CellPreset` 缺 `modules` 字段。加 module 类型 + 两端点封装。

- [ ] **Step 1: 加类型 + 端点**(编辑 `api.ts`)

`CellPreset` 接口加 `modules?: string[];`。在 `Options` 接口后加:
```typescript
export interface ModuleInfo {
  id: string;
  code: string;
  display_name: string;
  engines: string[];
  pillars: string[];
}

export interface ModulePlanEntry {
  module: string;
  display_name: string;
  role: string;
  engine: string;
  route_disposition: string;
  species_support: string;
  species_verdict: string;
  verdict: string;
  mismatch: string | null;
  caution_flags: string[];
  data_gated: boolean;
  pillars: string[];
  available_models: string[];
  reason: string;
}

export interface ModulePlan {
  species: string;
  primary: string;
  secondary: string[];
  overall_verdict: string;
  entries: ModulePlanEntry[];
  notes: string[];
}
```

在 `getOptions()` 后加:
```typescript
export function getModules(): Promise<{ modules: ModuleInfo[] }> {
  return req<{ modules: ModuleInfo[] }>("/api/modules");
}

// 该 job 的实际模块路由结果(只读)。不可路由 job 返回空 module_plan。
export function getModulePlan(jobId: string): Promise<{ module_plan: ModulePlan | Record<string, never> }> {
  return req<{ module_plan: ModulePlan | Record<string, never> }>(
    `/api/reports/${encodeURIComponent(jobId)}/module-plan`);
}
```

- [ ] **Step 2: build + lint**

Run: `cd praxis_vc_react && npm run build && npm run lint`
Expected: tsc 无类型错;oxlint 无 error。

- [ ] **Step 3: 提交**

```bash
find . -name '._*' -delete
git add praxis_vc_react/src/api.ts
git commit -m "feat(phase8): 前端 api.ts 加 /api/modules + /module-plan 封装与类型

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8.7: 前端 App.tsx 3 步 → 7 步状态机骨架(build-verified)

**Files:**
- Modify: `praxis_vc_react/src/App.tsx`
- Test: 无(build-verified)

**背景(真实代码):** `App.tsx:9` `type Step = "ask" | "confirm" | "result"`,状态集中,view 条件渲染 72-96。本 task 只扩状态机 + 占位接线新步骤(新 view 在 8.8/8.9 建;此 task 用现有 view + 临时"下一步"按钮占位,保证每步可 build 通过并手动走通)。

- [ ] **Step 1: 扩 Step 类型 + 状态流**(编辑 App.tsx)

```typescript
type Step = "ask" | "parse_review" | "confirm" | "module_context" | "run_confirm" | "result" | "advanced";
```

条件渲染块改为(先用现有 view + 占位,8.8/8.9 替换 TODO 占位为真实 view):
```tsx
{step === "ask" && (
  <AskView mode={mode} onMode={setMode} onParsed={(r) => { setParseResult(r); setStep("parse_review"); }} />
)}
{step === "parse_review" && parseResult && (
  <ParseReviewView parseResult={parseResult} onBack={() => setStep("ask")} onNext={() => setStep("confirm")} />
)}
{step === "confirm" && parseResult && (
  <ConfirmView parseResult={parseResult} mode={mode}
    onBack={() => setStep("parse_review")}
    onConfirmed={(req) => { setConfirmedRequest(req); setStep("module_context"); }} />
)}
{step === "module_context" && confirmedRequest && (
  <ModuleContextView request={confirmedRequest} onBack={() => setStep("confirm")} onNext={() => setStep("run_confirm")} />
)}
{step === "run_confirm" && confirmedRequest && (
  <RunConfirmView request={confirmedRequest} mode={mode}
    onBack={() => setStep("module_context")}
    onRan={(id) => { setJobId(id); setStep("result"); loadJobs(); }} />
)}
{step === "result" && jobId && (
  <ResultView jobId={jobId} onReset={newQuery} resetLabel="＋ 新建查询"
    onAdvanced={() => setStep("advanced")} />
)}
{step === "advanced" && jobId && (
  <ResultView jobId={jobId} onReset={newQuery} resetLabel="＋ 新建查询" advanced onBack={() => setStep("result")} />
)}
```

加新 state:`const [confirmedRequest, setConfirmedRequest] = useState<Record<string, unknown> | null>(null);`
`newQuery()` 里加 `setConfirmedRequest(null);`。
import 新 view(8.8/8.9 创建前先建空占位组件避免 build 断,见 Step 2)。

> ⚠️ 契约变更:`ConfirmView` 的 `onRan` 改为 `onConfirmed(req)`(只交出 request,不再直接 createJob;run 移到 RunConfirmView)。此改动在 8.9 落 ConfirmView;本 task 先建 3 个占位组件让 build 通过。

- [ ] **Step 2: 建 3 个最小占位组件**(让 App.tsx 能 build;8.8/8.9 填实)

Create `praxis_vc_react/src/views/ParseReviewView.tsx`、`ModuleContextView.tsx`、`RunConfirmView.tsx` 各一个最小可编译占位(接口对齐上面 props),例:
```tsx
// ParseReviewView.tsx(占位,8.8 填实)
import type { ParseResult } from "../api";
export default function ParseReviewView(
  { onBack, onNext }: { parseResult: ParseResult; onBack: () => void; onNext: () => void }) {
  return (<div className="card"><h2>2 · 解析核对</h2>
    <button onClick={onBack}>返回</button><button onClick={onNext}>下一步</button></div>);
}
```
(ModuleContextView props:`{request; onBack; onNext}`;RunConfirmView props:`{request; mode; onBack; onRan}`。)
ConfirmView 暂保持现 `onRan`?否 —— 为让 App build,本 task 同步把 ConfirmView 的 `onRan` 改名 `onConfirmed`(签名 `(req)=>void`),内部**暂**仍 createJob 然后 `onConfirmed(request)`?**不行**(会双 run)。正确:本 task ConfirmView 只改 prop 名与出口,把 createJob 逻辑整段移除,onConfirmed 传出编辑好的 request(createJob 移到 8.9 RunConfirmView)。ConfirmView 完整改动在 8.9;若本 task 无法干净拆分,则**本 task 连 ConfirmView 出口一起改**并在 8.9 只补 RunConfirmView 的 createJob。实现 subagent 按能编译通过的最小一致改动组织。

- [ ] **Step 3: build + lint + 手动验证**

Run: `cd praxis_vc_react && npm run build && npm run lint`
手动验证清单(启动 `praxis-vc serve` 或 `npm run dev` 后):
- [ ] 7 步都能前进/后退,无白屏
- [ ] ask → parse_review → confirm → module_context → run_confirm → result → advanced 全走通
- [ ] Sidebar 历史 job 打开仍正常(openedJobId 分支未破坏)

- [ ] **Step 4: 提交**

```bash
find . -name '._*' -delete
git add praxis_vc_react/src/App.tsx praxis_vc_react/src/views/
git commit -m "feat(phase8): 前端 App 3步→7步状态机 + 新步骤占位组件

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8.8: ParseReviewView + ModuleContextView 实装(build-verified)

**Files:**
- Modify: `praxis_vc_react/src/views/ParseReviewView.tsx`
- Modify: `praxis_vc_react/src/views/ModuleContextView.tsx`
- Modify: `praxis_vc_react/src/App.css`(新步骤样式)
- Test: 无(build-verified)

- [ ] **Step 1: ParseReviewView 实装**——展示 `parseResult` 的 candidate_request(表格)、parser/llm_used/fallback_used、assumptions、missing_fields、errors,只读核对,"返回/下一步"。用现有 `pretty`(JSON)/`.err` 样式。给完整组件代码(读 ConfirmView 现有 metadata 展示 46-171 复用风格)。

- [ ] **Step 2: ModuleContextView 实装**——挂载时 `getModules()` 拿 8 模块目录;从 `request` 找对应 cell preset(或按 species 从 getOptions 的 cell_presets 匹配)拿 `modules`;展示"预期涉及模块"卡片网格(code + display_name + engines),对该 species 高亮 supported。**明确标注**"这是静态预期,实际路由结果在运行后(步 6)展示"。完整组件代码,含 `getModules().then(...).catch(()=>setModules([]))` 降级。

- [ ] **Step 3: build + lint + 手动验证**

Run: `cd praxis_vc_react && npm run build && npm run lint`
手动验证清单:
- [ ] parse_review 正确显示解析字段与 assumptions
- [ ] module_context 显示 8 模块 + 该 species 预期模块高亮,含"静态预期"说明
- [ ] getModules 失败时降级不白屏

- [ ] **Step 4: 提交**

```bash
find . -name '._*' -delete
git add praxis_vc_react/src/views/ParseReviewView.tsx praxis_vc_react/src/views/ModuleContextView.tsx praxis_vc_react/src/App.css
git commit -m "feat(phase8): ParseReviewView + ModuleContextView 实装(静态预期模块)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8.9: RunConfirmView + ConfirmView 出口改造 + ResultView module 块 + advanced 拆分 + dist 构建(build-verified)

**Files:**
- Modify: `praxis_vc_react/src/views/RunConfirmView.tsx`
- Modify: `praxis_vc_react/src/views/ConfirmView.tsx`(出口 onConfirmed,移除内部 createJob)
- Modify: `praxis_vc_react/src/views/ResultView.tsx`(加 Module Routing 块 + onAdvanced/advanced/onBack props)
- Test: 无(build-verified)

- [ ] **Step 1: ConfirmView 出口改造**——移除内部 `createJob`,改为编辑完成后 `onConfirmed(request)` 交出组装的 request(species/cell_type/perturbation_type/perturbation_targets/input_modality/output_modality/task_type,对齐 test_api 里 job request 形状)。保留下拉/预设/校验 UI。

- [ ] **Step 2: RunConfirmView 实装**——展示最终 request 汇总 + LLM 报告复选框(现 ConfirmView 173-180 的 enable_llm_report)+ "确认运行"按钮 → `createJob(request, mode, enableLlmReport)` → `onRan(job_id)`。busy/err 态。

- [ ] **Step 3: ResultView 加 Module Routing 块 + advanced**——挂载时并发 `getModulePlan(jobId)`;在 Report tab 现有 4 块(Summary/Prediction/Reliability/Boundary)后加"Module Routing"块:primary/secondary/overall_verdict + entries 表(module·role·verdict·mismatch);空 module_plan 显"该请求未产生模块路由(abstain/不可路由)"。props 加 `onAdvanced?`(result 步显"高级"按钮跳 advanced)、`advanced?`(为真时只显 trace+provenance 两 tab)、`onBack?`。保留现有 3 tab 逻辑,advanced 模式默认 Trace tab。

- [ ] **Step 4: build + lint + 构建 dist(生产同源托管)**

Run: `cd praxis_vc_react && npm run build && npm run lint`
Expected: `praxis_vc_react/dist/` 生成(main.py:116 会挂它到 `/`)。

手动验证清单(`praxis-vc serve` 后浏览器走完整 7 步 human+AHR):
- [ ] confirm 交出 request 后进 module_context(不再直接 run)
- [ ] run_confirm 的"确认运行"真正 createJob 并进 result
- [ ] result 的 Module Routing 块显示 primary=genetic_hub 等实际路由
- [ ] 空路由(空 targets abstain)result 的 module 块显降级文案不白屏
- [ ] advanced 步显 trace + provenance

- [ ] **Step 5: 提交**

```bash
find . -name '._*' -delete
git add praxis_vc_react/src/views/ praxis_vc_react/dist
git commit -m "feat(phase8): RunConfirmView + ConfirmView 出口 + ResultView 模块路由块 + dist 构建

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

> ⚠️ dist 是否入库:若仓库现约定 dist 不入库(检查 `.gitignore`),则 dist 不 add,改在 .53 部署时 `npm run build`;此 task 只保证本地 build 通过。实现 subagent 先查 `.gitignore` 决定。

---

## Task 8.10: Linux/Docker smoke 10 条 + .53 真跑(TDD + integration + 远端)

**Files:**
- Create: `praxis_virtualcell/tests/test_linux_docker_smoke.py`
- Test: 自身

**背景(真实代码):** `deploy/vc/{Dockerfile,start.sh,check_install.sh}` 已就位;`.github/workflows/ci.yml` 用 `pytest -m "not integration"`。smoke 标 `@pytest.mark.integration`,mac skip;.53 真跑。examples/ahr_k562.json 是 check_install.sh 用的 demo。**push_authorized=true**,本 task 需 push→.53 pull。

- [ ] **Step 1: 写 smoke 测试文件**(10 条,标 integration;缺 docker/非 Linux 自动 skip)

给完整 `test_linux_docker_smoke.py`:每条 `@pytest.mark.integration`;用 `shutil.which("docker")` / `sys.platform` 判据 skip;10 条 = python≥3.11 / `praxis-vc --help` / offline demo 产 report.md 且 ≥9 段 / wheel fresh-venv 安装 / `docker build -f deploy/vc/Dockerfile` 成功 / `docker run` 容器起 / port 8000 `/api/health` 200 / `/api/reports/{id}/markdown` 可下载 / 输出文件齐(report.md+report.json+trace.json+provenance.json)/ offline demo 运行时间基线(<60s)。用 `subprocess`,超时保护,容器测试用固定 tag + 末尾 `docker rm -f`。

- [ ] **Step 2: 本地(mac)跑确认 skip 不 fail**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_linux_docker_smoke.py -q`
Expected: 10 skipped(mac 无 Linux/Docker 判据),0 failed。skip 基线 29 → 39。

- [ ] **Step 3: 全量回归(mac)确认无破坏**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 0 failed;passed 计数 = 627 + 后端新增(Task 8.1–8.5);skipped = 29 + 10。

- [ ] **Step 4: 提交并 push**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/tests/test_linux_docker_smoke.py
git commit -m "test(phase8): Linux/Docker smoke 10 条(integration,mac skip/.53 真跑)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git push origin feat/v0.9-phase0-module-core
```

- [ ] **Step 5: .53 真跑 Docker smoke**(远端 `zkyd@10.102.106.53:/home/zkyd/data1/mzy/PRAXIS-virtualcell`)

```bash
ssh zkyd@10.102.106.53 'cd /home/zkyd/data1/mzy/PRAXIS-virtualcell && git pull && \
  .venv/bin/python -m pytest praxis_virtualcell/tests/test_linux_docker_smoke.py -m integration -q'
```
Expected: 10 passed(Linux + Docker 齐)。**留存输出**作 Phase 完成证据。若某条 fail 揭示 Dockerfile/发行真缺陷 → 修 deploy/ 配置(非科学核心)重跑;若涉不确定 → BLOCKED 报控制器。

---

## Task 8.11: Phase 8 完成闸门 + v1.3 tag(控制器执行)

- [ ] **Step 1: 全量回归(mac)** `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q` → 记录 X passed / Y skipped / **0 failed**。
- [ ] **Step 2: 红线核验**:OFFLINE 零 LLM 仍产 report.md;`assert_llm_boundaries` 三 flag False;golden unsafe-accept=0 / negative 无静默 accept 两 KPI 绿;根 `tests/` 零触碰(`git diff --stat main..HEAD -- tests/` 空)。
- [ ] **Step 3: 提交范围核验**:本 Phase 只动 `praxis_virtualcell/{catalogs,io,tests}` + `praxis_vc_api/*` + `praxis_vc_react/*` + `docs/`;管线/治理/LLM/predictors/agents 核心零触碰(`git diff --stat` 核对)。
- [ ] **Step 4: .53 Docker smoke 10 passed 证据**已留存(Task 8.10 Step 5)。
- [ ] **Step 5: v1.3 里程碑 tag**(v1.3 = Phase 8 后,里程碑打 tag):
```bash
git tag -a v1.3.0 -m "v1.3 public release: 八模块贯通网站7步 + Linux/Docker release(.53 smoke 绿)"
```
tag 本地不 push(台账只 push 分支)。更新台账相位表/里程碑表。
- [ ] **Step 6: 按逐阶段暂停规则**:`paused_for_review=true`,结束 loop,给用户 Phase 8 完整汇报(v1.3 = 全升级收官)。

---

## Self-Review(展开后自查)

**1. Spec 覆盖**(路线图 §8 Phase 8 项):
- 网站 7 步流程 → Task 8.6–8.9 ✓
- report tests 30 → Task 8.4+8.5 ✓(12→30)
- Linux/Docker smoke 10 → Task 8.10 ✓
- cell catalog module 元数据(§2 薄层)→ Task 8.1 ✓
- 后端加端点 → Task 8.2+8.3 ✓

**2. Placeholder 扫描**:后端/smoke task 给了完整测试+实现代码;前端 8.8/8.9 的组件正文标了"给完整组件代码"要求实现 subagent 补全(受篇幅限制未逐字全贴,但接口/props/数据源/验证清单确定)——**执行时实现 subagent 须写完整可 build 代码,不留 TODO**。

**3. Type 一致性**:`ModulePlanEntry` 字段严格对齐真实 `module_plan.py`(module/display_name/role/engine/route_disposition/species_support/species_verdict/verdict/mismatch/caution_flags/available_models);`module_plan()` 取值路径 = `report["provenance"]["module_plan"]`(runtime.py:103 硬确认);前端 `ModulePlan` 类型对齐 `to_dict()` 输出键。App.tsx 的 `onConfirmed`/`onRan`/`onAdvanced` 契约在 8.7 定义、8.9 落地一致。

**4. 张力处理**:完整 7 步 UI + 前端不 TDD → 前端 task 全用 build-verified 模板(build+lint+手验清单),质量压力落在后端端点 TDD;module 预览不碰核心(静态预期 vs run 后实际分离)。
