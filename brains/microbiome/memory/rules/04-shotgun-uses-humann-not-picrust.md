---
rule_id: 04-shotgun-uses-humann-not-picrust
rule_type: case_distilled
applies_to: {microbiome_task: [functional, multiomics], sequencing_type: [shotgun_short, shotgun_long]}
confidence: high
evidence_cases: [microbiome-004-humann-functional]
schema_version: 2
---

# Rule 04: Shotgun functional profiling uses HUMAnN3, not PICRUSt2

## Statement
For shotgun metagenomic functional profiling, use HUMAnN3 (which actually reads gene-level abundances). PICRUSt2 is a 16S-derived prediction tool — using it on shotgun data discards the actual functional information present in the reads.

## Why
HUMAnN3 (Beghini et al. 2021, 10.7554/eLife.65088) maps reads to ChocoPhlAn (per-species pangenome) + UniRef90, then aggregates to MetaCyc pathways. PICRUSt2 predicts function from 16S taxonomy by reference genome lookup — it can never call genes the actual sample contains but the closest reference genome doesn't. On shotgun data, real KO/pathway abundances are >5x more accurate than predictions.

## How to apply
- Reviewer gate `MICROBIOME_REVIEW_PICRUST_FOR_SHOTGUN`: trigger when `data_source=shotgun` AND `pipeline.tools` contains `picrust2`.
- Skill `humann_functional/run.py` refuses 16S input with clear error.
- For 16S-only datasets, PICRUSt2 IS appropriate — but always note it is a prediction.

## Evidence
- microbiome-004: explicit anti-pattern — "PICRUSt2 当 shotgun 替代" listed in failure modes.

## Anti-patterns
- ❌ PICRUSt2 on shotgun reads
- ❌ HUMAnN3 on 16S reads (will fail)
- ❌ Reporting pathway abundances without ChocoPhlAn / UniRef version

## Implementation pointer
`skills/workflows/humann_functional/run.py`
