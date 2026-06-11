---
rule_id: 03-multi-binner-consensus
rule_type: case_distilled
applies_to: {microbiome_task: [mag_assembly, hi_c], sample_type: ALL}
confidence: high
evidence_cases: [microbiome-003-mag-assembly, microbiome-010-meta-hi-c]
schema_version: 2
---

# Rule 03: Multi-binner + DAS_Tool consensus for MAG recovery

## Statement
Metagenome-assembled genome (MAG) recovery MUST run ≥2 binners (MetaBAT2, CONCOCT, MaxBin2) and reconcile via DAS_Tool consensus. CheckM2 ML-based completeness/contamination assessment, then GTDB-tk taxonomy on dereplicated MAG set.

## Why
Single-binner pipelines miss 20–40% of recoverable MAGs because each binning algorithm uses different signals (tetranucleotide frequency vs differential coverage). DAS_Tool intersection is more conservative; union with quality filter is the modern standard (Almeida et al. 2021, 10.1186/s40168-020-00990-y).

## How to apply
- Reviewer gate `MICROBIOME_REVIEW_SINGLE_BINNER`: trigger when `task=mag_assembly` AND `design_plan.computational_pipeline.binners.length < 2`.
- Skill `mag_assembly_pipeline/run.py` runs MetaBAT2 + CONCOCT + MaxBin2 + DAS_Tool by default.
- QC thresholds: completeness ≥ 50%, contamination ≤ 5% for medium-quality; ≥ 90% / ≤ 5% for high-quality.

## Evidence
- microbiome-003: explicit decision chain — DAS_Tool over single binner.
- microbiome-010: Hi-C augments standard binning (not replaces) — same multi-binner consensus principle.

## Anti-patterns
- ❌ MetaBAT2 only
- ❌ Skipping DAS_Tool consensus
- ❌ Reporting MAGs without CheckM2 quality scores
- ❌ GTDB-tk classification before dereplication (dRep)

## Implementation pointer
`skills/workflows/mag_assembly_pipeline/run.py`
