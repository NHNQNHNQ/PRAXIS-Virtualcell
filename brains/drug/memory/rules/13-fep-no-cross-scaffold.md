---
rule_id: 13-fep-no-cross-scaffold
rule_type: case_distilled
applies_to: {target_class: ALL, modality: [small_mol_inhibitor, allosteric, covalent], project_phase: lead_opt}
confidence: high
evidence_cases: [drug-009-fep-relative-affinity]
schema_version: 2
---

# Rule 13: FEP perturbations stay within a single Murcko scaffold

## Statement
FEP (Free Energy Perturbation) is a relative ΔΔG calculation. It is reliable for small perturbations within a chemical series — typically R-group changes, ring substitution, or single-atom replacements. **It is NOT reliable for**:
- Cross-scaffold perturbations (e.g., quinazoline → pyrimidine swap)
- Macrocycle vs linear perturbations
- Charge-state changes (neutral → cation/anion)
- Stereochemistry inversion at a binding-pocket-facing center

Configuration: ≥ 12 lambda windows, ≥ 5 ns production per window, hysteresis < 0.5 kcal/mol on cycle closure (else re-run with longer sampling).

## Why
FEP convergence depends on overlap between λ windows; large perturbations increase the variance + sampling time required. Cross-scaffold attempts routinely produce 4-6 kcal/mol errors which is larger than the lead-opt signal we're trying to measure. The drug-009 FEP case explicitly fails on macrocycle and on slow-degree-of-freedom (P-loop) sampling.

## How to apply
- Skill `fep_relative_affinity` (P2 stub at v0; full at v0.5 via OpenFE) compares Murcko scaffold of `from` and `to` SMILES; rejects with `error: cross_scaffold_perturbation` when scaffolds differ.
- Reviewer at design stage blocks any FEP perturbation entry whose Murcko fingerprints differ.
- Cross-agent envelope `fep_relative_affinity` to PRAXIS-MD also enforces this scaffold-match check.
