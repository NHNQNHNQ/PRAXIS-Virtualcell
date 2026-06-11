---
name: multibody_refine
description: |
  RELION multibody refinement: split a flexible complex into ≥ 2 rigid bodies
  with independent alignment. Improves per-body resolution by 0.3-1.0 Å.
  Sanity invariant: each per-body FSC must improve ≥ 0.3 Å vs full-rigid map.
inputs:
  consensus_map: str (required)
  particles_star: str (required)
  body_masks: list (required)        # ≥ 2 mask paths
  body_names: list (optional)
outputs:
  full_rigid_resolution_a: float
  per_body: list                     # [{name, mask, resolution_a, improvement_a}]
  composite_map_path: str
env: praxis-cryo-base
status: ready_with_simulate
stage: execution
domain: refinement
case_evidence: [cryo-002-membrane-protein-gpcr, cryo-003-supercomplex-ribosome]
rule_evidence: [04-multibody-for-supercomplex]
status: not-deployed
deploy_blocker: staging .53 缺 relion/cryosparc/motioncor2 等 cryo 工具;待补 cryo env
---
# multibody_refine
Inter-body motion is the #1 limit of full-rigid refinement on big complexes. Multibody decouples it.

## 输出契约

```json
{
  "skill_id": "multibody_refine",
  "n_particles": 0,
  "resolution_a": 0.0,
  "map_path": "",
  "diagnostics": {
    "brain": "cryo",
    "archetype": "cryo"
  }
}
```
