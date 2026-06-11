---
name: protac_ternary
description: |
  PROTAC ternary complex modeling (target + PROTAC + E3 ligase). Returns ternary pose +
  cooperativity α. Implements rule 12 — PROTAC ≠ small-molecule inhibitor.
inputs: {warhead_smiles: str, e3_ligand_smiles: str, linker_smiles: str, target_pdb: str, e3_pdb: str}
outputs: {ternary_complex_pdb: str, cooperativity_alpha: float, hook_effect_warning: bool}
env: praxis-drug-rosetta (PRosettaC or relaxed Vina + custom)
status: skeleton
stage: execution
domain: modality
host_env: praxis-drug
---

# protac_ternary — SKELETON (P1)

Stub in v0.1. dBET1 (drug-007) is the reference: JQ1 + thalidomide-derivative + PEG linker.
Tracks DC50, Dmax, ternary stability, cell penetration (MW 700-900 = bottleneck).
At v0.5: PRosettaC (https://github.com/JKupp/PRosettaC) or custom Vina-relaxed protocol.

## 输出契约

```json
{
  "skill_id": "protac_ternary",
  "n_compounds": 0,
  "best_score": 0.0,
  "compound_csv": "",
  "diagnostics": {
    "brain": "drug",
    "archetype": "drug"
  }
}
```
