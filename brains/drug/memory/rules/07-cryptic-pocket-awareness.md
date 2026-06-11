---
rule_id: 07-cryptic-pocket-awareness
rule_type: case_distilled
applies_to: {target_class: ALL, modality: [small_mol_inhibitor, allosteric, covalent], project_phase: [hit_id, hit_to_lead]}
confidence: high
evidence_cases: [drug-006-fbdd-vemurafenib, drug-008-sotorasib-kras-covalent]
schema_version: 2
---

# Rule 07: Cryptic pocket awareness — apo + holo + MD

## Statement
Do not screen against an apo crystal structure alone. For every target, attempt all three of:
1. Apo (if available) — gives baseline
2. Holo (with co-crystal ligand) — gives pre-shaped pocket
3. MD-derived ensemble (50-100 ns) — exposes cryptic pockets

When apo and holo conformations differ significantly (Cα RMSD > 1.5 Å in pocket region), use MD ensemble + ensemble docking.

## Why
KRAS G12C was "undruggable" for 30 years because the switch-II cryptic pocket only opens transiently. Sotorasib's binding mode requires the holo or MD-revealed pocket. B-Raf DFG-out (vemurafenib mode) is similar — the pocket only exists in the inactive conformation. Apo-only docking missed both for years.

## How to apply
- Skill `pocket_detection` (TODO: P2 stub) runs FPocket / CryptoSite on apo + MD frames.
- For kinase + gtpase + bromodomain targets, Reviewer requires `validation_plan.computational_pipeline` to include MD pre-screen OR explicit acknowledgement that holo structure suffices.
- Cross-agent envelope: `predict_apo_holo_with_cryptic_pocket_search` request to PRAXIS-Protein.
