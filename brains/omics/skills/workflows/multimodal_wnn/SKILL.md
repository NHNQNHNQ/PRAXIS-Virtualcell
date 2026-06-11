---
skill_id: multimodal_wnn
status: ready
description: |
  CITE-seq RNA + ADT integration via Weighted Nearest Neighbors (Seurat WNN /
  totalVI / muon). Per rule 09: ADT must be CLR-normalized + isotype-subtracted.
  Joint RNA+ADT doublet detection (CITE-seq doublets show CD3+CD19, missed by
  RNA-only). Annotation requires concordance between RNA marker and ADT marker.
inputs:
  cite_h5ad: "AnnData with .X = RNA counts and .obsm['ADT'] or .layers['adt']"
  adt_normalization: clr  # | log (rejected — rule 09)
  isotype_columns: "list[str] of isotype-control antibody columns"
  method: seurat_wnn  # | totalvi | muon
  totalvi_epochs: 400
  random_seed: 0
outputs:
  wnn_h5ad: "runs/<task_id>/wnn_integrated.h5ad"
  annotation_concordance: "runs/<task_id>/rna_adt_concordance.tsv"
  figures:
    - "runs/<task_id>/figures/wnn_umap.png"
    - "runs/<task_id>/figures/adt_density_bimodality.png"
  metrics:
    n_cells: int
    rna_adt_concordance_rate: float    # fraction of clusters where markers agree
    review_clusters: list[int]
    isotype_subtracted: bool
    cite_doublet_count: int
qc_check:
  must_emit: [rna_adt_concordance_rate, isotype_subtracted, cite_doublet_count]
  warn_if:
    rna_adt_concordance_rate: "< 0.7"
    no_isotype_columns: true
  reject_if:
    adt_normalization: log    # rule 09
    rna_only_doublet_used: true
evidence_cases:
  - omics-007-citeseq-bmnc-wnn
related_rules:
  - 05-multimethod-consensus
  - 09-cite-seq-clr
  - 11-anti-rules-failure-modes
host_env: praxis-omics
---

# multimodal_wnn

## Purpose
CITE-seq RNA + ADT integration. Three failure modes (rule 09 / 11) avoided:
1. ADT log-normalize (compositional structure ignored) → rejected.
2. RNA-only doublet detection (CD3+CD19 CITE doublets missed) → rejected.
3. `cbind` ADT into RNA matrix for PCA (scale dominance) → rejected.

## Algorithm
1. Verify `adt_normalization == 'clr'`; reject otherwise.
2. Apply CLR to ADT layer: `clr(x) = log(x / geomean(x_isotypes_subtracted))`.
3. Subtract per-cell mean isotype before WNN if `isotype_columns` provided.
4. Run joint RNA+ADT doublet via muon → drop predicted doublets.
5. Method:
   - **seurat_wnn**: per-cell weighted RNA / ADT neighbor learning
   - **totalvi**: Bayesian latent with explicit protein background (GPU)
   - **muon**: framework-level WNN (Python)
6. Annotation: per cluster, check RNA marker top vote and ADT marker top vote
   agree at broad-class level; discordant clusters → `_review`.
7. Compute concordance rate; ADT density bimodality plot to flag noisy
   antibodies.

## Reference: case 007
> ADT 用 CLR 不用 log-normalize；忽略 compositional 性质 CD4 量"高"可能只是因为 cell 总抗体多。
> WNN/totalVI/MOFA+ 多模态专用方法，不允许直接 cbind 不同 modality。
> Doublet 检测必须双模态——RNA-only doublet detection miss CITE-seq 特有 doublet 类型。

## 输出契约

```json
{
  "skill_id": "multimodal_wnn",
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
