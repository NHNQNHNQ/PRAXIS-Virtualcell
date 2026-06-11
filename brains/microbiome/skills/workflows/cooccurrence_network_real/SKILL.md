---
name: cooccurrence_network_real
description: |
  REAL pure-Python SparCC compositional network inference (Friedman & Alm 2012,
  10.1371/journal.pcbi.1002687) — implements rule-08 (compositional-aware
  network methods) without depending on the original SparCC R package.
  Supports `sparcc` (iterative basis-correlation) and `spearman_clr` (CLR-
  transformed Spearman). Hard-rejects Pearson on raw count.
inputs:
  abundance_table:    TSV (required)  feature × sample integer counts
  method:             str (default sparcc)  sparcc | spearman_clr (pearson REJECTED)
  n_iter:             int (default 20)
  n_perms:            int (default 50)  bootstrap p-value permutations
  correlation_cutoff: float (default 0.30)
  p_cutoff:           float (default 0.10)
  out_subpath:        str (required)
outputs:
  edges_tsv:          TSV (source, target, correlation, p_value, edge_class)
  summary_json:       JSON (method, n_significant_edges, params)
env: praxis-microbiome (remote — uses base env numpy + scipy)
status: ready
stage: execution
domain: network
---

# cooccurrence_network_real

## Purpose
Real pure-Python SparCC implementation. Promotes the `cooccurrence_network` P1 stub to a working real skill that doesn't need the original SparCC R package or SpiecEasi/FlashWeave (all of which have install hassles).

## Sanity baseline (DA fixture reused)
Reference: `tests/baselines/da_mock/abundance.tsv` (100 features × 40 samples; 30 spiked together in case group → should form a positively-correlated cluster).
- Pass: ≥10 significant edges among the 30 spiked features at SparCC correlation ≥ 0.30 + p < 0.10.

## Usage
```bash
python -m skills.workflows.cooccurrence_network_real.run \
    --abundance-table tests/baselines/da_mock/abundance.tsv \
    --out-subpath runs/network-real-001/out
```

## 输出契约

```json
{
  "skill_id": "cooccurrence_network_real",
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
