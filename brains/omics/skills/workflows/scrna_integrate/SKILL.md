---
skill_id: scrna_integrate
status: ready
description: |
  Integrate multiple scRNA samples / batches via Harmony (default) or scVI
  (GPU) or BBKNN (exploratory). MUST set batch_key NOT to biology of interest
  (rule 04). Quality metrics: kBET / iLISI for batch mixing AND a biology
  preservation anchor (e.g. ISG15 LFC ≥ 2.5 for IFN data).
inputs:
  h5ad_path: "concatenated AnnData with `obs[batch_key]` and `obs[biology_key]`"
  batch_key: "donor | platform | lane | patient (NOT condition / cell_type / etc)"
  biology_key: "the variable to preserve (condition / patient_subtype / ...)"
  method: harmony  # | scvi | bbknn
  scvi_epochs: 400
  scvi_latent_dim: 10
  hvg_count: 2000
  n_pcs: 30
  random_seed: 0
outputs:
  integrated_h5ad: "runs/<task_id>/integrated.h5ad"
  integration_report: "runs/<task_id>/integration_report.json"
  metrics:
    method: str
    kbet_score: float
    iLISI: float
    biology_preservation_metric: float  # method-specific anchor
    n_cells: int
    cluster_count: int
qc_check:
  must_emit: [kbet_score, biology_preservation_metric]
  warn_if:
    biology_preservation_metric: "< case_anchor_threshold"
    kbet_score: "< 0.5"
  reject_if:
    batch_key_eq_biology_key: true
evidence_cases:
  - omics-002-scrna-kang-ifnb-integration
  - omics-003-scrna-tabula-muris-multitech
  - omics-005-scrna-tumor-malignant-id
related_rules:
  - 04-batch-vs-biology
  - 05-multimethod-consensus
  - 12-reproducibility-and-provenance
---

# scrna_integrate

## Purpose
Integrate samples removing batch while preserving biology. Hardest pitfall:
setting `batch_key = condition` ablates IFN response (case 002). The skill
**rejects** that configuration.

## Algorithm
1. Validate `batch_key != biology_key` (rule 04 — REJECT if violated).
2. HVG selection per batch then intersect (case 003: cross-platform HVG bias).
3. Method:
   - **harmony** (`harmonypy.run_harmony(pca, batch=batch_key, vars_use=[batch_key])`)
   - **scvi** (`scvi.model.SCVI(adata, batch_key=batch_key)`, train epochs)
   - **bbknn** (exploratory only — soft clusters)
4. Compute kBET for batch mixing; iLISI for batch + cluster mixing.
5. Compute biology-preservation anchor:
   - Case 002 IFN: ISG15 stim/ctrl log2FC after integration ≥ 2.5
   - Case 005 tumor: per-patient subclone CNV variation preserved
   - Case 003 atlas: tissue identity Adjusted Rand Index ≥ 0.7
6. Output integrated_h5ad with `obsm['X_scVI']` or `obsm['X_pca_harmony']`.

## Implementation status
**Stub** — runner.py validates inputs.

## Hard rule
batch_key cannot equal biology_key — rule 04. Skill returns
`status: rejected` with code `RULE_04_VIOLATION`.

## Reference: case 002
> Kang IFN-β: batch_key 设 condition → IFN signature 全部消失。
> 正确：batch_key=donor (8 supplied); biology_key=condition (ctrl|stim).

## 输出契约

```json
{
  "skill_id": "scrna_integrate",
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
