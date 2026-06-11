---
name: cooccurrence_network
description: |
  Microbial co-occurrence network: SparCC + SPIEC-EASI + FlashWeave (rule-08).
  Compositional-aware methods only — Pearson on raw count is rejected.
  Output: edge list + Leiden community detection.
inputs:
  abundance_table: TSV (required)  feature × sample, ≥50 samples
  method:          str (default sparcc)  sparcc | spieceasi | flashweave
  min_samples:     int (default 50)
  out_subpath:     str (required)
outputs:
  edge_list:       TSV (source, target, weight, p_value)
  modules:         TSV (Leiden community assignment per node)
env: da (remote with SpiecEasi + FlashWeave + python sparcc)
status: skeleton
stage: execution
domain: network
---

# cooccurrence_network (P1 stub)

## 输出契约

```json
{
  "skill_id": "cooccurrence_network",
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
