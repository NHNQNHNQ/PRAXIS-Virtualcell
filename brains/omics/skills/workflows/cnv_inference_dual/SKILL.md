---
skill_id: cnv_inference_dual
status: ready
description: |
  Tumor-cell identification via dual-tool CNV inference (rule 05 consensus).
  inferCNV + CopyKAT run in parallel; consensus rule: BOTH aneuploid AND tumor
  origin → malignant; either fails → ambiguous. Reference cells must be known-
  diploid immune cells (T cells preferred, NK risks NKT contamination).
inputs:
  h5ad_path: ".h5ad with epithelial subset (post-annotation)"
  reference_cell_type: "T_cell | B_cell (known-diploid immune ref)"
  reference_h5ad: ".h5ad subset of immune cells"
  window_size_genes: 100
  cutoff: 0.1
  copykat_genome: "hg20 | mm10"
  random_seed: 0
outputs:
  cnv_h5ad: "runs/<task_id>/cnv_annotated.h5ad"
  consensus_table: "runs/<task_id>/cnv_consensus.tsv"
  figures:
    - "runs/<task_id>/figures/infercnv_heatmap.png"
    - "runs/<task_id>/figures/copykat_pred.png"
  metrics:
    n_malignant: int
    n_diploid: int
    n_ambiguous: int
    consensus_rate: float
    infercnv_only_pos: int
    copykat_only_pos: int
qc_check:
  must_emit: [n_malignant, n_ambiguous, consensus_rate]
  warn_if:
    consensus_rate: "< 0.6"     # high disagreement → review
    n_malignant: "0 in tumor sample"  # likely false negative
  reject_if:
    single_method_only: true     # rule 05
    reference_includes_NKT_NK_only: true  # case 005 anti-rule
evidence_cases:
  - omics-005-scrna-tumor-malignant-id
related_rules:
  - 05-multimethod-consensus
  - 11-anti-rules-failure-modes
---

# cnv_inference_dual

## Purpose
Tumor cell ID is the hardest call in tumor scRNA. Marker (EPCAM/KRT19) is
ambiguous because normal alveolar type 2 also expresses them. The right
answer is **CNV inference with two tools, agree-or-flag** (rule 05).

## Algorithm
1. Verify `reference_cell_type ∈ {T_cell, B_cell}` — reject NK/NKT only
   (case 005 failure: NK reference contamination by NKT inflates baseline).
2. Run inferCNV with given window/cutoff. Output per-cell CNV score matrix.
3. Run CopyKAT in parallel with same reference. Output binary
   aneuploid/diploid + GMM probability.
4. Consensus rule:
   - Both call aneuploid AND sample is tumor (not normal-adjacent) → `malignant`
   - Both call diploid → `diploid`
   - Either disagrees → `ambiguous` (route to review)
5. Per-patient subclone analysis: hierarchical cluster CNV scores within each
   patient (NOT cross-patient — case 005 anti-rule).

## Reference: case 005
> 肿瘤恶性识别 ≥ 2 工具交集（inferCNV + CopyKAT 或 + Numbat），单一工具不接受。
> Reference 必须是已知 diploid 免疫细胞（最好 T cell，丰度高、CNV 干净）。
> Subclone 分析在 patient 内做，不跨 patient。

## 输出契约

```json
{
  "skill_id": "cnv_inference_dual",
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
