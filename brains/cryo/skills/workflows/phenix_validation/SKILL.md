---
name: phenix_validation
description: |
  Run Phenix validation_cryoem (MolProbity score / Q-score / EMRinger / Ramachandran).
  Sanity invariant: MolProbity < 2.0 + Q-score > 0.5 + EMRinger ≥ 1.0; missing
  any metric is a Reviewer-blocking error (CRYO_REVIEW_NO_MOLPROBITY).
inputs:
  model_cif: str (required)
  map_mrc: str (required)
  resolution_a: float (required)
outputs:
  molprobity_score: float
  ramachandran_outliers_pct: float
  rotamer_outliers_pct: float
  clash_score: float
  qscore: float
  emringer_score: float
  passes_thresholds: bool
env: praxis-cryo-phenix
status: ready_with_simulate
stage: execution
domain: validation
case_evidence: [cryo-005-modelangelo-buildmodel]
rule_evidence: [07-validation-suite-mandatory]
status: not-deployed
deploy_blocker: staging .53 缺 relion/cryosparc/motioncor2 等 cryo 工具;待补 cryo env
---
# phenix_validation
Every cryoEM model REQUIRES the full validation suite. Reporting only one metric is the #1 source of overstated quality claims.

## 输出契约

```json
{
  "skill_id": "phenix_validation",
  "n_particles": 0,
  "resolution_a": 0.0,
  "map_path": "",
  "diagnostics": {
    "brain": "cryo",
    "archetype": "cryo"
  }
}
```
