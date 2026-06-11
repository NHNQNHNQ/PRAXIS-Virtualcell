---
rule_id: 11-fbdd-physical-validation
rule_type: case_distilled
applies_to: {target_class: ALL, modality: fragment, project_phase: hit_id}
confidence: high
evidence_cases: [drug-006-fbdd-vemurafenib]
schema_version: 2
---

# Rule 11: Fragment hits require physical validation

## Statement
A fragment is not a "hit" until it has been physically validated by ≥ 1 of:
- NMR (ligand-detected: STD, WaterLOGSY; or protein-detected: ¹⁵N HSQC chemical shift perturbation)
- SPR / BLI (KD measurement)
- X-ray co-crystal (gold standard)
- ITC (thermodynamic confirmation)

Computational docking alone never qualifies a fragment as a hit.

## Why
Fragment libraries (~1000 cmpd, MW < 300, "rule of 3": HBA ≤ 3, HBD ≤ 3, logP ≤ 3) screen at high concentrations (0.5-1 mM) where docking has high false-positive rates. Vemurafenib's 7-azaindole fragment was identified by NMR + SPR + X-ray in parallel, not by docking. Without physical validation, fragment growing/linking starts from a wrong scaffold.

## How to apply
- Reviewer at design stage requires `validation_plan.wet_lab_assays_recommended` to include at least one of (`NMR`, `SPR`, `X-ray`, `ITC`) when modality = fragment.
- Reporting stage flags fragment candidates without physical-validation reference as `confidence_label: low` regardless of docking score.
