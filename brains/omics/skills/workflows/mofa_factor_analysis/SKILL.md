---
skill_id: mofa_factor_analysis
status: ready
description: |
  Multi-omics factor analysis via MOFA+ (mofapy2). Per-modality independent
  normalization to comparable scale; n_factors via elbow analysis; sparsity
  prior on (spike-and-slab); multi-seed (≥10) for reproducibility; cross-
  modality factor validation (variance ≥5% in ≥2 modalities). Rejects
  pre-imputation (MOFA has native missing support).
inputs:
  views_paths: "list[str] of per-modality matrix files (RNA, methylation, drug, mutation, ...)"
  view_names: "list[str] matching views_paths"
  n_factors: 10
  n_factors_elbow_search: [5, 10, 15, 20]
  sparsity_prior: spike_slab  # | normal
  ard_relevance: true
  n_seeds: 10
  cosine_similarity_threshold: 0.8     # robust factor cutoff
  random_seed: 0
outputs:
  mofa_model: "runs/<task_id>/mofa_model.hdf5"
  factor_loadings: "runs/<task_id>/factor_loadings.tsv"
  variance_explained: "runs/<task_id>/variance_explained.tsv"
  figures:
    - "runs/<task_id>/figures/variance_per_factor_per_view.png"
    - "runs/<task_id>/figures/factor_value_vs_metadata.png"
  metrics:
    n_factors_robust: int                 # cross-seed cosine > threshold
    factor_variance_explained: dict       # per factor per view
    n_dominant_modality_factors: int      # phantom factor count (single-view dominance)
    seed_stability: float                 # mean cosine across seeds
qc_check:
  must_emit: [n_factors_robust, factor_variance_explained, seed_stability]
  warn_if:
    seed_stability: "< 0.8"
    n_dominant_modality_factors: "> 0.3 of total"
  reject_if:
    pre_imputed_input: true              # case 008 anti-rule
    no_per_view_normalization: true      # case 008 anti-rule
    n_factors: "> 25"                    # phantom factor risk
evidence_cases:
  - omics-008-mofa-cll-multiomics
related_rules:
  - 10-multiomics-mofa
  - 11-anti-rules-failure-modes
  - 12-reproducibility-and-provenance
---

# mofa_factor_analysis

## Purpose
Multi-modality factor analysis. Anchors per case 008: factor 1 should
separate IGHV mutated vs unmutated CLL across all 4 modalities (RNA, meth,
drug, mut). Phantom factors (single-modality dominance) are rejected by
cross-modality variance check.

## Algorithm
1. Load each view; verify per-view independent normalization (z-score / unit
   variance). Reject if user pre-imputed (MOFA handles missing natively).
2. Align samples across views; drop samples missing any view (no imputation).
3. Elbow search: train MOFA at each n_factors in `n_factors_elbow_search`;
   pick at variance plateau.
4. Train MOFA at chosen n_factors with `n_seeds` seeds.
5. Compute robust factors: cosine similarity > threshold across seeds.
6. Per-factor cross-modality validation: variance explained ≥ 5% in ≥ 2 views.
7. Output: mofa_model.hdf5, factor_loadings, variance_explained,
   per-factor diagnostic plots.

## Reference: case 008
> MOFA 前每个 modality 独立 normalize 到可比 scale（z-score 或 unit variance）。
> n_factors 跑 elbow analysis：variance explained vs factors 拐点（通常 5-15）。
> Sparsity prior 强制开（spike-and-slab）以便解释。
> Factor validation 跨 modality：variance > 5% 在 ≥ 2 modality 才算 robust factor。
> Reproducibility：多 seed 取 stable factors（cosine similarity > 0.8 across runs）。

## 输出契约

```json
{
  "skill_id": "mofa_factor_analysis",
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
