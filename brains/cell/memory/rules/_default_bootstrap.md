---
rule_id: _default_bootstrap
schema_version: 1
scope: bootstrap
applies_to:
  cell_task: ALL
  image_modality: ALL
  sample_dimension: ALL
evidence_cases: [cell-001, cell-002, cell-003, cell-004, cell-005, cell-006, cell-007, cell-008, cell-009, cell-010]
confidence: medium
rule_type: cross_task_priors
provenance:
  source_type: synthesis
  source_path: synthesis/cell-synthesis.md
  extracted_at: 2026-04-29
---

# PRAXIS-Cell — 冷启动通用先验（8 unifying principles）

来自 10 个案例的横向提炼（synthesis/cell-synthesis.md「七、统一原则」）。任何 cell_task 在没有任务专属 rule 命中时，必须遵守以下 8 条。

## 1. DL segmentation 优先于 traditional

**证据**：cell-001（Cellpose vs watershed）、cell-008（Cellpose 3D / Stardist 3D）。

**Why**：现代 DL 模型（Cellpose / Stardist / Mesmer）在 generalist 设定下显著优于 watershed / threshold；watershed 仅适合 simple separated objects。

**How to apply**：
- 优先选 Cellpose（cyto2 / nuclei）/ Stardist / Mesmer (TissueNet for tissue) / DeepCell。
- Watershed 仅在数据量极小（< 50 image）+ object well-separated 时可作 baseline 对比。
- 必须 explicitly set `diameter` / `flow_threshold` / `cellprob_threshold` — 不准用默认值。

## 2. Per-cell aggregation, not per-pixel / per-image

**证据**：cell-001、cell-002、cell-007、cell-010。

**Why**：HCS 与 morphological profiling 的 readout 必须 per-cell（mean / median / distribution）；per-pixel 噪声极大；per-image 失去 cell-level heterogeneity。

**How to apply**：
- segmentation → per-cell mask → per-cell features (intensity / shape / texture)。
- HCS profile：per-cell → per-well median + MAD（不单点 per-image）。

## 3. Plate / batch normalization 必备

**证据**：cell-002（HCS edge effect / B-score）、cell-007（plate batch effect）、cell-010（cluster collapse）。

**Why**：96/384/1536-well plate 边缘 evaporation、seed density bias、staining batch 都会让 raw signal 不可比；不归一直接 z-score 假阳率高。

**How to apply**：
- HCS：B-score（median polish row+col effect）+ z-score combine。
- Cell Painting：per-plate DMSO median + MAD。
- 跨 plate combine 后 quantile normalize。

## 4. Multi-method consensus（避免单点失败）

**证据**：cell-005（Pearson + Manders + Costes）、cell-002（z-score + B-score + SSMD）、cell-007（CellProfiler + DeepProfiler）。

**Why**：单一指标极易被 outlier / threshold / dynamic range 影响；多方法交叉验证才稳。

**How to apply**：
- Colocalization：必须 Pearson + Manders M1/M2 + Costes randomization 三方合报。
- Hit calling：z-score + B-score + SSMD 至少两种交叉。
- Profile：CellProfiler 手工特征 + DeepProfiler embedding 双 backend。

## 5. Known biology / reference compound validation

**证据**：cell-003（germinal center should enrich CD20+B + Ki67）、cell-006（known EC50 within 5×）、cell-010（taxol clusters with microtubule reference）。

**Why**：纯算法跑通 ≠ 答案对；必须有 known-positive 在结果中浮现。

**How to apply**：
- Spatial proteomics：组织已知结构（GC / T-cell zone / tumor stroma）必须出现在 cluster annotation。
- Dose-response：必须 spike 一个已知 EC50 化合物（taxol / staurosporine）作 anchor。
- Phenotype landscape：reference MoA compound 库（kinase inhibitor / microtubule / DNA damage）作 cluster anchor。

## 6. 3D-aware tool for 3D data

**证据**：cell-008（Cellpose 3D vs Cellpose 2D-per-plane）。

**Why**：3D z-stack 用 2D-per-plane segmentation 损 z 轴 continuity；anisotropic voxel（xy 0.5 vs z 2 μm）让 metric 偏。

**How to apply**：
- z-stack 数据：Cellpose 3D / Stardist 3D / plant-seg。
- voxel 必须 explicit annotated；anisotropy 输入到 model。
- 每 cell 输出 3D volume / surface / sphericity（不 2D area）。

## 7. Anti-contamination QC 必跑

**证据**：cell-002（cytotoxic compound mask）、cell-003（autofluorescence）、cell-009（hot pixel）、cell-001（border cell）。

**Why**：image artifact（autofluorescence / hot pixel / cytotoxic fake-phenotype / edge well）不去会污染下游所有分析。

**How to apply**：
- IMC：**hot pixel removal 必须**（Steinbock pipeline）— PROMPT 强制 reviewer block。
- Fluorescence：rolling-ball background subtract + autofluorescence channel control。
- Segmentation：filter border-touching cells + area outliers + low-confidence segments。
- HCS：cytotoxic filter（cell count drop > 50% → exclude）、autofluorescence parallel control。

## 8. 跨 agent envelope hooks（PRAXIS suite 协同）

**证据**：PROMPT Phase 8 + cell-synthesis.md「七.8」。

**Why**：PRAXIS-Cell 不是孤岛 — 与 Drug、Omics、CRISPR 互通。

**How to apply**：
- ← **Drug**：HCS phenotypic screen + MoA cluster（envelope `from_drug`：compound_set + assay_request + expected_phenotype）。
- ← **Omics**：spatial transcriptomics ↔ spatial proteomics 互配（envelope `from_omics`：transcriptomics_run_id + registration_target）。
- ← **CRISPR**：CRISPR screen phenotype readout（envelope `from_crispr`：guide_library + readout_request + screening_format）。
- 每条 envelope 触发 `agents/orchestrator.py --resume-from reporting --task-id`。

---

## Confidence label 必须给出

每条 recommendation 的最后必带 `confidence: {cold_start | low | medium | high | domain_knowledge}`，且解释 confidence 来源（命中几条 case / 几条 rule、是否有 known-bio anchor、是否离线 fallback）。
