# Cell catalog 预设 + 结构化下拉增强 — 设计文档

> 日期 2026-07-03 · 归属 v0.6 产品化(计划 §2 的**薄化落地**) · 状态:已 brainstorm + 用户拍板,待写实现计划。

## 1. 决策(用户已拍板)

计划 §2 的重型 CellContext(带 fallback_policy/default_governance 的一等治理对象 + 首页翻新)**收敛**为三条:
1. **首页 IA**:混合——**保留聊天优先入口**,给 Confirm(及 Ask)加 `/api/options` 驱动的结构化下拉 + cell 预设选择器。不翻首页信息架构。
2. **权威源**:**薄 catalog**——catalog 只加 cell/model 预设 + 展示标签;**词汇/适用性/治理权威全留后端现有代码**(`species_schema` + `run_virtualcell_query` 白名单 + `model_applicability` + `reliability`)。**无双真相源、无新治理权威**。
3. **分层**:后端 `praxis_virtualcell/catalogs/cell_catalog.yaml` 存预设,经**扩展的 `/api/options`** 只读暴露,前端下拉消费。

## 2. 铁律

- catalog 是**只读展示层**:不参与预测/治理/路由决策,不引入新词汇权威。species/perturbation/task 合法值仍由 `SUPPORTED_SPECIES/PERTURBATION/TASKS`(单一真相源)决定;cell_type 仍是自由字符串(预设只是便捷选项)。
- 前端只展示:下拉/预设仅填充用户输入,最终仍走 `/api/parse`→confirm→`/api/jobs`,后端确定性 runtime 定终局。
- 不碰 governance/predictors/reliability/route_table/species_schema 逻辑。

## 3. 现状对齐(已读)

- `/api/options` 已返回 `{species, perturbation_type, task_type, cell_type_examples, cell_type_free_text}`(源自白名单,单一真相源)。
- 前端 `ConfirmView` 已有结构化字段(species/cell_type/perturbation_type/targets)但是**自由文本 input**;`AskView` 聊天优先、未用 options。
- `model_applicability` 已按 predictor 管 supported_species/cell_types/ortholog/negative_transfer(治理层,不动)。

**Gap(本切片补)**:①无 curated cell/model 预设;②前端未用 `/api/options` 的枚举做下拉(species/perturbation_type/task 仍自由文本,易输错)。

## 4. 后端:cell catalog + options 扩展

**新增** `praxis_virtualcell/catalogs/cell_catalog.yaml`(≥10 预设,覆盖 4 物种):
```yaml
# 只读 UI 辅助:curated cell/model 预设(展示层)。非权威词汇/治理。
presets:
  - id: human_k562
    species: human
    cell_type: K562
    label: "K562 — human CML (Norman perturb-seq)"
    example_perturbation_type: gene
    example_targets: [AHR, GATA1]
  - id: ecoli_iml1515
    species: bacteria
    cell_type: E. coli
    label: "E. coli — iML1515 GEM"
    example_perturbation_type: gene
    example_targets: [b0720]
  # … ≥10 条,human/mouse/yeast/bacteria 均有
```
每条:`id, species(∈白名单), cell_type(自由), label, example_perturbation_type, example_targets`。**yaml 只声明展示信息**,species 必须 ∈ SUPPORTED_SPECIES(loader 校验,越界即测试失败——防预设与白名单漂移)。

**新增** `praxis_virtualcell/catalogs/__init__.py`:`load_cell_presets() -> list[dict]`(读 yaml、跳过 `._*`、返回 presets 列表;校验每条 species ∈ SUPPORTED_SPECIES)。

**改** `praxis_vc_api/services/runtime_service.py::options()`:结果加 `"cell_presets": load_cell_presets()`。其余键不变。`/api/options` 端点无需改(已透传 svc.options())。

## 5. 前端:结构化下拉增强(ConfirmView)

**改** `praxis_vc_react/src/api.ts`:`Options` 类型加 `cell_presets`;新增 `getOptions()`(GET /api/options)。

**改** `praxis_vc_react/src/views/ConfirmView.tsx`:
- mount 时 `getOptions()` 拉枚举(失败则静默降级为纯文本,保持可用)。
- `species` / `perturbation_type` 由自由 input 改 `<select>`(选项来自 options;附"其它"允许保留原值,避免锁死)。
- 新增 **cell 预设 `<select>`**:选中即填充 species + cell_type + perturbation_type + targets(便捷,不锁死;选后仍可手改)。
- `cell_type` 保持自由文本 input(预设只是便捷);`targets` 保持逗号分隔文本。
- 顶部保留"LLM 未参与预测/治理决策"横幅(App 已有)。
- 聊天入口(AskView)不动。

## 6. 测试

后端(pytest):新增 `praxis_virtualcell/tests/test_cell_catalog.py`:
- `load_cell_presets()` 返 ≥10 条;每条含 id/species/cell_type/label;每条 species ∈ SUPPORTED_SPECIES(防漂移);4 物种均覆盖;id 唯一。
- 扩 `test_api.py::test_options`:断言 `cell_presets` 存在、非空、元素含 species/cell_type/label 且 species ∈ 返回的 species 白名单。

前端:`npm run build` 通过(tsc+vite)。手动/preview 验证下拉与预设填充(可选)。

## 7. 验收
- `/api/options` 返回 `cell_presets`(≥10,4 物种,species 不越白名单)。
- ConfirmView 有 species/perturbation_type 下拉 + cell 预设选择器,选预设自动填充,仍可手改。
- 全量 `praxis_virtualcell/tests` 无回归(0 failed);`npm run build` 通过。
- 无新词汇/治理权威;catalog 纯只读展示。

## 8. 不做(YAGNI)
- CellContext 一等对象 / fallback_policy / default_governance(治理留 runtime)。
- 首页 IA 翻新(结构化选择优先)——本次只做下拉增强。
- assay_context / available_predictors 声明(适用性由 model_applicability 运行时定)。
