---
case_id: omics-029-buettner-2015-cell-cycle-confound-failure
schema_version: 1
modality: scRNA_seq
study: "Buettner et al 2015, Computational analysis of cell-to-cell heterogeneity in single-cell RNA-sequencing data reveals hidden subpopulations of cells"
public_accession: "E-MTAB-2805 (mouse ESC); E-MTAB-3346"
doi: 10.1038/nbt.3102
organism: "Mus musculus (mouse ESC + naive T cell pilot)"
tissue: "embryonic stem cell + T cell pilot"
study_design: method_failure_demonstration
assay_subtype: smartseq_scrna_pilot
cell_type_focus: [embryonic_stem_cell_pluripotent, cell_cycle_phase]
tools: [scLVM 0.4, R, Smart-seq, sklearn PCA, GO_BP, Cyclone classifier]
method_choice: [cell_cycle_regression, latent_variable_model, cycle_gene_classifier, pre_clustering_correction]
status: validated
validated: true
source: praxis_seed
case_class: failure_pattern
provenance:
  source_type: literature_failure_demonstration
  doi: 10.1038/nbt.3102
  extracted_at: 2026-05-01
tags: [failure_case, cell_cycle_confound, scrna_artifact, scLVM, foundational, NEG]
---

# Buettner 2015 scLVM：cell cycle 作为 scRNA latent confound 的开山反例

## Background
Buettner et al 2015 是 scRNA 领域第一篇系统证明 **cell cycle 是 scRNA PCA / clustering 的 dominant latent variable** 的论文。**实验设计**：mouse ESC（同一 cell line, 同一 batch）；理论上不该有 subpopulation。**未做 cycle 校正前**：PC1 / PC2 完全是 G1 / S / G2-M 三个 cluster，被早期论文误标为"hidden subpopulation"。**关键贡献**：scLVM 工具 + 流程，明确 cell cycle 是 nuisance latent，需要 regress out 才能看到真正生物学异质性。这是 case-based learning 中"看似 cell type 实为 cell cycle"的教科书反例。

## What this paper actually did
1. **同源 mouse ESC**: 单 cell line, 同 batch — 理论上无 subpopulation
2. **未校正 PCA**: 三个明显 cluster 在 PC1/PC2 上 — Cyclone classifier 验证它们是 G1, S, G2-M
3. **scLVM** 用 Bayesian factor model 推 cell-cycle latent + 其他 latent (nuisance + biological)
4. **校正后**: 发现 ESC 内部仍有 ~3 个亚群，但是基于 differentiation potential / Nanog 表达 dynamics（真生物学）
5. **应用到 naive T cell**: 同样路径揭示 Th1 / Th2 / Th17 fate-bias 异质性，cycle 校正前完全被 cycle phase 掩盖
6. **公开 scLVM R 包** + cell-cycle gene set (Cyclone GO_BP curated)

## ★ 排除/不做的事 (反面教材)
- **PC1/PC2 cluster 直接 call cell type**: 多数情况下 PC1 在异质 dividing cell 是 cell cycle，不是 cell type
- **不做 cell cycle scoring**: scanpy `score_genes_cell_cycle` / Cyclone / Seurat `CellCycleScoring` 是必备 first-pass diagnostic
- **regress out 整套 cycle gene 不区分 phase-specific vs general**: 会过度移除 biology
- **Differentiating cell 用 cycle regression**: 分化中的 cycle 退出本身是 biology — regress out 会消去关键信号
- **拿 scLVM 旧 (R-only) 工作流 当现代标准**: 现代用 scanpy / Seurat 的 score-and-regress 一致路径
- **不查 cycle phase 比例 imbalance**: 如果 cluster A 70% G1, cluster B 70% G2-M，差异主要是 phase
- **batch + cycle 共变不分开建模**: 不同 capture batch 偏好不同 cycle phase → confound
- **快速分裂的 cell type (cancer / progenitor) 假设 cycle is biology**: 部分对，但仍要分离 phase-specific gene 与持续 active gene

## ★ 失败模式 (论文记录的)
- **Mouse ESC pilot**: 未校正时 PC1 = cycle，被早期论文 (Trapnell 2014 等部分) 当 differentiation 信号
- **Naive T cell**: cycle 掩盖 Th 偏向 — 校正后 Tbx21 / Gata3 / Rorc 高变 cell 显形
- **Cancer scRNA misanalysis**: 早期 melanoma scRNA (Tirosh 2016) 显示 malignant cell 的 cycle dominate；不校正 → "肿瘤异质性"被混入 cycle 信号
- **Differentiating embryo**: gastrulation / hematopoiesis 中 cycle exit 是 differentiation 一部分，naive regress out 会 erase fate-marker dynamics
- **Cycle gene list mismatch**: human / mouse cycle gene set 不能互换；用错 list → regression 不充分
- **Method ignorance compounds**: 论文 reanalysis 时常发现 7-8 年前的"亚群"在现代 cycle-aware 流程下消失
- **Cycle-aware integration**: 跨 batch 整合时若不联合 model cycle + batch，cycle phase imbalance 在 batch 间会被错认为 batch effect

## ★ 方法选择决策链 (Buettner 给出的)
```
scRNA 分析 first-pass cell cycle check?
├─ Step 1: cycle scoring (mandatory)
│   ├─ scanpy `score_genes_cell_cycle` / Seurat `CellCycleScoring`
│   ├─ Cyclone classifier for mouse / human
│   └─ Report % cells per phase
├─ Step 2: PCA without correction
│   ├─ Color by cycle phase
│   ├─ PC1/PC2 dominated by cycle? → flag for correction
│   └─ Cluster phase imbalance? → batch × cycle confound
├─ Step 3: regression decision
│   ├─ Static cell type heterogeneity → regress cycle out (sc.pp.regress_out)
│   ├─ Differentiating system → DO NOT naive regress; use scLVM-style joint model
│   └─ Cancer / fast-dividing → phase-specific gene only
├─ Step 4: post-correction validation
│   ├─ Cycle no longer dominant in PC1
│   ├─ Cluster phase ratio approximately balanced
│   └─ Known biology marker now visible
```

## ★ QC sanity check (known answer)
- Anchor (Buettner 2015 mouse ESC)：
  - **未校正 PC1/PC2 = G1/S/G2-M cluster**: > 40% variance attributable to cycle
  - **Cyclone classifier**: ESC 中 G1 ~30%, S ~30%, G2-M ~40%
  - **校正后 cluster**: cycle phase ratio per cluster 接近全局 (无 imbalance)
  - **真 biology**: Nanog 高变 cell 显形（pluripotency state heterogeneity）
- Pass criterion: 校正前后 cycle dominance shift 显著 + cluster phase 平衡 + 真 biology marker 显形
- Fail criterion: 校正后 cycle 仍 PC1 dominant → cycle gene list 不全 / regression 不充分

## Lessons → seeds for rules
1. **Cell cycle scoring 是 scRNA first-pass 必查**（rule 02 候选）— 不查就 cluster 多半是 cycle artifact
2. **PC1 dominated by cycle** 是 dividing population 的常见表现，不是 cell type
3. **Differentiating system 不能 naive regress cycle**：cycle exit 是 biology
4. **Cycle gene list 物种特异**：human / mouse 不互换
5. **跨 batch 整合时联合 model cycle + batch**：phase imbalance 假冒 batch effect
6. **快速分裂 cancer / progenitor 谨慎**：phase-specific gene only regress
7. **Reanalysis 旧 paper 的"hidden subpopulation"**：现代 cycle-aware 流程下经常消失 — 警惕历史结论
