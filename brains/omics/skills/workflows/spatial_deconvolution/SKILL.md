---
skill_id: spatial_deconvolution
status: ready
description: |
  Spatial transcriptomics deconvolution: per-spot cell-type proportion via
  cell2location + Tangram (rule 05 + rule 07). Requires PAIRED scRNA reference;
  rejects if missing. Output proportion matrix per spot + boundary review flags
  + Moran's I spatially-variable-gene list.
inputs:
  spatial_h5ad: ".h5ad with obsm['spatial'] coordinates"
  reference_h5ad: "paired scRNA reference (same tissue, same organism strain)"
  cell_type_column: "obs col in reference (e.g. 'cell_type')"
  method: cell2location  # | tangram | rctd; default runs both for consensus
  cell2loc_n_cells_per_location: 30
  cell2loc_detection_alpha: 200
  random_seed: 0
outputs:
  proportion_matrix: "runs/<task_id>/spatial_proportions.csv (spot × cell_type)"
  consensus_h5ad: "runs/<task_id>/spatial_deconv.h5ad"
  spatial_var_genes: "runs/<task_id>/morani_spatial_var_genes.tsv"
  figures:
    - "runs/<task_id>/figures/cell_type_spatial.png"
    - "runs/<task_id>/figures/boundary_review.png"
  metrics:
    n_spots: int
    n_cell_types: int
    boundary_review_count: int          # spots where methods disagree
    method_agreement_rate: float
    rare_cell_types_detected: list[str]  # e.g. Purkinje for cerebellum
qc_check:
  must_emit: [method_agreement_rate, rare_cell_types_detected]
  warn_if:
    method_agreement_rate: "< 0.6"
    rare_cell_type_missing: "Purkinje for cerebellum; layer markers for cortex"
  reject_if:
    no_paired_reference: true   # rule 07
    single_method_only: true    # rule 05
evidence_cases:
  - omics-006-spatial-slideseq-cerebellum
related_rules:
  - 05-multimethod-consensus
  - 07-spatial-deconvolution
  - 11-anti-rules-failure-modes
---

# spatial_deconvolution

## Purpose
Per-spot cell-type proportion is the central spatial inference. Per rule 07,
this requires a paired scRNA reference (same tissue, ideally same strain).
Per rule 05, ≥ 2 methods must agree. Boundary spots where layers meet are
flagged for review (deconvolution uncertainty).

## Algorithm
1. Verify `reference_h5ad` is non-empty and tissue overlaps spatial sample.
   Refuse if missing (rule 07).
2. Train cell2location reference signature; map to spatial:
   ```
   cell2location.models.RegressionModel.setup_anndata(reference_h5ad, ...)
   reg = cell2location.models.RegressionModel(reference_h5ad); reg.train(epochs=250)
   inf = cell2location.models.Cell2location(spatial_h5ad, cell_state_df=...)
   inf.train(max_epochs=30000, lr=0.002)
   ```
3. Run Tangram in parallel: map cells to spots (no mixture model — different
   ground truth, useful as cross-check).
4. Compute per-spot cell-type proportions for each method.
5. Boundary review: for each spot, if top cell-type call differs across methods
   → flag.
6. Spatial gene discovery: Squidpy `gr.spatial_autocorr(method='moran')`.
7. Sanity anchors:
   - Cerebellum: Calb1 spatially restricted to Purkinje layer (case 006).
   - Cortex: layer markers (Cux1, Foxp2) layer-restricted.

## Reference: case 006
> Spatial deconvolution 必须有 paired scRNA reference, 且 cell type granularity 决定空间分辨率。
> 跑 ≥ 2 deconvolution 方法 (cell2location + Tangram 或 + RCTD), 分歧 spot 标 review。
> HVG 改用 spatially variable gene selection (SpatialDE/SpaGCN)。

## 输出契约

```json
{
  "skill_id": "spatial_deconvolution",
  "matrix_path": "",
  "n_cells_post_qc": 0,
  "cluster_sizes": {},
  "marker_genes_per_cluster": {},
  "umap_png": "",
  "diagnostics": {
    "brain": "omics",
    "archetype": "omics_scrna"
  }
}
```
