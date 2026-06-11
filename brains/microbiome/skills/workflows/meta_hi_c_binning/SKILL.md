---
name: meta_hi_c_binning
description: |
  Hi-C augmented MAG binning: bin3C (Hi-C contact-graph clustering) + MetaCC
  alongside standard MetaBAT2/CONCOCT/MaxBin2 for the same shotgun assembly.
  Plasmid-host edges output explicitly (rule-10). P2 stub.
inputs:
  shotgun_reads_dir: str (required)
  hi_c_reads_dir:    str (required)
  restriction_enzyme: str (required)  e.g. MluCI, Sau3AI
  out_subpath:       str (required)
outputs:
  improved_mags: FA
  plasmid_host_edges: TSV
env: mag (remote, with bin3C + MetaCC + HiC-Pro)
status: skeleton
stage: execution
domain: hi_c
---

# meta_hi_c_binning (P2 stub)

## 输出契约

```json
{
  "skill_id": "meta_hi_c_binning",
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
