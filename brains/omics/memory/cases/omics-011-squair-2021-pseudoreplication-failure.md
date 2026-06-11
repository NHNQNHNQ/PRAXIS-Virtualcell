---
case_id: omics-011-squair-2021-pseudoreplication-failure
schema_version: 1
modality: scRNA_seq
study: "Squair et al 2021, Confronting false discoveries in single-cell differential expression"
public_accession: "(meta-analysis: 18 datasets including GSE96583 + 17 others)"
doi: 10.1038/s41467-021-25960-2
organism: Homo sapiens
tissue: "multi-tissue (immune, neural, hepatic, etc.) — meta-analysis"
study_design: meta_analysis_failure
assay_subtype: cross_assay_meta
cell_type_focus: [cross_tissue_failure_review]
tools: [edgeR 3.34, DESeq2 1.32, MAST 1.18, Wilcoxon, scIB benchmarks]
method_choice: [cell_level_DE, pseudobulk_DE, mast_random_effect, scIB]
status: validated
validated: true
source: praxis_seed
case_class: failure_landscape
provenance:
  source_type: literature_failure_review
  doi: 10.1038/s41467-021-25960-2
  extracted_at: 2026-04-29
tags: [failure_case, pseudoreplication, scRNA_DE, anti_pattern]
---

# Squair 2021：scRNA DE 中 pseudoreplication 的系统性失败

## Background
Squair 等系统比较了 14 种 scRNA DE 方法在 18 个 ground-truth 数据集（含 Kang IFN-β = case 002）上的表现。**结论震撼整个 scRNA 社区**：以 cell 为单位的 DE（cell-level Wilcoxon / t-test / 不带 random effect 的 MAST）在大量数据集上产生 false discovery rate 远高于 nominal level —— 通常多 10-100×。这是 case-based learning 中最有价值的反面典型。

## What this paper actually did (and why it matters)
1. 拿了 18 个数据集，每个都有 ground truth（"匹配 vs 真随机化"对照）
2. 对每个数据集分别跑：Wilcoxon on cells、t-test on cells、MAST without random effect、MAST with random effect、pseudobulk + DESeq2/edgeR/limma-voom
3. **量化 false positive rate**：在 negative control（随机化标签）下，哪些方法仍然报告显著 DE 基因？
4. **结果**：
   - Wilcoxon on cells：FDR 真值 30-50%（远超 nominal 5%）
   - MAST without random effect：FDR 20-40%
   - MAST with random effect：FDR 接近 nominal
   - **Pseudobulk + DESeq2/edgeR**：FDR 接近 nominal，且 effect size 估计稳健
5. 在 Kang IFN-β 数据上重做：cell-level Wilcoxon 报告 ISG15 等真 DE 但同时报告几千个 false positive 基因；pseudobulk DESeq2 收敛到 ~200-300 真 DE 基因

## ★ 排除/不做的事 (反面教材)
- **不做 cell-level Wilcoxon 出 final DE**：8 donor × 1k cells ≠ 8000 独立样本
- **MAST 不带 random effect**：MAST 有 random effect option，没设等于退化为 cell-level
- **以 nominal p value 信任结果**：没经验证的方法 nominal p 完全不可信
- **依赖 logfc threshold 解决问题**：不解决；FDR 还是炸

## ★ 失败模式 (本论文记录的)
- **整个 scRNA 社区 2017-2021 的论文 reanalysis**：Squair 重跑了发表论文的 DE，发现报道的 DE list 平均 30-60% 是 false positive
- **下游 GSEA/pathway 富集**：因 DE list 错，pathway 富集也错，造成被引用的"机制结论"虚高
- **Reviewer 经验**：审稿人开始要求 pseudobulk 默认（rule 06 的 community origin）
- **Squair 推荐的修正路径**：
  - 默认 pseudobulk + DESeq2/edgeR（minimum donor n ≥ 3 per group）
  - 当 cell-level effects 是研究目标时用 MAST + (1|donor) random effect
  - 当 donor 数 < 3 时显式标 confidence: low

## ★ 方法选择决策链
**这就是 rule 06 的来源**。Squair 给出的决策树：
```
是否有 ≥ 3 donor per group?
├─ YES → pseudobulk per (donor, condition, cell_type) → DESeq2/edgeR → apeglm shrinkage
└─ NO → MAST + random effect (1|donor) → label confidence: low
```

不允许的决策：
- 默认 cell-level Wilcoxon（即使工具 GUI 默认这样）
- 单 donor 的"DE"——这是 cell-state 比较，不是统计学意义上的 DE
- 跨 donor / 跨 batch 跑 cell-level——pseudoreplication 在 batch 上叠加，FDR 更糟

## ★ QC sanity check (known answer)
- Anchor: 在 Kang IFN-β 数据 (case 002) 上重跑：
  - cell-level Wilcoxon → 数千 DE 基因（含大量 false positive）
  - pseudobulk DESeq2 → ~200-300 DE 基因，ISG15 stim/ctrl LFC ≥ 2.5 robust
- Pass criterion (any new scRNA DE pipeline)：在 negative control（randomly shuffled labels）下，FDR < 10%
- Fail criterion：负对照报告 > 1000 false DE 基因

## Lessons → seeds for rules
1. **Pseudobulk DEFAULT for scRNA DE**（rule 06 主源） — 即使工具 GUI 默认 Wilcoxon 也要改
2. **Negative control 跑一次**：随机化 condition 标签后跑 DE，应该几乎没 DE 基因
3. **任何 scRNA DE 论文都该 cite Squair 2021** —— 这是社区共识的 pivot point
4. **cell-level effect 是另一个问题**：当问"细胞状态如何沿 trajectory 变"时 cell 是合理 unit；但"condition vs ctrl 比较"几乎都是 donor-level
5. **FDR 量化失败**：必须报告（即使是 1-2 个 negative control runs）才能让读者判断
