---
name: mag_assembly_real
description: |
  REAL minimal MAG-assembly pipeline using MEGAHIT v1.2.9 (static binary from
  GitHub release — bypasses bioconda's tensorflow/grpc/c-ares conflict that
  blocks the canonical mag_assembly_pipeline). Performs:
    1. fastp QC (already in praxis-microbiome-kraken)
    2. MEGAHIT de novo assembly → contigs.fa
    3. simple-bin: bowtie2 map reads back → length+coverage filter → "bins"
    4. report contig count, total assembly length, N50, n_bins

  Not a substitute for the canonical pipeline (no MetaBAT2 ensemble + DAS_Tool,
  no CheckM2 quality, no GTDB-tk taxonomy). Exists for the demo loop closure.
inputs:
  reads_dir:        str (required)
  out_subpath:      str (required)
  min_contig_len:   int (default 500)
  min_coverage:     float (default 1.0)
  n_threads:        int (default 16)
outputs:
  contigs:          contigs.fa
  contig_stats:     JSON (n, total_length, N50, GC%)
  bins:             list of FA files passing length+coverage filter
  bin_stats:        TSV
env: praxis-microbiome-kraken (remote — fastp + bowtie2; MEGAHIT path injected)
status: ready
stage: execution
domain: mag
host_env: praxis-microbiome-checkm2
---

# mag_assembly_real

## Purpose
Demonstrate REAL de novo metagenome assembly + simple binning loop without depending on the canonical MAG stack (MetaBAT2 / CONCOCT / DAS_Tool / CheckM2 / GTDB-tk all blocked by bioconda conflicts on this remote).

## Sanity baseline (mock community)
Reference: synthetic fastqs in `tests/baselines/16s_mock/` (5-genus mock).
- Pass: ≥1 contig assembled, total length within 50% of expected (~2.3 kb sum of 5 input refs each ~460bp).

## Usage
```bash
python -m skills.workflows.mag_assembly_real.run \
    --reads-dir tests/baselines/16s_mock \
    --out-subpath runs/mag-real-001/out
```

## 输出契约

```json
{
  "skill_id": "mag_assembly_real",
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
