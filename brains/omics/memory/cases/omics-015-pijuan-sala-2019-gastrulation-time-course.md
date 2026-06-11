---
case_id: omics-015-pijuan-sala-2019-gastrulation-time-course
schema_version: 1
modality: scRNA_seq
study: "Pijuan-Sala et al 2019, A single-cell molecular map of mouse gastrulation and early organogenesis"
public_accession: "E-MTAB-6967 (ArrayExpress); also at https://marionilab.cruk.cam.ac.uk/MouseGastrulation2018/"
doi: 10.1038/s41586-019-0933-9
organism: Mus musculus
tissue: "whole embryo (E6.5–E8.5 mouse gastrulation)"
study_design: time_course
assay_subtype: 10x_chromium_v1
cell_type_focus: [epiblast, primitive_streak, mesoderm_lineage, endoderm_lineage, ectoderm_lineage, blood_progenitor]
tools: [Cellranger 1.3, scanran custom, scran, igraph, MNN, scater, MouseGastrulationData R pkg]
method_choice: [time_resolved_atlas, mnn_batch_correction, trajectory_cell_state, doublet_detection_per_stage, lineage_inference]
status: validated
validated: true
source: praxis_seed
case_class: success
provenance:
  source_type: literature
  doi: 10.1038/s41586-019-0933-9
  extracted_at: 2026-04-29
tags: [time_course, gastrulation, mouse_embryo, trajectory, lineage]
---

# Pijuan-Sala 2019：小鼠 gastrulation 时间序列 atlas（time_course 范例）

## Background
小鼠 E6.5-E8.5（gastrulation 到 early organogenesis）每 6 小时取一个时间点，~116k cells 共 9 个时间点。**time_course 数据的核心难点**：stage 不是离散 batch（连续发育），但实验上每个时间点是独立 sample；需要既建模 stage 作 covariate（不当 batch 洗掉）又允许 trajectory 跨 stage 平滑。这是 case-based learning 中 "time_course 应该怎么做" 的金标准。

## What I actually did
1. **Per-stage QC**：每个时间点独立跑 QC（cell count / mito% / nFeature）；早期 stage cell 较小、mito% 阈值 5%，晚期 stage cell 较大允许 8%
2. **Per-stage doublet**：每个时间点独立 doublet 检测；blastocyst 阶段双核细胞 prior 高
3. **Joint normalization**：scran size factor estimation，用 quickCluster 跨 stage 共享归一化（避免 stage-specific scale 漂移）
4. **HVG selection**：per-stage HVG → 取**并集**（不是交集，因为不同 stage 的 lineage marker 不一样）；最终 ~3000 HVG
5. **Batch correction**：MNN with `batch=stage`（**注意：stage 是 batch 但同时是 biology**——MNN 保留 stage 的渐变，不强制混合）
6. **不用 Harmony with batch=stage**：会过 mixing 把 stage 信号洗掉
7. **Trajectory inference**：在 PCA + UMAP 上保留 stage 顺序（不强制 force-directed layout）；用 diffusion map / Palantir 推 pseudotime
8. **Cell type annotation**：~37 cell types（epiblast, primitive streak, mesoderm subtypes, endoderm, ectoderm, blood progenitor 等），manual marker + cross-referenced with literature
9. **Lineage inference**：每个分化分支用 cellRank 或 Palantir branch probability

## ★ 排除/不做的事
- **Stage 当成 batch 用 ComBat / aggressive Harmony**：会洗掉发育时间梯度，trajectory 完全失败
- **跨 stage 用 cluster-based 离散 cell type**：发育是连续的；硬切失去过渡态信息
- **Per-stage 独立分析后简单 concat**：丢失跨 stage 的 lineage 关系
- **HVG 取交集而非并集**：丢失 stage-specific lineage marker（如 T-box gene 在原条期才高表达）
- **不做 doublet per stage**：早期 stage 自然双核 vs 晚期 stage 真 doublet 区分不清
- **DE 跨 stage 直接比**：必须以 stage 为 covariate（design = ~ stage * lineage）

## ★ 失败模式
- **Trajectory 反向**：UMAP 拓扑可能把 E8.5 放在 E6.5 旁边（高维 embedding artifact）；要看 PAGA / 力布局确认
- **小细胞类型在早期消失**：blood progenitor 在 E7.5 才出现，per-stage cluster 时早期没有该 cluster；不能假设 cell type 跨 stage 持续存在
- **Maternal contamination**：母体血液混入早期 embryo → 假"early hematopoietic" cell；通过 hemoglobin gene + maternal-specific marker (Y-chr in male embryos) 区分
- **Stage label misassignment**：解剖时间不准 ±2-3h 影响 ordering；推荐用 morphology + 表观基因表达共同确定
- **Lineage branch 推断不稳**：seed 敏感；多 seed 取 robust branch
- **Trajectory branch 强度差异大**：mesoderm 分化早强；endoderm 弱；不能用相同 cluster resolution 处理

## ★ 方法选择决策链
```
time_course scRNA?
├─ Stage 是连续生物变量（不是 nuisance batch）
│   → 不能 ComBat / aggressive Harmony with batch=stage
│   → 用 MNN 或 scVI with batch=technical_batch (NOT stage)
│   → 保留 stage 在 design 中作 covariate
├─ Trajectory inference 工具
│   ├─ Discrete branching → Palantir / cellRank
│   ├─ Continuous → diffusion map, RNA velocity (scVelo)
│   └─ 多分支 → PAGA + UMAP
├─ Per-stage QC 阈值（早期 stage 与晚期不同）
└─ HVG 跨 stage 取并集（不是交集）
```

## ★ QC sanity check (known answer)
- Anchor (Pijuan-Sala 2019 gastrulation)：
  - **T (Brachyury)** 在 E7.5 primitive streak 高表达 vs E6.5 几乎无 (>10x)
  - **Sox17** 在 endoderm lineage 单调上调 across E7.0 → E8.5
  - **Hbb-bh1, Hbb-y** (embryonic hemoglobin) 仅在 E7.5+ blood progenitor 中
  - UMAP / diffusion map 上 stage label 排成时间梯度（早期 E6.5 在一端，晚期 E8.5 在另一端）
  - Cell type ARI cross-stage > 0.6（同 lineage 的 cell type 跨 stage 应该一致）
- Pass criterion：T 在 E7.5 高 + Sox17 单调上 + UMAP stage 单调
- Fail criterion：UMAP 上 stage 散乱 → batch correction 过度（把 stage 当 batch 洗掉了）

## Lessons → seeds for rules
1. **Time_course 中 stage 是 biology 不是 batch**：不进 batch_key（rule 04 时间序列特例）
2. **HVG 跨 stage 取并集**（不同 stage lineage marker 不同）
3. **Per-stage QC 阈值** 因 cell size / metabolic state 随发育变化
4. **Trajectory 多 seed 验证** + topology 检查（PAGA / 力布局）
5. **Stage label 不可假设精确**：±2-3h 误差，关键判断用 morphology + lineage marker 交叉
6. **Maternal contamination** 在 early embryo 是 known confound；分析前先剔
