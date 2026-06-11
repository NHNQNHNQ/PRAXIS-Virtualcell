---
rule_id: 04-modality-aware-routing
rule_type: case_distilled
applies_to: {target_class: ALL, modality: ALL, project_phase: ALL}
confidence: high
evidence_cases: [drug-007-protac-dbet1, drug-008-sotorasib-kras-covalent]
schema_version: 2
---

# Rule 04: Modality-aware tool routing — first decision in design

## Statement
Identify modality at scoping stage. Each modality has its own pipeline; do NOT use small-molecule-inhibitor tools for covalent / PROTAC / allosteric / fragment work.

## Routing table

| modality              | docking skill            | scoring                         | extra constraints                                  |
|-----------------------|--------------------------|---------------------------------|----------------------------------------------------|
| `small_mol_inhibitor` | `vina_gnina_dock`        | IC50 / pIC50 (predicted)        | normal pipeline                                    |
| `covalent`            | `covalent_docking`       | kinact/Ki (NOT IC50)            | reactive Cys identified; warhead reactivity tier   |
| `protac`              | `protac_ternary`         | DC50 + cooperativity α          | warhead + linker + E3 ligand all 3 needed          |
| `molecular_glue`      | `protac_ternary` (relaxed)| DC50 + ternary stability       | similar to PROTAC but no covalent linker           |
| `allosteric`          | `vina_gnina_dock`+pocket | IC50, allosteric site validation| FPocket / CryptoSite for cryptic site             |
| `fragment`            | `vina_gnina_dock`        | LE > 0.3, fit-quality, NMR/SPR  | rule of 3; physical validation REQUIRED            |
| `peptide`             | (out of scope v0)        | —                               | —                                                  |

## Why
Covalent: IC50 is time-dependent for irreversible binders; selectivity comes from reversible recognition not warhead reactivity. Use kinact/Ki.
PROTAC: ternary geometry is everything; many PEG linkers fail because of cooperativity ≪ 1; cell penetration (MW 700-900) is bottleneck.
Fragment: ligand efficiency (LE) is the right metric; NMR/SPR/X-ray confirms binding above HTS noise.

## How to apply
- Reviewer gate at design stage blocks any `compound_library[].smiles` containing acrylamide / chloroacetamide / sulfonyl-fluoride / α-haloketone / Michael-acceptor-with-EWG (covalent warhead) when modality ≠ covalent.
- Reviewer blocks PROTAC pipeline missing `linker_smiles` or E3 ligand identifier.
- Reviewer blocks fragment phase claiming "hit" without physical-validation entry in `validation_plan.wet_lab_assays_recommended`.
