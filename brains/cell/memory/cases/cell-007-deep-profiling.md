---
case_id: cell-007-deep-profiling
schema_version: 1
task: morphological_deep_profiling
input_data: HCS 多 perturbation × per-cell features (1000+ features)
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: U2OS
assay_format: 384well
channel_count: 6
dataset_accession: idr0080
antibodies_rrid: []
software_versions:
  cellprofiler: ">=4.2"
  pycytominer: ">=1.0"
  deepprofiler: ">=0.3"
  scikit-learn: ">=1.0"
tools: [CellProfiler 4 + features module, DeepProfiler, scikit-learn (UMAP / PCA), pycytominer]
key_paper_doi: 10.1038/s41467-024-45999-1
provenance:
  source_type: literature
  doi: 10.1038/s41467-024-45999-1
  citation: "Moshkov N et al. Learning representations for image-based profiling of perturbations. Nat Commun. 2024;15:1594. (DeepProfiler / Cell Painting deep representation learning)"
  extracted_at: 2026-04-30
  extraction_confidence: high
  unverified_details: []
  doi_corrected_v0_4: "Was 10.1038/s41592-022-01666-1 (m6A paper, unrelated); corrected via real CrossRef QA on 2026-04-30."
tags: [cell_painting, deep_profiling, morphological_profiling, cellprofiler, deepprofiler, moa, lincs, perturbation]
status: validated
---

# Cell Painting + DeepProfiler：morphological profiling

## Background
Cell Painting （Bray 2016）= 6 染色 (cytoplasm, nuclei, mitochondria, ER, actin, RNA) → 1500+ morphological features per cell。**目的**：化合物 / siRNA 处理 → cell phenotype "fingerprint" → cluster 找 mechanism-of-action (MoA)。DeepProfiler 用 DL embedding 替代手工 features (1024 dim ResNet)。

## What I actually did
1. **Cell Painting 6 channel image**：~5000 cells per well, 384-well plate
2. **Per-cell feature extraction**：CellProfiler measures 1500+ features per cell (intensity / shape / texture / radial distribution)
3. **Per-well profile**：median / aggregate cell features → 1500-dim profile per well
4. **Normalize**：DMSO control / per-plate / robustize (median + MAD)
5. **Feature selection**：variance threshold + correlation > 0.9 prune
6. **Cluster (UMAP + Leiden)**：similar profiles → similar MoA
7. **Reference compound matching**：query compound profile vs annotated reference (e.g., LINCS L1000 morphology) → predicted MoA
8. **DeepProfiler alternative**：CNN trained on Cell Painting → 1024-dim embedding → similar downstream

## ★ 排除/不做的事
- **Per-image profile (not per-well)**：image-to-image variability noise
- **Mean cell feature without per-cell distribution**：lose heterogeneity
- **No control normalize**：plate effect dominate signal
- **All 1500 features without selection**：collinear features dominate distance
- **MoA call without reference compound**：predicted MoA without anchor 不可信
- **Single feature engineering / DL choice**：CellProfiler + DeepProfiler dual confirm

## ★ 失败模式
- **Cell-cycle confound**：proliferating cell + arrest compound → confound
- **Toxicity vs MoA**：generic cytotoxic phenotype masks specific MoA
- **Concentration effect**：profile changes with dose → multi-concentration profile required
- **Batch effect across plate**：staining / imaging batch affect features
- **Edge well artifact**：HCS edge bias
- **Heterogeneous cell population**：cancer cell line drift across passages

## Lessons → seeds for rules
1. **Per-well profile (median across cells) + per-cell distribution**
2. **DMSO control + plate normalization**
3. **Feature selection** (variance + correlation pruning)
4. **Reference compound MoA database** (e.g., LINCS) for matching
5. **Multi-concentration profile** for dose-MoA
6. **CellProfiler + DeepProfiler cross-check**
7. **Cell cycle / cytotoxicity confound** flag
