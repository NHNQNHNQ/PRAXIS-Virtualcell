---
name: 2d_3d_classify
description: |
  2D classification followed by 3D classification (RELION) or 3D ab-initio +
  heterogeneity (cryoSPARC). Drops junk 2D classes, then explores K=3-5
  conformational/compositional 3D classes. Sanity invariant: at least 1 stable
  class with FSC reaching the resolution claim, and reported `K` ∈ [2, 8].
inputs:
  particles_star: str (required)
  k_2d: int (default 50)
  k_3d: int (default 4)
  symmetry: str (default C1)
  backend: str (relion|cryosparc; default relion)
outputs:
  good_2d_class_count: int
  junk_2d_class_count: int
  retained_particle_count: int
  k_3d: int
  per_3d_class: list   # [{class_id, fraction, resolution_a, label}]
  best_class_id: int
  best_class_resolution_a: float
env: praxis-cryo-base
status: ready_with_simulate
stage: execution
domain: classification
case_evidence: [cryo-001-apoferritin-reference, cryo-004-heterogeneity-3dclass]
rule_evidence: [05-heterogeneity-three-tools-triangulate]
status: not-deployed
deploy_blocker: staging .53 缺 relion/cryosparc/motioncor2 等 cryo 工具;待补 cryo env
---
# 2d_3d_classify
2D classify (drop junk) → 3D classify (K=3-5). Heterogeneity is *expected*; running with K=1 and ignoring sub-state mixing yields a sharp FSC that hides a smeared map.

## 输出契约

```json
{
  "skill_id": "2d_3d_classify",
  "n_particles": 0,
  "resolution_a": 0.0,
  "map_path": "",
  "diagnostics": {
    "brain": "cryo",
    "archetype": "cryo"
  }
}
```
