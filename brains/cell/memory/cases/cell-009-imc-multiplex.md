---
case_id: cell-009-imc-multiplex
schema_version: 1
task: imaging_mass_cytometry_multiplex
input_data: IMC (Imaging Mass Cytometry) tonsil 30-marker
image_modality: IMC
sample_dimension: 2d_tissue
cell_type: tonsil_tissue
assay_format: slide
channel_count: 30
dataset_accession: null
antibodies_rrid:
  - RRID:AB_2864354
  - RRID:AB_2895110
  - RRID:AB_2864372
  - RRID:AB_2864356
  - RRID:AB_2864359
  - RRID:AB_2864370
software_versions:
  steinbock: ">=0.16"
  scimap: ">=1.0"
  pixie: ">=0.3"
  ilastik: ">=1.4"
tools: [Steinbock pipeline, IMC Tools, ImcSegmentationPipeline, scimap, Pixie, Fiji + MCD viewer]
key_paper_doi: 10.1038/nmeth.2869
provenance:
  source_type: literature
  doi: 10.1038/nmeth.2869
  citation: "Giesen C et al. Highly multiplexed imaging of tumor tissues with subcellular resolution by mass cytometry. Nat Methods. 2014;11(4):417-422."
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: ["RRIDs are representative metal-tagged antibodies; specific lots vary."]
tags: [imc, imaging_mass_cytometry, multiplex, tissue_proteomics, hot_pixel, steinbock, hyperion, isobaric_overlap]
status: validated
---

# IMC (Imaging Mass Cytometry)：tissue 30+ marker spatial proteomics

## Background
IMC = laser ablate tissue + ICP-MS detect heavy metal-tagged antibodies → spatial multiplex 30-50 markers。**与 CODEX 不同**：(1) destructive (one tissue 一次)；(2) lower spatial resolution (~1 μm vs CODEX 0.5)；(3) lower throughput (slow ablation)；(4) 无 fluorescent issues。Hyperion (Fluidigm) 是主流硬件。

## What I actually did
1. **Image stack**：ROI 1 mm² × 30 channel (CD3, CD4, CD8, CD20, FoxP3, CK, Vimentin etc.)
2. **Steinbock pipeline**：
   - Hot pixel removal (IMC artifact)
   - Per-channel intensity normalize (arcsinh or log)
   - Pixel classifier (Ilastik) → 3-class (cell / membrane / background)
   - Cell segmentation (Mesmer 与 CODEX 相同)
3. **Per-cell marker quantification**
4. **Cell typing**: 同 CODEX (knowledge-based + cluster)
5. **Spatial analysis**: scimap neighborhood enrichment
6. **Comparison vs CODEX**: similar pipeline, different artifacts

## ★ 排除/不做的事
- **Hot pixel 不去**: detector artifact 必须 filter
- **Linear intensity (no arcsinh)**: dynamic range > 1000×
- **Fluorescence pipeline 直接套**: IMC has no spectral bleedthrough but has metal isobaric overlap
- **Ignore ablation drift**: laser ablation 慢，sample 在 acquisition 中可能漂移
- **Standard cell phenotype panel ignore tissue context**: tonsil markers vs tumor markers 不同
- **Single ROI per tissue**: spatial heterogeneity miss

## ★ 失败模式
- **Isobaric metal overlap**: ¹⁵⁸Gd vs ¹⁵⁹Tb 类似 mass，detector 区分弱
- **Antibody conjugation efficiency**: different metal labels conjugate differently
- **Tissue thickness affecting ablation**: 5 μm sections standard
- **ROI selection bias**: pathologist-selected ROI vs random sample
- **Ablation depth variability**: laser power affects deeper layer
- **Acquisition time long**: 1 mm² ~ 1-2 hours

## Lessons → seeds for rules
1. **Hot pixel removal** mandatory
2. **arcsinh transform** for dynamic range
3. **Metal isobaric overlap** check in panel design
4. **Steinbock standard pipeline**
5. **Multi-ROI per tissue** for heterogeneity
6. **Antibody panel validation** per metal tag
7. **Acquisition time budget** for mm² scale
