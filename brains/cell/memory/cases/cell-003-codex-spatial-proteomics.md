---
case_id: cell-003-codex-spatial-proteomics
schema_version: 1
task: spatial_proteomics_cell_typing_neighborhood
input_data: 38-marker CODEX image of tonsil tissue
image_modality: CODEX
sample_dimension: 2d_tissue
cell_type: tonsil_tissue
assay_format: slide
channel_count: 38
dataset_accession: idr0073
antibodies_rrid:
  - RRID:AB_2895114
  - RRID:AB_2895089
  - RRID:AB_2895091
  - RRID:AB_2864355
  - RRID:AB_2864363
  - RRID:AB_2864357
software_versions:
  mesmer: ">=0.4"
  scimap: ">=1.0"
  pixie: ">=0.3"
tools: [CODEX MAV (Akoya), Steinbock pipeline, ImcSegmentationPipeline, Pixie, Maui, scikit-image]
key_paper_doi: 10.1016/j.cell.2018.07.010
provenance:
  source_type: literature
  doi: 10.1016/j.cell.2018.07.010
  citation: "Goltsev Y et al. Deep profiling of mouse splenic architecture with CODEX multiplexed imaging. Cell. 2018;174(4):968-981.e15."
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: ["Specific antibody RRIDs depend on lot used; representative IDs listed."]
tags: [codex, spatial_proteomics, multiplex, cell_typing, tonsil, germinal_center, mesmer, neighborhood_analysis]
status: validated
---

# CODEX 38-marker spatial proteomics：cell typing + 邻域

## Background
CODEX (CO-Detection by indEXing) / Akoya PhenoCycler = 多轮抗体 cycling 在同 tissue 上 detect 30-100 markers。**输出**：multiplexed image (X × Y × N marker channel)。Pipeline：segmentation → marker quantification → cell typing → spatial neighborhood。

## What I actually did
1. **Image stack**：tonsil 1.5 mm² × 38 markers (CD3, CD4, CD8, CD20, CD68, FoxP3 etc.)
2. **Segmentation**：Mesmer (TissueNet trained, segmentation in tissue context) > Cellpose (single-cell oriented)
3. **Per-cell marker quantification**：mean intensity per channel within mask
4. **Pre-processing**：arcsinh transform (compress dynamic range), z-score per marker
5. **Cell typing**：
   - **Knowledge-based**：Pixie threshold per marker → call cell type by marker pattern (CD3+CD4+ = CD4 T)
   - **Unsupervised cluster**：Leiden clustering → annotate post-hoc by marker
   - **Reference-mapped**：Maui / SCelltyper transfer label from annotated reference
6. **Spatial neighborhood**：Squidpy / scimap → cell type co-localization enrichment
7. **Tissue domain detection**：cluster cells by neighborhood composition → identify tissue domains (germinal center, T cell zone)
8. **Validation**：known biology — germinal center 应富集 CD20+ B + Ki67 + AID

## ★ 排除/不做的事
- **Cellpose for tissue context**：Mesmer / TissueNet trained on tissue better
- **Mean intensity without arcsinh**：marker dynamic range 跨 100×
- **Single cell type method**：knowledge-based + clustering 双方法 cross-check
- **Forget marker QC**：weak / failed antibody confounds typing
- **No spatial validation**：cell type call without spatial sanity (germinal center 应 B-rich)
- **Bleed-through not corrected**：adjacent cycle marker 残留

## ★ 失败模式
- **Antibody non-specificity**：commercial antibody 跨 cycle 性能不一
- **Tissue artifact**：fold / tear → segmentation fail in those region
- **Marker spillover**：strong signal 临近 weak marker
- **Z-stack imaging**：3D tissue 切 2D slice 损 marker continuity
- **Batch effect across slides**：sample prep variability → marker intensity shift
- **Rare cell type underdetected**：< 1% population 难 cluster

## Lessons → seeds for rules
1. **Mesmer / TissueNet** for tissue segmentation
2. **arcsinh + z-score** preprocessing
3. **Knowledge-based + clustering** dual cell typing
4. **Marker QC** mandatory (antibody validation per cycle)
5. **Spatial sanity check** (known biology)
6. **Batch effect** across slides handle
7. **Rare cell type** flag low confidence
