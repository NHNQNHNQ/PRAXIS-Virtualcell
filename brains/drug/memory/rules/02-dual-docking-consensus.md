---
rule_id: 02-dual-docking-consensus
rule_type: case_distilled
applies_to: {target_class: ALL, modality: [small_mol_inhibitor, allosteric, fragment], project_phase: [hit_id, hit_to_lead]}
confidence: high
evidence_cases: [drug-001-vina-egfr-screening, drug-003-pocket2mol-sbdd]
schema_version: 2
---

# Rule 02: Dual docking with consensus rank

## Statement
Single docking method is insufficient for hit-id virtual screens. Always run AutoDock Vina (geometry + force field) **and** GNINA (CNN re-scoring) **and** rank by consensus (sum of normalized ranks).

## Why
GNINA's CNN provides 5-10% enrichment improvement over Vina alone in DUD-E benchmarks. Vina's force field gets the geometry; GNINA's deep model gets the soft pose-quality signal.

## How to apply
- For small_mol_inhibitor / allosteric / fragment screens: skill `vina_gnina_dock` runs both, returns `consensus_rank`.
- Compute enrichment factor at 1% (EF1%); EF1% < 5 means library prep or receptor prep is broken — fix before trusting hits.
- Spike-in ≥ 5 known actives in every screen as enrichment validator.

## Edge cases
- **Covalent**: use `covalent_docking` skill, not `vina_gnina_dock` (rule 04).
- **PROTAC**: ternary complex sampling, not single-protein docking (rule 12).
