---
rule_id: 06-unite-for-fungi
rule_type: case_distilled
applies_to: {microbiome_task: [amplicon_its], sequencing_type: [ITS], sample_type: ALL}
confidence: high
evidence_cases: [microbiome-006-its-fungal]
schema_version: 2
---

# Rule 06: Use UNITE database (not SILVA) for fungal ITS analysis

## Statement
For fungal ITS amplicon analysis, use the **UNITE** database (currently v10.0). SILVA is bacterial/archaeal-focused and lacks comprehensive fungal coverage; using SILVA on ITS data will mis-assign or fail to assign most fungal taxa.

## Why
SILVA is a curated rRNA reference database optimized for prokaryotic 16S/18S regions. Fungal phylogeny requires the ITS region, with reference sequences curated by mycologists in UNITE (Nilsson et al. 2019, 10.1186/s40168-020-00818-9 references this). UNITE includes species hypothesis (SH) clustering specifically designed for fungal taxonomic ambiguity at species level.

## How to apply
- Reviewer gate `MICROBIOME_REVIEW_SILVA_FOR_FUNGI`: trigger when `marker=its OR task=amplicon_its` AND `reference_db ~= /^SILVA/`.
- Skill `its_fungal_pipeline/run.py` defaults to UNITE 10.0.
- Use ITSx or ITSxpress to extract ITS1 / ITS2 region before classifier.
- FUNGuild for functional guild assignment after taxonomy.

## Evidence
- microbiome-006: explicit anti-pattern — "SILVA for fungi" listed in failure modes.

## Anti-patterns
- ❌ SILVA classifier on ITS reads
- ❌ Skipping ITS region extraction (full amplicon vs ITS only)
- ❌ Assigning fungal species without acknowledging copy-number variability (10–100× across taxa)
- ❌ Ignoring low fungal biomass (<1% reads in stool) → no negative control

## Implementation pointer
`skills/workflows/its_fungal_pipeline/run.py` (P1 stub)
