---
case_id: cell-010-phenotype-clustering
schema_version: 1
task: phenotype_landscape_clustering
input_data: 10000 compound × 1500 morphological features
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: U2OS
assay_format: 384well
channel_count: 6
dataset_accession: idr0080
antibodies_rrid: []
software_versions:
  pycytominer: ">=1.0"
  scanpy: ">=1.10"
  umap-learn: ">=0.5"
  leidenalg: ">=0.10"
  hdbscan: ">=0.8"
tools: [pycytominer, UMAP, Leiden, hdbscan, scanpy (adapt for cytometry data)]
key_paper_doi: 10.1038/nprot.2016.105
provenance:
  source_type: literature
  doi: 10.1038/nprot.2016.105
  citation: "Bray M-A et al. Cell Painting, a high-content image-based assay for morphological profiling using multiplexed fluorescent dyes. Nat Protoc. 2016;11(9):1757-1774. (Foundational Cell Painting protocol; phenotype landscape clustering downstream)"
  extracted_at: 2026-04-30
  extraction_confidence: high
  unverified_details: []
  doi_corrected_v0_4: "Was 10.1038/s41592-022-01666-1 (m6A paper, unrelated); corrected via real CrossRef QA on 2026-04-30. cell-007 and cell-010 no longer share DOI."
tags: [phenotype_landscape, umap, leiden, hdbscan, moa_inference, reference_compound, polypharmacology, cell_painting]
status: validated
---

# Phenotype clustering：化合物 phenotype landscape + MoA 推断

## Background
HCS 化合物筛选给每化合物一个 high-dim morphological profile。**目标**：cluster phenotype landscape → similar phenotype = similar MoA。**核心方法**：UMAP embed → Leiden cluster → reference MoA matching。

## What I actually did
1. **Per-compound profile**：1500 features × 10000 compounds matrix
2. **Normalize**：median + MAD per feature, plate-aware
3. **Feature selection**：drop low variance (< 0.01), drop highly correlated (> 0.9)，剩 ~500 features
4. **Dimensionality reduction**：PCA to 50, then UMAP to 2D
5. **Cluster**：Leiden resolution 0.5-1.5 sweep, hdbscan as alternative
6. **Reference compound annotation**：known MoA compounds (kinase inhibitor, ER stress, microtubule, DNA damage etc.) as anchors in landscape
7. **Cluster annotation**：each cluster centroid distance to reference → assign MoA
8. **Novel cluster identification**：cluster far from any reference = potential novel MoA
9. **Validation**：known MoA compound 应聚到 expected cluster (e.g., taxol with other microtubule disruptors)

## ★ 排除/不做的事
- **Cluster without reference annotation**：cluster ID 无 biological meaning
- **t-SNE for HCS profile**：UMAP 在 high-dim biological data 表现 better
- **Single resolution Leiden**：try multiple resolutions
- **Toxic compound 不 separate**：generic cytotoxic dominate cluster
- **DMSO control 不 include**：should map to "no effect" zone
- **Forget concentration**：per-compound at multiple concentrations 给 trajectory not point

## ★ 失败模式
- **Cluster collapse**：normalization / scaling 错让所有 compound look similar
- **Mode-of-action 模糊**：similar phenotype 不一定 same MoA (downstream effects similar)
- **Polyptarmacology**：化合物 multi-target → mixed phenotype hard cluster
- **Concentration variability**：low dose subtle / high dose generic toxic
- **Cell line specificity**：HCS 在 U2OS vs HeLa 不同 phenotype
- **Reference annotation incomplete**：MoA library 覆盖 < 10% druggable space

## Lessons → seeds for rules
1. **PCA → UMAP → Leiden** standard pipeline
2. **Reference compound anchoring** for MoA call
3. **Multi-resolution clustering** sweep
4. **Toxic compound separate cluster**
5. **Multi-concentration trajectory** > single point
6. **Cell line specificity** flag
7. **Novel cluster** mark for follow-up investigation
