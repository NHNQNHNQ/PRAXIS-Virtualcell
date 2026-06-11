---
name: mutation_panel_screen
description: |
  Mutation panel docking for resistance-prone targets (kinase / gtpase / protease / polymerase).
  Implements rule 09 — mandatory in lead-opt phase.
inputs: {lead_smiles: str, wt_pdb: str, mut_list: list[str]}
outputs: {per_mutation_dock_score: dict[mut → float], delta_score_vs_wt: dict[mut → float], resistance_vulnerable_flag: bool}
env: praxis-drug-vina
status: skeleton
stage: execution
domain: lead_opt
---

# mutation_panel_screen — SKELETON (P1)

Stub in v0.1. T315I gatekeeper (drug-010 imatinib SAR) is the reference case.
At v0.5: PyRosetta cartesian_ddg(antibody env) → re-dock → score difference vs WT.
Required for kinase / gtpase / protease / polymerase lead-opt phase.

## 输出契约

```json
{
  "skill_id": "mutation_panel_screen",
  "n_compounds": 0,
  "best_score": 0.0,
  "compound_csv": "",
  "diagnostics": {
    "brain": "drug",
    "archetype": "drug"
  }
}
```
