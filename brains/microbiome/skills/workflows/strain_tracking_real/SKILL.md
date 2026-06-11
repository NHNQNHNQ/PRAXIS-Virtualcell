---
name: strain_tracking_real
description: |
  REAL strain-level SNV calling from bowtie2-aligned reads.
  Substitutes for StrainPhlAn4/inStrain when their marker DBs aren't
  provisioned. Implements rule-09 strain resolution principle: per-position
  per-sample dominant base → SNV table → Hamming distance between samples.
  Architecturally similar to inStrain (Olm 2021) without the marker DB.
inputs:
  reads_dir:        str (required)  multi-sample paired-end fastq.gz
  reference_fasta:  str (required)
  out_subpath:      str (required)
  min_alt_freq:     float (default 0.10)
  min_coverage:     int (default 5)
  n_threads:        int (default 8)
outputs:
  snv_table:        TSV (reference × position × per-sample dominant + coverage)
  strain_distance:  TSV (Hamming distance between samples per reference)
  summary_json:     JSON
env: praxis-microbiome-kraken (remote — bowtie2 + python)
status: ready
stage: execution
domain: strain
host_env: praxis-microbiome-humann
---

# strain_tracking_real

## Purpose
Real strain-resolved analysis without StrainPhlAn4 marker DB. bowtie2-align reads from N samples against reference fasta, walk CIGAR to assign bases to ref positions, find positions where samples disagree on dominant base, compute pairwise Hamming distances.

## Sanity baseline
With our 2-sample synthetic mock having identical reference content, expect 0 SNVs (samples are identical at the base level). With samples having distinct strains, expect non-zero Hamming distance per reference. This run primarily verifies the CIGAR-walking pipeline runs correctly.

## 输出契约

```json
{
  "skill_id": "strain_tracking_real",
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
