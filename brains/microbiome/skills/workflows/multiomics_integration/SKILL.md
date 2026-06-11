---
name: multiomics_integration
description: |
  Host + microbe + metabolite integration: MOFA+ (factor analysis) +
  mixOmics (DIABLO sparse PLS) + MaAsLin2 (per-omics association) + MIMOSA
  (mediation). Implements rule-07 (triangulation required). P1 stub.
inputs:
  microbiome_table: TSV (required)  feature × sample
  host_rna_table:   TSV (optional)
  metabolite_table: TSV (optional)
  metadata_tsv:     TSV (required)
  out_subpath:      str (required)
outputs:
  mofa_factors:    TSV (latent factors × sample)
  mixomics_blocks: TSV (per-block loadings)
  maaslin_assoc:   TSV (per-omics × outcome)
  mimosa_mediation: TSV (microbe → metabolite → host chains)
env: da (remote, with mofapy2 + mixOmics)
status: skeleton
stage: execution
domain: multiomics
---

# multiomics_integration (P1 stub)

## 输出契约

```json
{
  "skill_id": "multiomics_integration",
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
