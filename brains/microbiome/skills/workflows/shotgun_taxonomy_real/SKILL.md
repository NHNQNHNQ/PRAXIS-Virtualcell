---
name: shotgun_taxonomy_real
description: |
  REAL shotgun metagenomic taxonomy via dual-aligner consensus (bowtie2 + bwa
  if available) against a reference fasta. Substitutes for the canonical
  `shotgun_taxonomy` skill (Kraken2+Bracken+MetaPhlAn4) when the standard
  Kraken2 DB (~50GB) and MetaPhlAn4 DB are not yet downloaded — but still
  enforces rule-02 (dual-classifier consensus) by running TWO independent
  aligners and reporting their agreement.

  Pipeline: fastp QC → bowtie2 → bwa-mem (if installed; else skip with WARN)
  → Python SAM parser per aligner → consensus join (species present in
  ≥2 aligners marked high_confidence; in only one marked candidate).
inputs:
  reads_dir:        str (required)  remote dir with paired _R1/_R2.fastq.gz
  reference_fasta:  str (required)  remote path to reference .fasta
  out_subpath:      str (required)  remote workdir-relative output dir
  n_threads:        int (default 8)
outputs:
  consensus_table:  TSV (sample × reference + consensus class)
  bowtie2_table:    TSV (per-aligner abundance)
  bwa_table:        TSV (per-aligner abundance, when bwa available)
  per_sample_json:  JSON
env: praxis-microbiome-kraken (remote — has fastp + bowtie2 + bwa + samtools)
status: ready
stage: execution
domain: shotgun
host_env: praxis-microbiome-kraken
---

# shotgun_taxonomy_real

## Purpose
Demonstrate the **real** dual-classifier consensus principle (rule-02) with what's actually installed on remote. Not a replacement for full Kraken2+MetaPhlAn4 — exists for the demo loop and as a fallback when DBs aren't downloaded.

## Sanity baseline (5-genus mock community)
Reference: `tests/baselines/16s_mock/references.fasta` + synthetic fastqs.
- Pass: ≥2 aligners agree on dominant taxa for both samples; ≥4/5 input genera marked high_confidence.

## Usage
```bash
python -m skills.workflows.shotgun_taxonomy_real.run \
    --reads-dir tests/baselines/16s_mock \
    --reference-fasta tests/baselines/16s_mock/references.fasta \
    --out-subpath runs/shotgun-real-001/out
```

## 输出契约

```json
{
  "skill_id": "shotgun_taxonomy_real",
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
