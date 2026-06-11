---
skill_id: scrna_qc_pipeline
status: ready
description: |
  scRNA-seq QC: read 10x mtx / h5 / h5ad → compute pct_mito / n_genes / total_counts
  → apply organ-specific thresholds (rule 02-scrna-qc-priors) → output filtered AnnData
  + QC metrics + figures (mito distribution, knee plot, per-cluster cell count).
  Ordering: QC → doublet_detect → normalize. Run BEFORE scrna_doublet_detect.
inputs:
  data_path: "10x mtx dir | .h5 | .h5ad"
  tissue: "string (PBMC | bone_marrow | liver | brain | ...) — drives mito% threshold"
  min_genes_per_cell: 200
  max_pct_mito: null  # if null, infer from tissue per rule 02
  min_total_counts: 500
outputs:
  filtered_h5ad: "runs/<task_id>/scrna_qc.h5ad"
  qc_report: "runs/<task_id>/qc_report.json"
  figures: "runs/<task_id>/figures/{mito_distribution.png, knee_plot.png}"
  metrics:
    n_cells_pre_qc: int
    n_cells_post_qc: int
    median_pct_mito: float
    median_n_genes: int
qc_check:
  must_emit: [n_cells_post_qc, median_pct_mito, mito_distribution_figure]
  warn_if:
    n_cells_post_qc_drop_pct: ">50%"  # warn if QC drops more than half
    median_pct_mito: ">25 in PBMC tissue"  # likely tissue mismatch
evidence_cases:
  - omics-001-scrna-pbmc10k-canonical
  - omics-003-scrna-tabula-muris-multitech
  - omics-005-scrna-tumor-malignant-id
related_rules:
  - 02-scrna-qc-priors
  - 11-anti-rules-failure-modes
host_env: praxis-omics
---

# scrna_qc_pipeline

## Purpose
Run scRNA-seq QC with **organ-specific** mito% thresholds and return a
filtered AnnData. Defends against the most common failure mode (rule 11):
flat 5% mito% threshold cleared 30% of real PBMC monocytes (case 001).

## Algorithm
1. Load data (10x mtx / h5 / h5ad) via Scanpy `sc.read_*`.
2. Compute QC: `pct_counts_mt` (genes starting with `MT-` for human, `mt-`
   for mouse), `n_genes_by_counts`, `total_counts`.
3. Resolve thresholds:
   - From `tissue` parameter, look up rule 02 organ table: CNS=5, PBMC=15,
     liver/kidney=25, cardiac=35.
   - If tissue not in table: default 15% with warning.
4. Filter cells: `n_genes >= min_genes_per_cell` AND `total_counts >=
   min_total_counts` AND `pct_counts_mt <= max_pct_mito`.
5. Produce figures:
   - `mito_distribution.png`: violin + histogram with threshold line
   - `knee_plot.png`: cells ranked by total_counts (ambient RNA decision)
6. Emit `qc_report.json` with metrics + thresholds applied + filter rate.

## Implementation status
**Stub** — runner.py validates inputs and emits `simulated: true`. Replace
with the real Scanpy implementation when scrna conda env is provisioned
(see `config/tools.yaml` `conda_envs.scrna`).

## Sanity check
- Cell count drop > 50% → likely wrong tissue / wrong threshold; status: warn.
- median pct_mito after filtering near threshold → tissue/threshold mismatch.

## Reference: case 001
> mito 阈值切 5% 会清掉 30% 真实 mono；PBMC 用 15% 正确。
> Doublet 必须在归一化之前删，否则 HVG 被污染。

## 输出契约

```json
{
  "skill_id": "scrna_qc_pipeline",
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
