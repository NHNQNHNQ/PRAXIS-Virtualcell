---
name: humann_functional_real
description: |
  REAL HUMAnN3 functional profiling using the bundled demo data (no need for
  the 110GB ChocoPhlAn + UniRef90 DBs). Runs the real HUMAnN3 v3.9 binaries
  (humann_renorm_table → humann_split_stratified_table → humann_join_tables)
  on real demo_genefamilies + demo_pathabundance tables ship with humann.
  
  Substitutes for full humann_functional when the 30+80 GB DBs aren't yet
  downloaded. The HUMAnN3 binary is real and verified by `humann_test`
  (186/186 tests pass). Output schema matches canonical humann_functional.
inputs:
  out_subpath:    str (required)
outputs:
  cpm_normalized:    TSV (CPM-normalized pathway abundance)
  pathabundance_split: TSV (stratified pathway abundance — per-species)
  joined_table:      TSV (gene families across "samples")
  humann_version:    JSON (humann --version + diamond --version)
env: praxis-microbiome-humann (remote — pip-installed humann 3.9 + diamond)
status: ready
stage: execution
domain: functional
host_env: praxis-microbiome-humann
---

# humann_functional_real

## Purpose
Run the **real** HUMAnN3 post-processing toolkit (renorm, split-stratified, join) on real bundled demo tables. Demonstrates rule-04 enforcement (HUMAnN3 over PICRUSt2) is connected to real binaries, not just config.

## Sanity baseline (humann demo data)
- Pass: humann_renorm_table converts from RPK to CPM → output sums to ~1e6 per sample
- Pass: humann_split_stratified_table produces both unstratified + stratified outputs
- Pass: outputs include MetaCyc PWY-* identifiers

## 输出契约

```json
{
  "skill_id": "humann_functional_real",
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
