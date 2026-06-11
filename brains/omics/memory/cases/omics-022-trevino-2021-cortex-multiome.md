---
case_id: omics-022-trevino-2021-cortex-multiome
schema_version: 1
modality: scRNA_seq
study: "Trevino et al 2021, Chromatin and gene-regulatory dynamics of the developing human cerebral cortex at single-cell resolution"
public_accession: "GSE162170"
doi: 10.1016/j.cell.2021.07.039
organism: Homo sapiens
tissue: "fetal cerebral cortex (PCW 16, 20, 21, 24)"
study_design: time_course
assay_subtype: 10x_chromium_multiome_paired_rna_atac
cell_type_focus: [neural_progenitor, intermediate_progenitor, neuron_lineage, layer_specific]
tools: [Cellranger-arc 2.0, Signac 1.7, Seurat 4.0 WNN, ArchR 1.0, scVI 0.16, MultiVI 0.20, chromVAR 1.12]
method_choice: [10x_multiome_paired, wnn_integration, peak_gene_linkage, multivi_joint, motif_chromvar]
status: validated
validated: true
source: praxis_seed
case_class: success
provenance:
  source_type: literature
  doi: 10.1016/j.cell.2021.07.039
  extracted_at: 2026-05-01
tags: [multiome, paired_rna_atac, fetal_cortex, time_course, multimodal_integration]
---

# Trevino 2021：fetal cortex Chromium Multiome（RNA + ATAC 同细胞配对）

## Background
10x Chromium Multiome（RNA + ATAC 来自同一 cell，不是 batch correction）在 fetal cerebral cortex (PCW 16-24) 上的应用。同细胞测两 modality，避免了 case 016 (Visium) / case 009 (Buenrostro 仅 ATAC) 的 modality-跨样本对齐问题，但引入新挑战：peak-gene linkage 在 cell type pool 时大量假阳性，motif enrichment 被高丰度 cell type 主导。**case-based learning 角度**：跨模态联合分析的 best practice — Multiome 是当前 paired multimodal 的事实标准，与 case 007 (CITE-seq 仅 RNA+ADT，shared cell) 互补但更复杂（基因组覆盖维度高得多）。

## What I actually did
1. **Cellranger-arc** 处理 raw fastq → 配对 RNA + ATAC matrix per cell（同一 GEM）
2. **Joint QC**：cell 同时通过 RNA QC（n_genes ≥ 200, mito% ≤ 10）AND ATAC QC（TSS enrichment ≥ 4, nFrag ≥ 1000）；任一失败该 cell 丢
3. **Per-modality preprocessing**：
   - RNA：normalize + log1p + scale + HVG (3000) + PCA
   - ATAC：iterative LSI（rule 08：drop component 1 = depth proxy）
4. **Joint integration**: 三种方法 cross-check（rule 05 多方法 consensus）：
   - **WNN (Seurat)**：per-cell weighted neighbor learning across RNA + ATAC
   - **MultiVI (scvi-tools)**：joint VAE on RNA + ATAC
   - **ArchR + RNA addon**：RNA matrix added to ArchR project for shared embedding
5. **Joint clustering** + **annotation**：use both modalities — RNA marker call + ATAC accessibility at marker loci must agree
6. **Peak-gene linkage** (Signac `LinkPeaks`)：correlate peak accessibility ↔ gene expression **per cell type**（不在 pooled cell 上 — 强制 anti-rule）
7. **Motif enrichment** (chromVAR)：per-cell-type motif activity；**对于丰度差异大的 cell type 要 stratify**（避免 low-abundance type signal 被淹没）
8. **Trajectory inference**：along developmental stages PCW 16→24，用 RNA+ATAC 联合 Slingshot；NPC → IPC → ExN/InN lineage

## ★ 排除/不做的事
- **`cbind` RNA + ATAC matrix 直接 PCA**：scale 和分布完全不同；强制 join modality 必用 WNN / MultiVI / MOFA
- **Pooled-cell peak-gene linkage**：cross-cell-type pooled correlation 假阳率极高（peak A 在 NPC 高 + gene B 在 NPC 高 ≠ A regulates B in NPC）
- **ATAC QC 用 mito%**：scATAC nuclear prep 几乎无 mito read（rule 08 / case 009 反规则的延伸到 Multiome）
- **HVG only on RNA when annotating ATAC clusters**：要 jointly select features (HVG + 高变 peak)
- **MultiVI 默认用 RNA token + ATAC token 不区分 modality**：必须 setup_anndata with `modality_keys`
- **跨 stage (PCW) batch_correct 当 nuisance**：stage 是生物轴 (rule 13 time_course)；batch_key=technical 而非 stage

## ★ 失败模式
- **Doublet detection 单 modality 失败**：单 RNA 检 doublet (scrublet) 错过 ATAC-only doublet (高 nFrag 但 RNA 低 → 看似 stressed cell 实为 doublet)；解：AMULET (ATAC-aware) + scrublet 双过滤
- **Peak-gene linkage 跨 cell type 假阳**：原始论文 reanalysis 显示 30-50% pooled linkage 在 cell-type-stratified 后消失
- **Cell type ambiguity in transitional cell**：IPC (intermediate progenitor) 在 RNA 看似 NPC，ATAC 已开始 commit；标 review，不强制 binary call
- **Stage label imprecise**：PCW 估算 ±1 周；trajectory pseudotime 比 stage label 更稳
- **RNA-ATAC 表达-可及性时间差**：transcription factor (TF) ATAC site 提前 open 数小时-数天 才表达 → linkage 是 lagged (cause: TF binding 先于 transcription)
- **Library complexity bias**：低 read depth cell 在 ATAC 看似封闭，假"closed chromatin"；nFrag normalize 必做
- **Motif enrichment 受 GC bias**：chromVAR 必须用 GC-matched background

## ★ 方法选择决策链
```
配对 multimodal (Multiome / SHARE-seq / SNARE-seq) 数据?
├─ YES → joint integration
│   ├─ Cell type focus → WNN (Seurat, fast)
│   ├─ Trajectory/development → MultiVI 或 scVI multimodal (latent space 更稳)
│   ├─ Multi-batch atlas → MultiVI + batch correction
│   └─ Peak-gene 调控关系 → Signac LinkPeaks + cell-type stratified
├─ ATAC alone → ArchR (rule 08)
└─ RNA alone → standard rule 02-06 path

Joint QC?
├─ Cell通过 IF AND ONLY IF (RNA OK AND ATAC OK)
├─ 不能"RNA 好但 ATAC 差就用 RNA only" — 该 cell 在 doublet 检测里就该被剔
└─ Doublet via AMULET (ATAC) + scrublet (RNA) 双过滤
```

## ★ QC sanity check (known answer)
- Anchor (Trevino 2021 cortex)：
  - **SOX2 RNA + ATAC accessibility 相关** in NPC (TF binding to its own promoter)
  - **FOXP2** RNA-restricted to deep-layer ExN; matching ATAC site near FOXP2 promoter open
  - **NEUROD2 motif activity** highest in newborn neurons; not in NPC
  - **Layer markers**: SATB2 (upper layer), TBR1 (deep layer), CUX2 (L2-3) — RNA + ATAC 同向
  - WNN clustering ARI vs manual annotation ≥ 0.7
  - Stage trajectory: PCW 16 (NPC-rich) → PCW 24 (mature neuron-rich)，沿 trajectory 单调
- Pass criterion: layer marker RNA + ATAC 同向 + stage trajectory 单调
- Fail criterion: WNN 把 NPC 混到 mature neuron → integration 过校正；peak-gene linkage > 50% 在 random 对照中也阳性 → cross-cell-type pooled bias

## Lessons → seeds for rules
1. **Multiome 配对 cell ≠ 解决一切**：仍需 stratify（cell type）做 peak-gene linkage 才避假阳
2. **Joint QC 必双门**：RNA + ATAC 两侧都过 cell 才进，不允许 single-modality fallback
3. **Doublet 双过滤**：AMULET (ATAC) + scrublet (RNA) 互补
4. **Multimodal integration ≥ 2 method**（rule 05 延伸）：WNN + MultiVI cross-check 跨 cell type 一致
5. **Stage 是 biology**（rule 13 echo）：不 correct 进 batch
6. **Motif chromVAR 必带 GC background**：default ON；否则 GC-rich/poor regions 假阳
7. **TF ATAC 提前 open 几小时-几天**：linkage 是 lagged；trajectory 上比较 expression vs accessibility 时考虑
