---
rule_id: 03-ligand-prep-stereo-protonation-tautomer
rule_type: case_distilled
applies_to: {target_class: ALL, modality: ALL, project_phase: [hit_id, hit_to_lead, lead_opt]}
confidence: high
evidence_cases: [drug-001-vina-egfr-screening, drug-003-pocket2mol-sbdd]
schema_version: 2
---

# Rule 03: Ligand prep must enumerate stereo / protonation / tautomer

## Statement
Every ligand entering docking must be expanded into:
1. Stereoisomers (RDKit `EnumerateStereoisomers`)
2. Protonation states at pH 7.4 (Dimorphite-DL)
3. Tautomers (RDKit `TautomerEnumerator`)
4. 3D conformers (ETKDGv3, ≥ 1 conformer per stereoisomer/tautomer)

Then convert to PDBQT (Meeko + OpenBabel).

## Why
~30% of drug-like compounds have multiple physiologically relevant protonation states at pH 7.4 (imidazole, carboxylates, amines, guanidiniums). ~50% of true binders have alternative tautomers (lactam/lactim, amide/iminol). Single-state docking misses the binding state. Wrong tautomer = wrong H-bond pattern = wrong pose ranking.

## How to apply
- Skill `ligand_prep` (P0) does all four steps; returns count of variants per input compound.
- Reviewer gate at design stage blocks if `compound_library[].source = literature_lead` AND no ligand_prep skill in `computational_pipeline`.
- For computationally-cheap virtual screens (10k+ compounds), per-compound enumeration ceiling: 16 variants (top-N by MMFF energy).
