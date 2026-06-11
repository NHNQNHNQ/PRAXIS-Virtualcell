---
case_id: omics-014-replogle-2022-perturb-seq
schema_version: 1
modality: perturb_seq
study: "Replogle et al 2022, Mapping information-rich genotype-phenotype landscapes with genome-scale Perturb-seq"
public_accession: "GSE264667; processed at https://gwps.wi.mit.edu/"
doi: 10.1016/j.cell.2022.05.013
organism: Homo sapiens
tissue: K562 (CML cell line) and RPE1 (epithelial)
study_design: crispr_screen
assay_subtype: perturb_seq_crispri_genome_scale
cell_type_focus: [K562_leukemia, RPE1_epithelial, perturbation_phenotype]
tools: [Cellranger 6.0, scanpy 1.9, MAGeCK, MIMOSCA, scVI, Mixscape, custom_energy_clustering]
method_choice: [crispri_perturb_seq, sgRNA_assignment, mixscape, energy_distance_clustering, transcriptional_phenotype_map]
status: validated
validated: true
source: praxis_seed
case_class: success
provenance:
  source_type: literature
  doi: 10.1016/j.cell.2022.05.013
  extracted_at: 2026-04-29
tags: [perturb_seq, crispri, genome_scale, K562, transcriptional_phenotype]
---

# Replogle 2022：Perturb-seq 全基因组扰动 + 表型图谱

## Background
Perturb-seq = CRISPRi/CRISPRa + scRNA-seq，每个细胞带 sgRNA 标签，可同时测千个基因 perturbation 的 transcriptomic 表型。Replogle 等做到目前最大规模（genome-scale）：在 K562（白血病）和 RPE1（上皮）两株细胞上 perturb 9866 个 essential gene + 11258 个 expressed gene。**~2.5 million cells**。这是 case-based learning 的"未来 default scRNA workflow"——每个分析 agent 都该知道 Perturb-seq 与传统 scRNA 的差异。

## What I actually did
1. **Data structure**：每个细胞带一个 sgRNA 条码（10x 5' library + extra capture sequence）→ Cellranger 同时输出 RNA matrix + sgRNA assignment table
2. **sgRNA assignment**：直接用 sgRNA UMI count > threshold 不可靠（多重感染，bleedthrough）；用 **Mixscape** 或 Replogle 的混合模型 — 区分 "perturbed" vs "non-targeting control + escapers"
3. **Multi-perturbation cells**：MOI ~1 设计但实际 ~30% 双感染，分析时只保留单 sgRNA cells（~1.5M out of 2.5M）
4. **QC** 同标准 scRNA + sgRNA-specific：`pct_mt < 15`, `n_genes > 500`，sgRNA UMI assignment confidence
5. **Phenotype computation**：每个 perturbation 的 mean transcriptomic profile vs non-targeting control → energy distance / Wasserstein 距离作 perturbation 强度
6. **Clustering perturbations** (not cells)：用 perturbation × gene effect matrix 跑 hierarchical / UMAP → 把功能相关基因 cluster 起来（如 ribosome biogenesis、proteasome、mitochondrial OXPHOS）
7. **Validation**：跨 K562 和 RPE1，shared cluster (universal pathway) vs cell-type-specific cluster（lineage program）
8. Resource: GPU for scVI; memory ~500GB for full matrix

## ★ 排除/不做的事
- **Bulk DE 类比 scRNA DE**：Perturb-seq 的核心 unit 是 perturbation（sgRNA），不是 cell；不能直接做 cell-level Wilcoxon
- **不区分 "perturbed" vs "escaper"**：CRISPRi efficiency ~70-90%，用 raw sgRNA assignment 把 escaper 当 perturbed → effect size 被稀释
- **Multi-sgRNA cells 一起分析**：双感染 cell 的表型不可解读
- **n_cells_per_perturbation < 30 跑 phenotype**：power 不足，noise 主导
- **跨 cell line 直接比较 perturbation 强度**：lineage 表达背景不同，应做 cell-line-internal normalization

## ★ 失败模式
- **sgRNA bleedthrough**：barcode 跨 droplet 污染，导致 single-cell 错绑 sgRNA → false phenotype
- **Genome-scale screen 中 essential gene 死掉**：CRISPRi knockdown → 细胞死亡 → 该 sgRNA 几乎检测不到 → false negative；需要做 lethality 分析（sgRNA depletion over time）
- **Mixscape escaper detection 假阴**：高效 sgRNA 在 transcriptome 上几乎无 effect 看似 escaper 实际是 lethal —— 需结合 sgRNA enrichment time-series
- **Perturbation cluster 不稳**：seed 敏感；需要多 seed 取共识 cluster
- **Doublet detection 复杂**：scrublet on RNA + sgRNA assignment 双重过滤；普通 scrublet 误把 high-MOI 当 doublet

## ★ 方法选择决策链
```
是 Perturb-seq 数据？
├─ YES → sgRNA assignment 走 Mixscape (escaper detection + perturbation efficacy)
│        → phenotype = perturbation × gene effect matrix
│        → cluster perturbations (not cells)
│        → energy distance > 0.1 视为 perturbed
│        → DE 用 pseudobulk per perturbation × cell-line + DESeq2
└─ NO (传统 scRNA) → rule 06 走 pseudobulk + DESeq2 路线
```

**关键决策**：sgRNA UMI threshold（推荐 ≥ 5 + Mixscape 二次过滤），cell number per perturbation（≥ 30），cell-line baseline（per-cell-line non-targeting control, 不跨细胞系）。

## ★ QC sanity check (known answer)
- Anchor (Replogle K562 genome-scale)：
  - 已知 ribosome biogenesis 基因 (RPS3, RPL3, NOP56 等) perturbation **cluster 在一起**（hierarchical clustering 的 leaf）
  - 已知 proteasome 基因 (PSMA1-7, PSMB1-7) 同 cluster
  - Non-targeting control sgRNA effect ≈ 0（应该几乎无 transcriptomic 改变）
  - Perturbation 数 × cell-line cluster 重合度 (cosine) > 0.6 across K562/RPE1（universal pathways）
- Pass criterion：ribosome / proteasome cluster 各自完整 + non-targeting effect < 0.05
- Fail criterion：non-targeting 也显著 perturbed → sgRNA 污染或 batch artifact；ribosome cluster 散落 → escaper detection 失败

## Lessons → seeds for rules
1. **Perturb-seq 的 unit 是 perturbation 不是 cell**：分析转向 perturbation × phenotype matrix
2. **sgRNA assignment 必须用 Mixscape 类工具**（不能 raw threshold）；区分 perturbed / escaper / unassigned
3. **Multi-sgRNA cell 必须过滤**：MOI 设计为 1 但实际 ~30% 双感染
4. **Per-cell-line baseline**：不跨细胞系直接比；用 per-cell-line non-targeting control
5. **Perturbation cluster validation**：已知 pathway gene 该 cluster 一起；non-targeting effect 该 ≈ 0；这两条是 sanity 必查
6. **Energy distance / Wasserstein 比 LFC 更适合 phenotype 距离**：不是 marginal gene effect，而是 multivariate 表型
