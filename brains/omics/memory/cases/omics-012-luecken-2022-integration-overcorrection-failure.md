---
case_id: omics-012-luecken-2022-integration-overcorrection-failure
schema_version: 1
modality: scRNA_seq
study: "Luecken et al 2022, Benchmarking atlas-level data integration in single-cell genomics"
public_accession: "(scIB benchmark suite — 13 atlas tasks across human + mouse)"
doi: 10.1038/s41592-021-01336-8
organism: Homo sapiens
tissue: "multi-tissue atlas (immune, lung, pancreas, brain, etc.)"
study_design: meta_analysis_failure
assay_subtype: cross_method_benchmark
cell_type_focus: [cross_tissue_atlas]
tools: [scIB, Harmony, scVI, scANVI, BBKNN, Seurat_v3_CCA, fastMNN, ComBat, Conos, scGen, DESC, ScanoramaCT, MNN]
method_choice: [scIB_benchmark, Harmony, scVI, scANVI, BBKNN]
status: validated
validated: true
source: praxis_seed
case_class: failure_landscape
provenance:
  source_type: literature_failure_review
  doi: 10.1038/s41592-021-01336-8
  extracted_at: 2026-04-29
tags: [failure_case, integration, over_correction, batch_vs_biology, anti_pattern]
---

# Luecken 2022：scRNA atlas integration 中过校正与欠校正的系统失败地图

## Background
Luecken 等用 scIB benchmark 把 16 种 integration 方法同时跑在 13 个 atlas 任务上（含 immune 综合、lung、pancreas、brain 等），既量化 batch mixing（kBET / iLISI），也量化 biological conservation（cluster ARI / cell type ASW / trajectory conservation / silhouette of cell types）。**核心发现**：没有方法在所有任务上都赢；许多"主流"方法在某些场景**严重过校正**（destroy biology）或**严重欠校正**（batch dominates）。

## What this paper actually did (and what it found)
1. 13 atlas tasks 涵盖 simple (1-2 batch / few cell types) → complex (10+ batch / 30+ cell types / cross-platform)
2. 14 个 metric 分两组：
   - **Batch removal**：kBET、iLISI、graph integration LISI
   - **Bio conservation**：NMI / ARI / cell type ASW / trajectory / cell-cycle / HVG conservation
3. 计算综合得分 + 单维度分析，公开 leaderboard
4. **关键 fail patterns 量化**：
   - **MNN-based 方法（fastMNN, Scanorama）** 在 cross-platform 任务上 over-correct → small cell types ASW 大幅下降
   - **ComBat** 在 cell type 比例不平衡 batch 间显著 over-correct
   - **Seurat CCA** 在 trajectory tasks 上压扁 trajectory 结构
   - **BBKNN** 速度快但 cluster boundary 软
   - **scVI/scANVI** 综合表现最好但需要 GPU + 训练时间
   - **Harmony** 是单 modality 最稳的折中（速度 + 质量）

## ★ 排除/不做的事 (反面教材)
- **跑单个 integration 方法当 final**：rule 05 强源 —— 该论文证明 single-method 不可靠
- **看 batch removal 一项指标**：高 mixing 但 biology 被洗 = bad，single metric 误导
- **trajectory 数据用 ComBat / fastMNN aggressive integration**：trajectory 被压扁
- **小 cell type 比例 < 1% 时信任 atlas integration**：小群体几乎不可避免被洗
- **不报 metric trade-off**：只报 mixing 不报 biology preservation = 不可解读

## ★ 失败模式 (论文记录的)
- **小细胞类型消失**：ComBat 在 immune atlas 上把 pDC（占比 0.5%）几乎抹平
- **Trajectory 压扁**：Seurat CCA 在 pancreas development 上把连续分化变成离散 cluster
- **过 mixing 把生物学当 batch**：ComBat / aggressive Harmony 当 cell type 比例不平衡时把 cell type 当 batch 处理
- **Cross-platform 失败案例多发**：Smart-seq2 + 10x 整合时 dropout 模式不同 → 多数方法在 cell type 数 > 15 任务上失败

## ★ 方法选择决策链 (Luecken 2022 给出的)
按场景：
```
任务规模？
├─ 简单 (1-3 batch, < 10 cell types) → Harmony or BBKNN 都行
├─ 中等 (4-10 batch, < 20 cell types) → Harmony / scVI 都好；prefer scVI 如果 GPU 可用
├─ 复杂 (cross-platform / cross-tissue / 大 batch) → scVI/scANVI 是当前最佳
└─ Trajectory/development → 优先 trajectory-preserving 方法 (scVI / Conos), 避免 ComBat / aggressive MNN
```

**强制**：≥ 2 方法 + 量化两个方向（mixing + biology）。

## ★ QC sanity check (known answer)
- Anchor (Kang IFN-β / 类似 condition-paired)：
  - **Bio preservation**：ISG15 stim/ctrl LFC ≥ 2.5 在 CD14 mono；cell type ARI cross batch ≥ 0.7
  - **Batch mixing**：kBET 接受率 ≥ 0.5 across donors
- Pass criterion: 两个方向都过 → integration 合格
- Fail criterion: 任一方向显著低于阈值 → 选另一方法或调超参

## Lessons → seeds for rules
1. **Integration 必须 ≥ 2 方法 cross-check**（rule 05 强化源） —— 不同任务最佳方法不同
2. **必须量化 mixing AND biology preservation 两个维度** —— 单看一个误导
3. **scVI/scANVI 是当前 SOTA**，但 Harmony 是"无 GPU 时的保底" —— 这两个组合是 robust 默认
4. **ComBat / fastMNN 在 atlas-scale 任务上需要谨慎使用** —— 在 cell type 比例极不平衡或 cross-platform 时容易 over-correct
5. **Atlas integration 的小 cell type 不可信**：占比 < 1% 的 cell type 在 integration 后报告 confidence: low
6. **scIB benchmark 是社区标准**：任何新 atlas 论文该用它评估
