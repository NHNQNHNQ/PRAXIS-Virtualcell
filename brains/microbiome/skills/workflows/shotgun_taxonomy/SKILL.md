---
name: shotgun_taxonomy
description: |
  Shotgun metagenomic taxonomy via dual classifiers — Kraken2+Bracken (k-mer)
  AND MetaPhlAn4 (marker-gene). Enforces rule-02 (single classifier rejected).
  Steps: fastp QC → bowtie2 host removal (hg38) → Kraken2 classify → Bracken
  abundance → MetaPhlAn4 → consensus species table (intersection = high
  confidence; union = candidate).
inputs:
  reads_dir:        str (required)  remote dir with paired .fastq.gz
  host_genome:      str (default hg38)  bowtie2 index for host removal
  kraken_db:        str (default kraken2_standard)  Kraken2 DB path
  metaphlan_db:     str (default vJun23_CHOCOPhlAnSGB_202403)
  bracken_readlen:  int (default 150)
  classifier_confidence: float (default 0.1)
  n_threads:        int (default 16)
  out_subpath:      str (required)
outputs:
  kraken2_bracken:    TSV (species × sample relative abundance, k-mer source)
  metaphlan4:         TSV (clade × sample relative abundance, marker-gene source)
  consensus_species:  TSV (high_confidence | candidate based on dual agreement)
  host_read_fraction: JSON (per-sample host removal stats)
env: kraken (remote)
status: ready
stage: execution
domain: shotgun
host_env: praxis-microbiome-kraken
---

# shotgun_taxonomy

## Purpose
Provide species-level taxonomic abundance from shotgun metagenomic reads via dual classifier consensus, implementing rule-02. Single-classifier mode is refused.

## Implementation
- Remote conda env `praxis-microbiome-kraken` with kraken2, bracken, metaphlan, fastp, bowtie2, samtools.
- Pipeline shell:
  1. fastp paired-end quality + adapter trim
  2. bowtie2 → host removal (hg38)
  3. Kraken2 + Bracken (re-estimate abundance)
  4. MetaPhlAn4 (marker-gene)
  5. Consensus join: species present in both → `high_confidence`; in only one → `candidate`

## Sanity baseline (gut sample dominance)
Reference dataset: human gut shotgun (e.g., HMP gut sample SRS019968).
- Pass: phylum-level Firmicutes 0.4–0.7, Bacteroidetes 0.2–0.5, Proteobacteria <0.15 (consistent across both classifiers).
- Fail: any classifier alone gives Proteobacteria >0.3 (likely contamination signal needs blank).

## Usage
```bash
python -m skills.workflows.shotgun_taxonomy.run \
    --reads-dir /home/zkyd/data2/mzy/PRAXIS-Microbiome/runs/task-002/raw_fastq \
    --out-subpath runs/task-002/shotgun_out
```

## 输出契约

```json
{
  "skill_id": "shotgun_taxonomy",
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
