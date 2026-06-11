---
name: aizynth_retrosynthesis
description: |
  Retrosynthesis filter via AiZynthFinder. Returns ≤ N-step routes with commercial start materials.
  Implements rule 10 (synthesis filter triple-check: SAscore + AiZynth + commercial avail).
inputs:
  target_smiles: str
  max_depth: int (default 6)
  stocks: str (default 'eMolecules+Enamine_BB+Sigma' — actual stocks file from aizynth config)
outputs:
  routes:
    - n_steps: int
      score: float
      reactions: list[str]
      commercial_start_materials: list[str]
      tree_pickle: str (path)
  best_route_n_steps: int
  any_under_6_steps: bool
env: praxis-drug-aizynth (separate conda env; aizynthfinder + tensorflow + RDKit)
status: ready
stage: execution|reporting
domain: synthesis
---

# aizynth_retrosynthesis

Runs AiZynthFinder against a target SMILES + commercial stock files. Returns ranked routes with step count and starting materials. The `commercial_start_materials` list is the PRAXIS-Drug filter signal — at least 80% of starts must be in eMolecules / Enamine BB / Sigma.

If `aizynthfinder` is not installed, falls back to **SAscore-only** mode and explicitly tags the result `mode: sascore_only` so the Reviewer downgrades the candidate's confidence to `low`.

## Why
Generative models routinely produce molecules with 8+ step syntheses or rare heterocycles. Three-way filter (SAscore + AiZynth + commercial) is the first practical gate (rule 10).

## CLI
```bash
python -m skills.workflows.aizynth_retrosynthesis.run \
    --smiles "Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc1nccc(-c2cccnc2)n1" \
    --max-depth 6
```

## 输出契约

```json
{
  "skill_id": "aizynth_retrosynthesis",
  "n_compounds": 0,
  "best_score": 0.0,
  "compound_csv": "",
  "diagnostics": {
    "brain": "drug",
    "archetype": "drug"
  }
}
```
