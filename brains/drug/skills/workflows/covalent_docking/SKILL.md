---
name: covalent_docking
description: |
  Covalent docking with reactive Cys constraint (Vina + restraints, or AutoDock-CrankPep, or Schrödinger CovDock).
  Returns kinact/Ki estimate (NOT IC50). Implements rule 04 modality routing.
inputs: {receptor_pdbqt: str, reactive_residue: str, ligand_with_warhead: str}
outputs: {covalent_pose_pdbqt: str, kinact_Ki_estimate: float, warhead_reactivity_tier: str}
env: praxis-drug-vina
status: skeleton
stage: execution
domain: docking
---

# covalent_docking — SKELETON (P1)

Stub in v0.1. To implement at v0.5: Vina with covalent restraints (Cys SG distance to warhead C < 2 Å),
or invoke `gnina --covalent` if the gnina build supports it. Sotorasib (drug-008) is the reference
case for warhead reactivity tier (acrylamide → mild; chloroacetamide → mid; α-haloketone → high).

## 输出契约

```json
{
  "skill_id": "covalent_docking",
  "n_compounds": 0,
  "best_score": 0.0,
  "compound_csv": "",
  "diagnostics": {
    "brain": "drug",
    "archetype": "drug"
  }
}
```
