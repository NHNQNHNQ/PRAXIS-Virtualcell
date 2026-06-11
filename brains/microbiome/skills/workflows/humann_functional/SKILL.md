---
name: humann_functional
description: |
  Functional metagenomic profiling via HUMAnN3 (ChocoPhlAn v311 + UniRef90
  201901b → MetaCyc pathways). Refuses 16S input (rule-04 — must use shotgun).
  Output: gene_families.tsv, pathabundance.tsv, pathcoverage.tsv,
  cpm_normalized.tsv.
inputs:
  reads_dir:        str (required)  remote dir with paired host-removed shotgun .fq.gz
  metaphlan_dir:    str (optional)  precomputed MetaPhlAn output (faster)
  chocophlan_db:    str (default v311 path)
  uniref90_db:      str (default 201901b path)
  data_source:      str (required)  must be "shotgun"; "16s" rejected
  norm:             str (default cpm)  cpm | relab
  n_threads:        int (default 16)
  out_subpath:      str (required)
outputs:
  gene_families:     TSV (UniRef90 gene families × sample)
  pathabundance:     TSV (MetaCyc pathway × sample)
  pathcoverage:      TSV (pathway coverage)
  cpm_normalized:    TSV (CPM-normalized counts)
env: humann (remote)
status: ready
stage: execution
domain: functional
host_env: praxis-microbiome-humann
---

# humann_functional

## Purpose
Convert shotgun metagenomic reads → per-species gene-family counts → MetaCyc pathway abundances. Implements rule-04: refuses 16S/PICRUSt2 substitution.

## Sanity baseline (iHMP IBD pathway recovery)
Reference: subset of iHMP IBD shotgun (PRJNA398089).
- Pass: ≥75% (9/12) of known IBD-DA pathways recovered at adj p<0.1 when paired with `da_compositional`.
- Known pathways include `PWY-7222: guanosine deoxynucleotides de novo II`, `PWY-5675: nitrate reduction V`.

## Usage
```bash
python -m skills.workflows.humann_functional.run \
    --reads-dir /home/zkyd/data2/mzy/PRAXIS-Microbiome/runs/task-003/host_removed \
    --metaphlan-dir runs/task-003/shotgun_out/metaphlan4 \
    --data-source shotgun --out-subpath runs/task-003/humann_out
```

## 输出契约

```json
{
  "skill_id": "humann_functional",
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
