---
name: da_compositional
description: |
  Compositional-aware differential abundance via R: ANCOM-BC2 + MaAsLin2 +
  LinDA running in parallel; cross-method consensus (significant in ≥2 methods
  → high_confidence). Refuses --rarefy flag (rule-12). Refuses raw t-test
  (rule-05).
inputs:
  abundance_table:  TSV (required)  feature × sample integer counts
  metadata_tsv:     TSV (required)  sample metadata; first col = sample_id
  formula:          str (default "case_vs_control + age + sex")
  methods:          list (default [ancombc2, maaslin2, linda])
  prevalence_min:   float (default 0.10)
  mean_abund_min:   float (default 5e-5)
  out_subpath:      str (required)
outputs:
  da_per_method:        TSV (one file per method with effect + adj p)
  consensus_da:         TSV (features significant in ≥2 methods)
  effect_sizes:         TSV (per-method log fold change)
env: da (remote)
status: ready
stage: execution
domain: stats
---

# da_compositional

## Purpose
Run modern compositional-aware DA methods on a microbiome count table; require ≥2-method consensus before declaring a finding high-confidence. Implements rules-05 + 12.

## Sanity baseline (1000 taxa, 30 spiked)
Simulated abundance table with 30 of 1000 features given 5× shifts; 970 null.
- Pass: ≥80% recall on 30 spiked features at adj p<0.1; ≤5% false discovery on null features.

## Usage
```bash
python -m skills.workflows.da_compositional.run \
    --abundance-table runs/task-005/asv_table.tsv \
    --metadata-tsv runs/task-005/metadata.tsv \
    --formula "diagnosis + age + sex + bmi" \
    --out-subpath runs/task-005/da_out
```

## 输出契约

```json
{
  "skill_id": "da_compositional",
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
