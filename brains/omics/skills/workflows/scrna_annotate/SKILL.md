---
skill_id: scrna_annotate
status: ready
description: |
  Cell-type annotation with DUAL-SOURCE evidence (rule 05 multi-method consensus):
  CellTypist (auto) + manual marker check. Single-source annotation rejected.
  Output: cell_type column + per-cell confidence + concordance flag.
inputs:
  h5ad_path: ".h5ad post-integration with cluster column"
  organism: Homo sapiens  # for HGNC vs MGI marker DB
  reference_model: "Immune_All_Low.pkl | Immune_All_High.pkl | custom (CellTypist .pkl)"
  manual_marker_set: "dict[cell_type] → list[gene] (≥ 2 markers per type)"
  cluster_column: leiden  # which obs col groups cells
outputs:
  annotated_h5ad: "runs/<task_id>/annotated.h5ad"
  annotation_report: "runs/<task_id>/annotation_report.json"
  metrics:
    n_cell_types_assigned: int
    cluster_concordance_rate: float  # fraction of clusters where auto + manual agree
    review_clusters: list[int]       # discordant clusters
qc_check:
  must_emit: [n_cell_types_assigned, cluster_concordance_rate]
  warn_if:
    cluster_concordance_rate: "< 0.7"
  reject_if:
    only_one_source: true  # rule 05
evidence_cases:
  - omics-001-scrna-pbmc10k-canonical
  - omics-003-scrna-tabula-muris-multitech
  - omics-007-citeseq-bmnc-wnn
related_rules:
  - 05-multimethod-consensus
  - 11-anti-rules-failure-modes
host_env: praxis-omics
---

# scrna_annotate

## Purpose
Annotate cell types via two independent sources: automated (CellTypist) +
manual marker check. Per rule 05, single-source is rejected. Discordant
clusters are flagged for human review (rule 05 consensus rules).

## Algorithm
1. Run CellTypist with reference_model on the AnnData.
2. For each cluster, score against manual_marker_set (≥ 2 markers per
   cell type, rule 11 anti-rule).
3. Compare CellTypist majority vote vs manual marker top-vote per cluster.
4. Concordance rate = fraction of clusters where both agree at the
   broad-class level (e.g., "T cell" matches "CD4 T" or "CD8 T").
5. Discordant clusters → `review_clusters` list; their `cell_type` column
   gets `_review` suffix and `confidence: low`.
6. Per case 003: in brain, CellTypist accuracy < 60%; require explicit
   `reference_model="Allen_Brain_atlas.pkl"` else flag warn.
7. Per case 007: CITE-seq, also require ADT marker concordance (separate
   skill `multimodal_annotate` will be implemented later).

## Implementation status
**Stub.**

## Reference: case 001
> 注释 = 自动 + 至少 2 marker 手工交叉，单一来源不接受。
> 单 marker 注释 cluster：CD8A 在 NK 也有，MS4A1 在 plasmablast 已下调。

## 输出契约

```json
{
  "skill_id": "scrna_annotate",
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
