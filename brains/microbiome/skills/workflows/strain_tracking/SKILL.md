---
name: strain_tracking
description: |
  Strain-level tracking from longitudinal shotgun metagenomic samples:
  StrainPhlAn4 (marker SNVs) + inStrain (population genetics SNV + coverage) +
  midas2 (pangenome). Implements rule-09. P2 stub.
inputs:
  reads_dir:        str (required)  longitudinal samples
  reference_strain: str (default GTDB strain reference)
  min_coverage:     int (default 5)
  out_subpath:      str (required)
outputs:
  strainphlan_tree: NWK
  instrain_snv:     TSV
  midas2_panels:    TSV
env: kraken (remote, with strainphlan + instrain + midas2)
status: skeleton
stage: execution
domain: strain
---

# strain_tracking (P2 stub)

## 输出契约

```json
{
  "skill_id": "strain_tracking",
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
