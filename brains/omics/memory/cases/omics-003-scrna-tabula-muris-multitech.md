---
case_id: omics-003-scrna-tabula-muris-multitech
modality: scRNA_seq
study: Tabula Muris (Schaum 2018)
public_accession: GSE109774
doi: 10.1038/s41586-018-0590-4
organism: Mus musculus
tissue: 20 organs, multi-batch, dual-platform
tools:
- Scanpy 1.10
- scvi-tools 1.1
status: validated
validated: true
source: praxis_seed
study_design: cohort_atlas
assay_subtype: smartseq2_and_10x_v2
cell_type_focus:
- cross_tissue_atlas
method_choice:
- scvi
- scanvi
- celltypist
- azimuth
case_class: success
---

# Tabula Muris：跨技术 + 跨组织整合最难场景

## Background
Tabula Muris 一次性测了 20 个小鼠器官，每个器官同时用 **Smart-seq2（FACS-sorted, plate-based, full-length）** 和 **10x Chromium v2（droplet, 3'）** 两种技术。这是测试 cross-tech integration 的唯一公开金标准。

## What I actually did
1. **不要把两个 platform 当 batch 整合到一起做 final analysis**——drop-out 模式根本不同（Smart-seq 长 transcript 全长覆盖、10x 仅 3' poly-A）
2. **正确做法**：分别 per-platform 走标准 pipeline → cell type 独立注释 → **post-hoc 比较** cell type 是否一致（用 SingleR/Azimuth label transfer）
3. 若必须整合（如做 atlas），用 **scVI/scANVI with `batch_key='platform'`** + 大量 donor sample 做 batch
4. **HVG 选择按 platform 独立做**再求交集——Smart-seq HVG 偏向长基因，10x 偏向短基因；naive 合并 HVG 会偏
5. **跨组织 cell type 命名标准化**：用 Cell Ontology（CL ID）而不是文本——同样是 "macrophage" 在肝（Kupffer）、肺（alveolar mac）、脑（microglia）是不同细胞 type

## ★ 排除/不做的事
- **Cellranger output 直接和 STARsolo Smart-seq output cbind**：count distribution 不可比
- **跨 platform Wilcoxon DE**：technical artifact 完全淹没生物学
- **统一 mito% 阈值跨所有 20 个器官**：肝/肾代谢高 mito 25% 是正常，神经元 5% 已经是死细胞——必须 per-tissue threshold 表
- **靠单一 cell type 注释包**：CellTypist 在脑组织 < 60% 准确，需要 Allen Brain reference

## ★ 失败模式
- **Platform-specific dropout**：Smart-seq 看到的 lowly-expressed TF（< 5 TPM）在 10x 里完全 zero——cell state 比较时这些 TF 被错误标"丢失"
- **Tissue-specific QC**：Liver hepatocyte 自然双核 → doublet detector 会假阳；需 tissue-aware doublet rate prior
- **Ambient RNA 跨组织差异巨大**：Pancreas islet 因为 acinar cell 强表达消化酶，ambient 污染显著高
- **Annotation drift**：同样 marker（CD11b/Itgam）在不同器官指代不同 myeloid lineage

## ★ QC sanity check (known answer)
- Anchor (Tabula Muris GSE109774, cross-platform)：
  - 同一组织在 Smart-seq2 + 10x v2 上注释 cell type 的 ARI ≥ 0.7（用 SingleR/Azimuth label transfer）
  - Liver: hepatocyte > 60%；Pancreas: acinar > 30%（兼检 ambient correction）
  - Per-platform HVG 交集 ≥ 30%（< 10% 表明 platform bias 主导）
  - 跨组织 cell type 用 CL ID 而非文本（macrophage 在肝/肺/脑是不同 CL）
- Pass criterion：ARI ≥ 0.7 AND 组织 cell type 主型符合预期
- Fail criterion：ARI < 0.5 → cross-platform 整合错（HVG 合并而非交集？）

## Lessons → seeds for rules
1. **跨 platform 默认不整合**：分开分析 + post-hoc 比较是 safe baseline；若要整合用 scVI 且 platform 入 batch_key
2. **QC 阈值表 organ-specific**：mito 范围 5%（CNS）/15%（PBMC, immune）/25%（liver, kidney）/35%（cardio acutely stressed）
3. **Cell type ontology 强制**：用 CL ID 不用文本名，跨组织/跨研究才可比
4. **HVG 跨技术取交集**而非合并，避免 platform bias 渗入下游
5. **Doublet rate prior tissue-aware**：肝 hepatocyte 多核；肿瘤 doublet rate 偏高（fusion）
