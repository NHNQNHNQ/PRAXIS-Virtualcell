---
name: pocket2mol_sbdd
description: Structure-based de novo generation via Pocket2Mol / TargetDiff / DiffSBDD. Generated molecules MUST be re-docked + ADMET + retrosynthesis filtered (rule-06).
inputs: {pocket_pdb: str, atom_map: dict, n_samples: int}
outputs: {generated_sdf: str, validity_pass_rate: float}
env: praxis-drug-p2m (GPU; v0 stub)
status: skeleton
stage: design
domain: generative
---

# pocket2mol_sbdd — SKELETON (P1, GPU env required)

Stub in v0.1. To implement: separate conda env, Pocket2Mol pretrained weights from the original repo (https://github.com/pengxingang/Pocket2Mol), GPU recommended. Output SDF must be re-docked + ADMET + retrosynth (rule-06).

## 输出契约

```json
{
  "skill_id": "pocket2mol_sbdd",
  "n_compounds": 0,
  "best_score": 0.0,
  "compound_csv": "",
  "diagnostics": {
    "brain": "drug",
    "archetype": "drug"
  }
}
```
