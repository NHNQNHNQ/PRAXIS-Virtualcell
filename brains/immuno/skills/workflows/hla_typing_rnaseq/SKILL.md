---
name: hla_typing_rnaseq
description: (auto-generated stub from parity rewrite v2; please fill)
status: green
host_env: PRAXIS-CRISPR-bins
---
# hla_typing_rnaseq ⭐ MVP

4-digit HLA-I/II typing from RNA-seq fastq with ≥ 3-caller consensus (rule 02 + rule 05).

## Inputs

```json
{
  "fastq_paths": ["sample_R1.fastq.gz", "sample_R2.fastq.gz"],
  "read_count_min": 30000000,
  "callers": ["OptiType", "arcasHLA", "HLA-LA"],   // ≥ 3 (rule 02)
  "require_consensus_count": 2,
  "classes": ["I", "II"],
  "tumor_paired_normal_fastq": null
}
```

## Outputs

```json
{
  "skill_id": "hla_typing_rnaseq",
  "n_epitopes": 0,
  "epitopes_csv": "",
  "diagnostics": {
    "brain": "immuno",
    "archetype": "mhc_epitope"
  }
}
```

## Tools (real runner, Linux)

- OptiType (Python pkg)
- arcasHLA (Python + samtools)
- HLA-LA (graph-aligner; needs reference graph)
- seq2HLA, xHLA, Polysolver (additional)

## --simulate behavior

Stable mock haplotype `A*02:01,A*03:01 / B*07:02,B*15:01 / C*07:02,C*06:02 / DRB1*15:01,DRB1*04:01` (random hashed). Consensus tied to deterministic seed.

## Sanity QC

- callers count ≥ 3 (rule 02)
- All output alleles 4-digit format (rule 02)
- consensus ≥ 2/3 per locus

## Sanity test (deferred)

1000 Genomes RNA-seq sample → 4-digit consensus ≥ 95% accuracy vs PCR-SBT truth (`tests/sanity/test_hla_typing_consensus.py`).
