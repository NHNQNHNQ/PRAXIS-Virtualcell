---
rule_id: 09-strain-when-needed
rule_type: case_distilled
applies_to: {microbiome_task: [strain, multiomics], sequencing_type: [shotgun_short, shotgun_long]}
confidence: high
evidence_cases: [microbiome-009-strain-tracking]
schema_version: 2
---

# Rule 09: Strain-level resolution when biology requires it (FMT, pathogen, transmission)

## Statement
For studies of fecal microbiota transplant (FMT), pathogen tracking, mother-infant transmission, or strain replacement, species-level taxonomy is insufficient. Use strain-resolved methods: StrainPhlAn4 (marker-gene), inStrain (SNV + coverage), midas2 (pangenome), PanPhlAn3 (presence/absence). Coverage threshold ≥5× per strain for reliable calls.

## Why
A single species can host coexisting strains differing by thousands of SNVs and entire gene clusters. FMT engraftment, antibiotic-induced strain replacement, and vertical transmission are invisible at species level (Schmidt et al. 2022, 10.1038/s41587-021-01070-8). Strain analysis requires shotgun (not 16S) and adequate depth.

## How to apply
- Skill `strain_tracking/run.py` (P2 stub) coordinates StrainPhlAn4 + inStrain.
- Coverage QC: <5× per strain marked unreliable.
- Multi-strain coexistence: explicitly model rather than collapsing to consensus.
- Reference strain bias: novel strains will look like reference; orthogonal call needed (pangenome).

## Evidence
- microbiome-009: explicit anti-pattern — "Species level when strain matters".

## Anti-patterns
- ❌ 16S for FMT engraftment claims
- ❌ Single strain caller (StrainPhlAn alone misses non-marker SNVs)
- ❌ Reporting strain calls below 5× coverage without uncertainty
- ❌ Assuming reference strain represents the sample strain

## Implementation pointer
`skills/workflows/strain_tracking/run.py` (P2 stub)
