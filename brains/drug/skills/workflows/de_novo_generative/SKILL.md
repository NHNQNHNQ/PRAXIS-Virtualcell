---
name: de_novo_generative
description: |
  De novo molecular generation via REINVENT4 (or MolGPT / GFlowNet). Multi-objective reward
  with reality-check filters (rule-06). Each generated compound MUST pass docking + ADMET +
  retrosynthesis triple filter before being eligible as a hit candidate.
inputs:
  target_uniprot: str
  target_pdb: str
  reward_objectives: list[{name, weight, target_value}]
  n_steps: int
  scaffold_constraint: str (Murcko SMILES, optional)
outputs:
  generated_smiles: list[str]
  reward_breakdown_per_compound: dict
env: praxis-drug-reinvent (GPU; v0 stub)
status: skeleton
stage: design
domain: generative
---

# de_novo_generative — SKELETON (P1, GPU env required)

This skill is a stub in v0.1. Its `run.py` raises `NotImplementedError` with a clear message about how to provision the GPU env and download REINVENT4 weights.

Behaviour when invoked: orchestrator's Execution Agent will see `dry_run` results and the Reviewer will downgrade the candidate's confidence to `low`.

To implement at v0.5: separate conda env (`praxis-drug-reinvent`), REINVENT4 ≥ 4.0, GPU recommended. Output SMILES MUST then go through `vina_gnina_dock + admet_multi + aizynth_retrosynthesis` (rule-06 reality check).

## 输出契约

```json
{
  "skill_id": "de_novo_generative",
  "n_compounds": 0,
  "best_score": 0.0,
  "compound_csv": "",
  "diagnostics": {
    "brain": "drug",
    "archetype": "drug"
  }
}
```
