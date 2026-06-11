---
name: fep_relative_affinity
description: |
  Relative free energy perturbation (ΔΔG) within a Murcko scaffold. Implements rule 13
  — refuses cross-scaffold perturbations.
inputs: {lead_pdb: str, perturbations: list[{from_smiles, to_smiles}], n_lambda: int (≥12), n_reps: int}
outputs: {ddg_kcal: dict, hysteresis: float, cycle_closure_kcal: float}
env: praxis-drug-openfe (OpenFE + OpenMM, GPU env, conflicts with vina-py)
status: skeleton
stage: execution
domain: fep
host_env: praxis-drug-openfe
---

# fep_relative_affinity — SKELETON (P2, GPU env conflict)

Stub in v0.1. drug-009 is the reference (≥12 lambda, ≥5 ns/window, hysteresis < 0.5 kcal/mol).
At v0.5: OpenFE + OpenMM in `praxis-drug-openfe` env.
v0 alternative: dispatch via cross-PRAXIS envelope (`fep_relative_affinity` request_type) to PRAXIS-MD,
which has the production FEP setup.

Murcko scaffold check is enforced at the API entry point — perturbation pairs with different scaffolds
return `error: cross_scaffold_perturbation` (rule-13).

## 输出契约

```json
{
  "skill_id": "fep_relative_affinity",
  "n_compounds": 0,
  "best_score": 0.0,
  "compound_csv": "",
  "diagnostics": {
    "brain": "drug",
    "archetype": "drug"
  }
}
```
