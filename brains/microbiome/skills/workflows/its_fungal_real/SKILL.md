---
name: its_fungal_real
description: |
  REAL ITS amplicon abundance via fastp + bowtie2 against a fungal reference
  fasta. Substitutes for canonical its_fungal_pipeline (UNITE classifier +
  ITSxpress + FUNGuild) when those aren't provisioned. Implements rule-06
  (use UNITE-family fungal references, not SILVA).
inputs:
  reads_dir:        str (required)
  reference_fasta:  str (default tests/baselines/its_mock/references.fasta)
  out_subpath:      str (required)
  n_threads:        int (default 8)
outputs:
  abundance_table:  TSV (sample × fungal taxon)
  per_sample_json:  JSON
env: praxis-microbiome-kraken (remote — fastp + bowtie2 already there)
status: ready
stage: execution
domain: fungal
host_env: praxis-microbiome-kraken
---

# its_fungal_real

## Purpose
Real ITS pipeline using only tools confirmed in `praxis-microbiome-kraken`. Demonstrates rule-06 by routing fungal reads against fungal references (Saccharomyces / Candida / Aspergillus / Penicillium / Malassezia ITS1 sequences).

## Sanity baseline
Reference: `tests/baselines/its_mock/{sample01_stool,sample02_skin}_R{1,2}.fastq.gz`.
- Pass: ≥4/5 input fungal genera recovered; sample01 dominated by Saccharomyces+Candida; sample02 dominated by Malassezia.

## 输出契约

```json
{
  "skill_id": "its_fungal_real",
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
