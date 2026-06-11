---
case_id: cell-015-bbbc021-caicedo-profiling
schema_version: 1
task: morphological_deep_profiling
input_data: BBBC021 — 38 compounds × 6 doses × Cell Painting 3-channel images
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: MCF7
assay_format: 96well
channel_count: 3
dataset_accession: BBBC021
antibodies_rrid: []
software_versions:
  cellprofiler: ">=4.2"
  pycytominer: ">=1.0"
  deepprofiler: ">=0.3"
tools: [CellProfiler 4, pycytominer, DeepProfiler, scikit-learn, BBBC021 dataset]
key_paper_doi: 10.1038/nmeth.4397
provenance:
  source_type: literature
  doi: 10.1038/nmeth.4397
  citation: "Caicedo JC et al. Data-analysis strategies for image-based cell profiling. Nat Methods. 2017;14(9):849-863."
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
tags: [cell_painting, bbbc021, mcf7, morphological_profiling, moa, reference_dataset, caicedo, pycytominer]
status: validated
---

# BBBC021 + Caicedo profiling：Cell Painting 标准 reference benchmark

## Background
BBBC021（Ljosa 2012）= MCF7 breast cancer cells × 38 compounds × 6 dose × 3-channel fluorescence (DNA / β-tubulin / actin)，每化合物 annotated 12 mechanism-of-action (MoA) classes（actin disruptor / DNA damage / Aurora kinase inhibitor / microtubule stabilizer / ...）。**Caicedo 2017 Nat Methods** 是 image-based cell profiling 标准方法学综述，定义 NSC (Not-Same-Compound) / NSCB (Not-Same-Compound-or-Batch) 评估 metric。

## What I actually did
1. **Input**: 39,604 images (8 batches × 55 plates × 12 fields × 3 channels)
2. **Per-cell features (CellProfiler)**: 1500+ measurements (intensity / shape / texture / radial distribution / neighbor relationships)
3. **Per-well aggregation**: median across cells (typical N ~ 600 cells per field, ~5000 cells per well)
4. **Normalization**:
   - **Per-plate** DMSO control median + MAD (robust z-score)
   - Across-plate: NO simple z-score; use NSCB-aware quantile normalization
5. **Feature selection**: drop features with > 0.9 correlation; drop features with < 0.01 variance; ~500-700 features remain
6. **MoA classification benchmark**:
   - Compute per-compound profile (median across replicates, batches)
   - K-NN with treatment-level NSC distance (closest non-self compound)
   - Accuracy = % treatments whose NN has same MoA
7. **Caicedo 2017 reports**: ~70-94% NSC MoA accuracy depending on profile method (CellProfiler 70%; CNN deep features 94%)
8. **Validation**: Known active compound (taxol microtubule stabilizer) clusters with epothilone B (also microtubule stabilizer); cytochalasin D clusters with latrunculin B (both actin disruptors)

## ★ 排除/不做的事
- **Z-score across plates without batch correction**：batch effect dominates
- **Mean (not median) cell aggregation**: outlier cells skew profile
- **Drop features post-hoc by p-value**：data leakage if MoA known at training
- **Single replicate compound profile**：no batch / well variance estimate
- **Use NSCB unwarranted**: NSCB is stricter than NSC; report both
- **Skip whitening (sphering / PCA-whitening)**: collinear features dominate distance
- **Per-image profile (not per-well)**: image-to-image noise inflates variance
- **Compare across labs without harmonization**: stains / objectives / cell line passages differ

## ★ 失败模式
- **Known cytotoxic compound dominance**：generic cell-death phenotype masks specific MoA
- **Polypharmacology**：compound has multiple MoA → mixed cluster membership
- **Concentration-dependent MoA shift**：subtle phenotype at low dose, generic toxic at high dose
- **Batch / plate / day effect**: even with normalization, residual structure remains
- **Cell line drift**: passage > 30 → phenotype shift
- **Annotation noise**: literature MoA labels are coarse / inconsistent
- **Imbalanced MoA classes**: some MoA only 1-2 compounds → classification benchmark biased

## Lessons → seeds for rules
1. **DMSO per-plate normalize + cross-plate quantile**
2. **Per-well median (not mean / not per-image)**
3. **Feature selection (variance + correlation pruning) before profile**
4. **NSC + NSCB metrics** (not single-fold CV)
5. **Multi-replicate per compound** (≥ 4 wells / 2 plates)
6. **Reference compound anchors** (taxol, latrunculin B, ...) in every screen
7. **Compute / version provenance**: log CellProfiler pipeline version, feature list
8. **Cell line passage tracking** (BBBC021 = passage 7-15 MCF7)
