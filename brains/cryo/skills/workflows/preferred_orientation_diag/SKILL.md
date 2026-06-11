---
name: preferred_orientation_diag
description: |
  Diagnose preferred orientation: angular distribution histogram, cryoEF
  efficiency factor, 3DFSC directional FSC. Below cryoEF=0.7 is bad, below 0.5
  is severe. Returns mitigation recommendations (tilt collection, surfactant,
  graphene oxide, GraFix). Sanity invariant: cryoEF reported AND mitigations
  enumerated when cryoEF < 0.7.
inputs:
  particles_star: str (required)
  refinement_map: str (required)
outputs:
  cryoef: float
  worst_3dfsc_direction: list  # [angle1, angle2]
  worst_to_best_fsc_ratio: float
  angular_distribution_histogram: list  # 18-bin angular distribution
  severity: str  # ok | warn | severe
  mitigations: list
env: praxis-cryo-base
status: ready_with_simulate
stage: execution
domain: diagnostics
case_evidence: [cryo-006-preferred-orientation]
rule_evidence: [08-cryoef-threshold-pref-orient]
status: not-deployed
deploy_blocker: staging .53 缺 relion/cryosparc/motioncor2 等 cryo 工具;待补 cryo env
---
# preferred_orientation_diag
Without this diagnostic, "FSC = 3.0 Å" can hide regions at 5+ Å. Always run post-refinement.

## 输出契约

```json
{
  "skill_id": "preferred_orientation_diag",
  "n_particles": 0,
  "resolution_a": 0.0,
  "map_path": "",
  "diagnostics": {
    "brain": "cryo",
    "archetype": "cryo"
  }
}
```
