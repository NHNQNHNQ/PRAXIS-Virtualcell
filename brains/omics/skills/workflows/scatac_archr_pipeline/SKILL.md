---
skill_id: scatac_archr_pipeline
status: ready
description: |
  scATAC-seq end-to-end via ArchR + chromVAR. LSI not PCA, drop component 1
  (depth proxy). Iterative peak calling: tile → LSI → cluster → MACS3 per
  cluster → union peak → re-LSI on peak matrix. QC = TSS enrichment + nFrag
  + fragment size periodicity (NOT mito% — nuclear prep). Doublet detection
  by ArchR simulation method, NOT scrublet (different generative model).
  Analysis at motif level via chromVAR.
inputs:
  fragments_path: ".tsv.gz fragments file (chr / start / end / barcode / count)"
  organism: Homo sapiens  # | Mus musculus
  genome: hg38  # | mm10
  tile_size_bp: 500
  tss_enrichment_min: 4.0
  n_frag_min: 1000
  drop_lsi_component_1: true   # rule 08
  doublet_method: archr_simulation  # | amulet
  random_seed: 0
outputs:
  arrowfile: "runs/<task_id>/arrowfiles/<sample>.arrow"
  cell_peak_matrix: "runs/<task_id>/cell_peak_matrix.h5"
  motif_activity: "runs/<task_id>/chromvar_motif_activity.csv"
  figures:
    - "runs/<task_id>/figures/tss_enrichment.png"
    - "runs/<task_id>/figures/fragment_size_periodicity.png"
    - "runs/<task_id>/figures/lsi_components.png"
    - "runs/<task_id>/figures/motif_lineage_heatmap.png"
  metrics:
    n_cells_pre_qc: int
    n_cells_post_qc: int
    median_tss: float
    median_n_frag: int
    lsi_components_used: list[int]
    n_peaks_called: int
    n_motifs_active: int
qc_check:
  must_emit: [median_tss, median_n_frag, n_peaks_called, n_motifs_active]
  warn_if:
    median_tss: "< 4.0"
    n_peaks_called: "< 10000"
  reject_if:
    pca_used_instead_of_lsi: true   # rule 08
    lsi_component_1_kept: true       # rule 08
    bulk_peak_set_used: true         # case 009 anti-rule
    mito_qc_applied: true            # case 009 anti-rule
evidence_cases:
  - omics-009-scatac-buenrostro-hematopoiesis
related_rules:
  - 08-scatac-lsi
  - 11-anti-rules-failure-modes
  - 12-reproducibility-and-provenance
---

# scatac_archr_pipeline

## Purpose
scATAC-seq end-to-end. Defends against case 009's documented failure modes:
PCA on raw counts (poor signal), bulk peak set (misses cell-type-specific),
LSI component 1 contamination (depth proxy), per-peak DE (sparse), mito%
QC (no mito reads in nuclear prep).

## Algorithm
1. Build ArchR ArrowFile from fragments, tile = `tile_size_bp` bp bins.
2. QC: TSS enrichment ≥ `tss_enrichment_min`, nFrag ≥ `n_frag_min`,
   fragment-size periodicity (mono-/di-nucleosome).
3. Doublet detection: ArchR `addDoubletScores` (simulation method,
   case 009).
4. **LSI** (TF-IDF + SVD), 50 components. **Drop component 1** (depth proxy,
   rule 08).
5. Cluster on LSI components 2–30; UMAP; Leiden.
6. **Per-cluster MACS3 peak calling**; union peak set; re-LSI on cell × peak.
7. **chromVAR motif activity**: per-cell TF motif z-score with GC background
   correction.
8. Sanity anchor: GATA1 motif activity high in erythroid lineage; PU.1 in
   myeloid (case 009).
9. Optional: Palantir trajectory pseudotime (after MAGIC smoothing) for
   lineage analysis.

## Reference: case 009
> scATAC 用 LSI 不用 PCA, 并丢第一个 component (depth proxy)。
> Iterative peak calling: tile → LSI → cluster → per-cluster MACS → union peak → re-LSI。
> TSS enrichment + nFrag 是 QC 主指标, 不是 mito%。
> 分析升一级: peak → motif (chromVAR) → gene activity, 因 single-peak 信号太稀。

## 输出契约

```json
{
  "skill_id": "scatac_archr_pipeline",
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
