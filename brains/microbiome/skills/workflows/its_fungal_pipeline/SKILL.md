---
name: its_fungal_pipeline
description: |
  Fungal ITS amplicon pipeline: ITSxpress region extraction → DADA2 (modified
  parameters for ITS variable length) → UNITE 10.0 species hypothesis classifier
  → FUNGuild functional guild assignment. Implements rule-06 (UNITE not SILVA).
  P1 stub — skeleton documents the planned pipeline but does not execute.
inputs:
  reads_dir:        str (required)
  region:           str (default ITS1)  ITS1 | ITS2
  reference_db:     str (default UNITE10.0)
  out_subpath:      str (required)
outputs:
  fungal_asv_table: TSV
  fungal_taxonomy:  TSV
  funguild:         TSV (functional guild per ASV)
env: qiime2 (remote, with itsxpress + funguild add-on)
status: skeleton
stage: execution
domain: fungal
---

# its_fungal_pipeline (P1 stub)

P1 stub — returns `simulated: true` and describes the real pipeline. To
promote to ready, install ITSxpress + FUNGuild in the qiime2 conda env on the
remote server and replace the simulate-only branch with the real shell
pipeline.

## 输出契约

```json
{
  "skill_id": "its_fungal_pipeline",
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
