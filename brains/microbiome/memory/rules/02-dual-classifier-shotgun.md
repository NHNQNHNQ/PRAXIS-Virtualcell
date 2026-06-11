---
rule_id: 02-dual-classifier-shotgun
rule_type: case_distilled
applies_to: {microbiome_task: [shotgun_taxonomy, multiomics, strain], sample_type: ALL}
confidence: high
evidence_cases: [microbiome-002-shotgun-kraken, microbiome-007-host-microbe-multiomics, microbiome-009-strain-tracking]
schema_version: 2
---

# Rule 02: Dual classifier (k-mer + marker-gene) for shotgun taxonomy

## Statement
Shotgun metagenomic taxonomic profiling MUST use at least two complementary classifiers — one k-mer based (Kraken2 + Bracken) and one marker-gene based (MetaPhlAn4) — and report consensus. Single-classifier results have 5–15% false positive species calls (Lu & Salzberg 2020, 10.1186/s13059-019-1891-0).

## Why
K-mer and marker-gene methods make different errors. Kraken2 over-calls related species (E. coli vs Shigella ~95% identity confused). MetaPhlAn4 misses species absent from its marker catalog. Intersection = high-confidence calls; union = candidate set requiring confirmation.

## How to apply
- Reviewer gate `MICROBIOME_REVIEW_SINGLE_CLASSIFIER`: trigger when `task=shotgun_taxonomy` AND `design_plan.computational_pipeline.classifier_count < 2`.
- Skill `shotgun_taxonomy/run.py` enforces dual-classifier execution by default.
- Output `consensus_species.tsv` flags species present in ≥2 classifiers as `high_confidence`.

## Evidence
- microbiome-002: explicit anti-pattern — "Single classifier shotgun" listed in failure modes.
- microbiome-009: strain-level work likewise relies on multi-method (StrainPhlAn + inStrain + midas2).

## Anti-patterns
- ❌ Kraken2 only (without MetaPhlAn4 cross-check)
- ❌ MetaPhlAn4 only (misses non-marker species)
- ❌ Centrifuge only (high false positive on closely-related species)

## Implementation pointer
`skills/workflows/shotgun_taxonomy/run.py`
