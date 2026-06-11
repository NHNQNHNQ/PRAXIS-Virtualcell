---
skill_id: scrna_doublet_detect
status: ready
description: |
  scRNA-seq doublet detection on RAW counts BEFORE normalization (rule 02 ordering).
  Backend: scrublet (default) for scRNA; ArchR built-in for scATAC; joint RNA+ADT
  for CITE-seq (rule 09). Output: doublet annotation column + simulation-method
  diagnostics.
inputs:
  h5ad_path: ".h5ad with raw counts in .X (NOT log-normalized)"
  expected_doublet_rate: null  # if null, compute as 0.075 * (n_loaded / 10000)
  method: scrublet  # | doubletfinder | archr | citepro
  modality: scRNA_seq  # | CITE_seq | scATAC_seq
outputs:
  annotated_h5ad: "runs/<task_id>/scrna_doublet_annotated.h5ad"
  doublet_report: "runs/<task_id>/doublet_report.json"
  metrics:
    n_doublet_predicted: int
    doublet_rate: float
    threshold_used: float
qc_check:
  must_emit: [n_doublet_predicted, doublet_rate]
  warn_if:
    doublet_rate: ">15%"  # extremely high → revisit expected_doublet_rate
    doublet_rate: "<2%"   # extremely low → maybe tissue priors off
  reject_if:
    h5ad_X_appears_normalized: true  # raw counts required
evidence_cases:
  - omics-001-scrna-pbmc10k-canonical
  - omics-005-scrna-tumor-malignant-id
  - omics-007-citeseq-bmnc-wnn
related_rules:
  - 02-scrna-qc-priors
  - 09-cite-seq-clr
  - 11-anti-rules-failure-modes
---

# scrna_doublet_detect

## Purpose
Detect doublets BEFORE normalization. Rule 02 ordering: QC → doublet → normalize.
Doing this AFTER normalization contaminates HVG selection (case 001 anti-rule).

## Algorithm
1. Load h5ad. **Verify X is raw counts** (integer or sparse-int) — reject if
   floating-point looks log-normalized.
2. Compute `expected_doublet_rate = 0.075 * (n_loaded / 10000)` if not given.
   Tissue-aware adjustment (case 003): liver hepatocytes are bi-nucleate, do
   NOT inflate doublet rate; tumor doublet rate slightly higher (fusion).
3. Run `scrublet.Scrublet(counts, expected_doublet_rate)` →
   `scrub.scrub_doublets(min_counts=2, min_cells=3, min_gene_variability_pctl=85, n_prin_comps=30)`.
4. For CITE-seq (rule 09): also run joint RNA+ADT doublet via
   muon `mu.pp.intersect_obs` + scrublet on each + intersection
   (CD3+CD19 doublets visible in ADT but not RNA).
5. For scATAC: use ArchR's simulation-based doublet (`addDoubletScores`),
   not scrublet (different generative model).
6. Annotate `obs['doublet_score']` and `obs['predicted_doublet']`.

## Implementation status
**Stub** — runner.py validates inputs only.

## Sanity check
- doublet_rate > 15%: revisit `expected_doublet_rate` or tissue priors.
- doublet_rate < 2%: tissue/library quirks; flag as `confidence: medium`.

## 输出契约

```json
{
  "skill_id": "scrna_doublet_detect",
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
