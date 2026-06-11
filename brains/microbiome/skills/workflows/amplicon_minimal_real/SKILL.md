---
name: amplicon_minimal_real
description: |
  REAL minimal 16S amplicon abundance pipeline using only tools confirmed
  installed on remote (fastp + bowtie2 + Python SAM parser). Built specifically
  to demonstrate end-to-end "real case-based learning" without QIIME2/SILVA
  download requirements. Aligns paired-end reads against a small reference
  fasta of V3-V4 amplicons and reports per-reference relative abundance.
inputs:
  reads_dir:        str (required)  remote dir with paired _R1/_R2.fastq.gz
  reference_fasta:  str (required)  remote path to reference .fasta
  out_subpath:      str (required)  remote workdir-relative output dir
  n_threads:        int (optional, default 16)
outputs:
  abundance_table:  TSV (sample × reference relative abundance)
  per_sample_json:  JSON (counts + alignment rate per sample)
  fastp_reports:    one .json per sample
  sam_files:        one .sam per sample (kept for inspection)
env: praxis-microbiome-kraken (remote — has fastp + bowtie2 + python)
status: ready
stage: execution
domain: amplicon
host_env: praxis-microbiome-dada2-r
---

# amplicon_minimal_real

## Purpose
Demonstrate the **real** end-to-end loop ("real case retrieval → real LLM design → real binary execution → real abundance numbers cited in real report"). Substitutes for `amplicon_dada2_qiime` when QIIME2/SILVA aren't installed (e.g., bioconda solver hell + Docker Hub blocked).

This is **not** a replacement for the full DADA2 pipeline — it skips chimera detection, ASV inference, and proper taxonomy assignment. It exists for the demo loop and for sanity testing where a small reference set is acceptable.

## Sanity baseline (synthetic 5-genus mock)
Reference: `tests/baselines/16s_mock/references.fasta` + `tests/baselines/16s_mock/sample{01,02}_gut_R{1,2}.fastq.gz`.
- Pass: 100% bowtie2 alignment rate; 5/5 input genera recovered; relative abundance within ±10% of truth.
- Real verified result (2026-04-30 on zkyd@10.102.106.53): 5/5 recovered; max abundance error 0.022.

## Usage
```bash
python -m skills.workflows.amplicon_minimal_real.run \
    --reads-dir tests/baselines/16s_mock \
    --reference-fasta tests/baselines/16s_mock/references.fasta \
    --out-subpath runs/real-demo-001/abundance_out
```

## 输出契约

```json
{
  "skill_id": "amplicon_minimal_real",
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
