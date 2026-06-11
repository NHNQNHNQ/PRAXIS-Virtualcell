---
name: meta_hi_c_real
description: |
  REAL Hi-C contact-graph binning (bin3C-style) without the bin3C package.
  Aligns Hi-C paired reads against assembly contigs (bwa-mem), extracts
  trans-contig contacts, builds weighted contact graph, greedy modularity
  merging. Implements rule-10 (Hi-C augments standard binning).
inputs:
  contigs_fa:        str (required)  assembly contigs (e.g. from mag_assembly_real)
  hi_c_reads_dir:    str (required)  paired Hi-C fastq dir
  out_subpath:       str (required)
  min_contacts:      int (default 1)  min trans-contig contacts to merge bins
  n_threads:         int (default 8)
outputs:
  contact_graph:     TSV (contig_a, contig_b, n_contacts)
  bin_assignments:   TSV (contig, bin_id)
  summary_json:      JSON
env: praxis-microbiome-kraken (remote — bwa + python)
status: ready
stage: execution
domain: hi_c
---

# meta_hi_c_real

## Purpose
Real Hi-C augmented binning without the bin3C Python package or HiC-Pro. Demonstrates the principle of rule-10: trans-contig contacts from Hi-C reveal which contigs lived in the same cell.

## Sanity baseline
With synthetic Hi-C reads where pairs are designed to cross between known reference contigs (5 references → 5 expected bins after merging linked pairs), expect bin count ≤ # references. Verifies the contact extraction + graph clustering pipeline runs end-to-end.

## 输出契约

```json
{
  "skill_id": "meta_hi_c_real",
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
