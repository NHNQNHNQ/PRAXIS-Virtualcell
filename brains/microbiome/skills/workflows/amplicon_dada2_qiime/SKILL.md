---
name: amplicon_dada2_qiime
description: |
  16S/ITS amplicon DADA2 pipeline via QIIME2 on the remote analysis server.
  Steps: cutadapt primer removal → DADA2 (filterAndTrim, learnErrors, dada,
  mergePairs, removeBimeraDenovo) → classify-sklearn against SILVA 138.1 (16S)
  or UNITE 10.0 (ITS) → mafft+fasttree phylogeny. Outputs: ASV table, taxonomy
  TSV, rooted Newick tree, per-sample QC summary.
inputs:
  reads_dir:        str (required)  remote dir with paired .fastq.gz
  marker:           str (required)  16s | its
  primer_fwd:       str (optional, default 341F for V3-V4 / ITS1F for ITS)
  primer_rev:       str (optional, default 805R for V3-V4 / ITS2 for ITS)
  reference_db:     str (optional, default SILVA138.1 for 16s, UNITE10.0 for its)
  trunc_len_fwd:    int (optional, default 240 for 16s 250bp)
  trunc_len_rev:    int (optional, default 200 for 16s 250bp)
  n_threads:        int (optional, default 16)
  out_subpath:      str (required)  remote workdir-relative output dir
outputs:
  asv_table:        TSV (feature × sample, integer counts)
  taxonomy:         TSV (asv_id → kingdom; phylum; class; order; family; genus; species)
  phylogeny:        Newick (rooted)
  qc_summary:       JSON  (read counts pre/post-filter, chimera %, DB version)
env: qiime2 (remote)
status: ready
stage: execution
domain: amplicon
---

# amplicon_dada2_qiime

## Purpose
Convert raw 16S or ITS amplicon reads into an ASV-level abundance table + taxonomy + phylogenetic tree, using the modern (2026) QIIME2 + DADA2 best-practice pipeline. Implements rule-01 (ASV over OTU) and rule-06 (UNITE for fungi).

## Implementation
- Remote execution via `tools/remote_exec.run_remote()`; conda env `praxis-microbiome-qiime2`.
- Steps shelled to QIIME2 CLI:
  1. `qiime tools import` (paired-end demux)
  2. `qiime cutadapt trim-paired` (primer removal)
  3. `qiime dada2 denoise-paired` (per-run error model + chimera removal)
  4. `qiime feature-classifier classify-sklearn` (vs SILVA 138.1 / UNITE 10.0)
  5. `qiime phylogeny align-to-tree-mafft-fasttree`

## Sanity baseline (HMP mock community)
HMP V3-V5 mock community (SRR033103 subset → 100 reads per known taxon for ~20 known species):
- Pass: ≥95% of input genera recovered in the ASV taxonomy table.
- Fail: <90% genera recovered, or any ASV classified outside expected phyla.

## Usage
```bash
# Real remote run
python -m skills.workflows.amplicon_dada2_qiime.run \
    --reads-dir /path/on/remote/raw_fastq \
    --marker 16s --reference-db SILVA138.1 \
    --out-subpath runs/task-001/dada2_out

# Local simulate (no remote required)
python -m skills.workflows.amplicon_dada2_qiime.run --simulate --marker 16s
```

## 输出契约

```json
{
  "skill_id": "amplicon_dada2_qiime",
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
