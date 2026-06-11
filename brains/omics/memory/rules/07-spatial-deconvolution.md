---
rule_id: 07-spatial-deconvolution
rule_type: case_distilled
applies_to:
  modality: spatial_transcriptomics
  study_design: ALL
  tissue_class: ALL
  task: deconvolution
evidence_cases:
  - case_id: omics-006-spatial-slideseq-cerebellum
    page_hint: "Step 3 (paired scRNA reference); Step 5 (cell2location + Tangram)"
confidence: high
status: active
created: 2026-04-29
---

# Spatial deconvolution requires a paired scRNA reference

## Statement
1. Spatial deconvolution (cell2location / Tangram / RCTD) requires a **paired
   scRNA reference** of the same tissue, ideally same organism strain.
2. **Cell-type granularity in reference = upper bound on spatial resolution**.
3. **≥ 2 deconvolution methods** must run in parallel; disagreement spots get
   `_review` flag.
4. **Per-puck / per-section batch**: each tissue section is its own batch; do
   not concatenate naively.
5. **HVG → spatially variable genes**: prefer Moran's I or SpatialDE/SpaGCN
   over standard mean-variance HVG for downstream.

## Why
- No reference → unsupervised NMF gives spatial pattern but cannot map to
  biology (case 006 anti-rule).
- Cross-strain reference (e.g. B6 atlas → BALB/c spatial): some markers fail.
  Confidence: medium with explicit caveat.
- cell2location alone: NB overdispersion misfits highly-expressed genes;
  Tangram alone: no mixture model. Disagreement at layer boundaries reveals
  algorithm uncertainty (case 006).
- < 1% cell type detection unreliable; require robustness across ≥ 2 methods +
  ≥ 5 spots before reporting.

## Sanity checks per tissue
- Slide-seq cerebellum: Calb1 spatially restricted to Purkinje cell layer (case 006).
- Visium cortex: Snap25 across all neurons; layer markers (Cux1, Foxp2) layer-restricted.

## Cold-start fallback
- No paired scRNA → block deconvolution; switch to:
  - Spatially variable gene discovery (no cell-type assignment).
  - Marker-based per-spot scoring (lower confidence, label `medium`).
  - Recommend user collect / find a paired scRNA reference.
