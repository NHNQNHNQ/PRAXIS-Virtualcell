---
rule_id: 11-negative-control-low-biomass
rule_type: case_distilled
applies_to: {microbiome_task: ALL, sample_type: [human_oral, human_skin, low_biomass_tissue, water_freshwater, mock_community]}
confidence: high
evidence_cases: [microbiome-002-shotgun-kraken, microbiome-006-its-fungal, microbiome-007-host-microbe-multiomics]
schema_version: 2
---

# Rule 11: Negative controls mandatory for low-biomass samples

## Statement
Any project with low-biomass samples (skin, oral, lung, low-density tissue, environmental water) MUST include DNA extraction blanks AND reagent blanks, processed identically to samples. Apply decontam-style filtering (R `decontam` prevalence/frequency, or manual blacklist) before any downstream analysis.

## Why
DNA extraction kits and PCR reagents contain background bacterial DNA at low but detectable levels — often dominated by Burkholderia, Pseudomonas, or alphaproteobacteria from kit manufacturing. In a high-biomass sample (gut, soil) this is invisible; in low biomass it can dominate the apparent community. Salter et al. 2014 first quantified this; the "kitome" is now widely recognized.

## How to apply
- Reviewer gate `MICROBIOME_REVIEW_NO_NEG_CONTROL_LOW_BIOMASS`: trigger when `sample_type ∈ {oral, skin, low_biomass_*}` OR `biomass_estimate=low` AND `negative_control_plan.negative_control_samples` is empty.
- Skill outputs include `negative_control_diagnostics` block with contaminant count.
- Decontam method preference: prevalence (binary present/absent) for low-N studies; frequency (correlation with DNA quantity) when qPCR data available.

## Evidence
- microbiome-002: explicit failure mode — "Reagent contamination" listed.
- microbiome-006: ITS fungal in stool has <1% reads = effectively low biomass for fungi → blanks needed.
- microbiome-007: multiomics dataset must apply decontam before integration.

## Anti-patterns
- ❌ Running low-biomass samples without blanks
- ❌ "We didn't have time for blanks" (not acceptable)
- ❌ Filtering only by abundance threshold (misses low-abundance contaminants)
- ❌ Ignoring qPCR DNA quantification for frequency-based decontam

## Implementation pointer
QC step inside every P0 skill `run.py`; `tests/test_reviewer_low_biomass_block.py` enforces.
