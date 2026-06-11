---
rule_id: 01-asv-over-otu
rule_type: case_distilled
applies_to: {microbiome_task: [amplicon_16s, amplicon_its, amplicon_18s], sample_type: ALL}
confidence: high
evidence_cases: [microbiome-001-16s-dada2, microbiome-006-its-fungal]
schema_version: 2
---

# Rule 01: Use ASVs (DADA2) over OTU clustering for amplicon data

## Statement
For 16S/ITS/18S amplicon analysis, default to **ASV** (Amplicon Sequence Variant) inference via DADA2 (or deblur). Do NOT use OTU clustering (vsearch / usearch / mothur cluster) when DADA2 is available.

## Why
ASVs offer single-nucleotide resolution and exact reproducibility across studies — OTU clusters at 97% identity merge biologically distinct strains and lose the ability to integrate with public ASV databases. Callahan et al. 2016 (Nat Methods, 10.1038/nmeth.3869, the DADA2 paper) showed ASVs recover known mock community composition more accurately than OTU clustering at every taxonomic level.

## How to apply
- Reviewer gate `MICROBIOME_REVIEW_OTU_WHEN_DADA2`: trigger when `task ∈ {amplicon_16s, amplicon_its}` AND pipeline tools include `vsearch_cluster | usearch | mothur_cluster`.
- Skill `amplicon_dada2_qiime` is the canonical entry point.
- Required steps inside DADA2: per-run error model (`learnErrors`), bimera removal (`removeBimeraDenovo`), paired-end merge.

## Evidence
- microbiome-001: explicit decision in case body — "OTU clustering when DADA2 available" listed as anti-pattern.
- microbiome-006: ITS pipeline also uses DADA2 (modified parameters) over OTU clustering.

## Anti-patterns
- ❌ vsearch --cluster_fast at 97%
- ❌ usearch -cluster_otus
- ❌ mothur cluster.split

## Implementation pointer
`skills/workflows/amplicon_dada2_qiime/run.py`
