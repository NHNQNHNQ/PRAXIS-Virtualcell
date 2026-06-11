---
name: da_compositional_real
description: |
  REAL compositional-aware differential abundance via R: MaAsLin2 or ANCOM-BC2.
  Satisfies rule-05 (compositional-aware required) and rule-12 (no rarefaction).
  Runs in praxis-microbiome-da-v2 (R + ANCOMBC + MaAsLin2 provisioned). Reads an
  abundance matrix (samples × taxa) + sample metadata with a group column, fits
  the chosen DA model, writes a per-feature results table.
inputs:
  abundance_csv:  CSV (required)  rows = samples, cols = taxa (counts); first col = sample id
  metadata_csv:   CSV (required)  first col = sample id, must contain the group_col column
  group_col:      str (default "group")  metadata column with the case/control grouping
  method:         str (default "ancombc")  one of: ancombc | maaslin2
outputs:
  taxonomy_table:    CSV  per-feature DA results
  diversity_metrics: JSON {shannon, observed_otus}
  n_samples:         int
env: praxis-microbiome-da-v2 (R + ANCOMBC + MaAsLin2; phyloseq absent → ancombc path requires phyloseq, maaslin2 path runs standalone)
status: ready
stage: execution
domain: stats
host_env: praxis-microbiome-da-v2
---

# da_compositional_real

## Purpose
Compositional-aware DA via R (MaAsLin2 / ANCOM-BC2) in the praxis-microbiome-da-v2 env. Real, canonical DA models.

## Sanity baseline (synthetic)
Spike 30 of 1000 features with 5× shift; 970 null.
- Pass: ≥80% recall on spiked at q<0.10; ≤5% FDR on null.

## 输出契约

```json
{
  "skill_id": "da_compositional_real",
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
