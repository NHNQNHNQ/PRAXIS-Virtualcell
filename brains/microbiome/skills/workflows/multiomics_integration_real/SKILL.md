---
name: multiomics_integration_real
description: |
  REAL multi-omics integration via sklearn CCA + scipy Spearman pairwise.
  Substitutes for MOFA+/mixOmics R packages. Implements rule-07 (multi-omics
  triangulation): 2 complementary methods (latent factor + per-feature
  pairwise) on the same paired matrices.
inputs:
  microbe_table:    TSV (required)  microbiome abundance feature × sample
  host_rna_table:   TSV (required)  host RNA-seq counts feature × sample
  metabolite_table: TSV (optional)  metabolite intensity feature × sample
  out_subpath:      str (required)
  n_components:     int (default 3)  CCA components
  top_k:            int (default 20)  top Spearman pairs to report
outputs:
  summary_json:     JSON (CCA canonical correlations per omics pair)
  top_pairs_tsv:    TSV (top-k correlated feature pairs across omics)
env: praxis-microbiome (remote — base env numpy + scipy + sklearn)
status: ready
stage: execution
domain: multiomics
---

# multiomics_integration_real

## Purpose
Real multi-omics integration without R. CCA finds latent factors (MOFA-style); Spearman finds per-feature relationships (MaAsLin2-style). Together they satisfy rule-07's triangulation principle.

## Sanity baseline
Reference: `tests/baselines/multiomics_mock/{microbe,host_rna,metabolite}.tsv` (30 samples, 50/100/30 features; 5 microbe-RNA + 3 microbe-metabolite truly linked via shared latent driver).
- Pass: top-5 Spearman microbe-RNA pairs include ≥3 of the 5 linked pairs.

## 输出契约

```json
{
  "skill_id": "multiomics_integration_real",
  "n_samples": 0,
  "taxonomy_table": "",
  "diversity_metrics": {
    "shannon": 0.0,
    "observed_otus": 0
  },
  "diagnostics": {
    "brain": "microbiome",
    "archetype": "microbiome_pipeline"
  }
}
```
