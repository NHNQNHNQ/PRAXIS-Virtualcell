---
name: focused_refine
description: |
  Single-region focused refinement (RELION focused / cryoSPARC local). Mask
  + signal subtraction. Sanity invariant: ROI mask must have soft edge ≥ 6
  voxels, and masked-region FSC must exceed full-map FSC.
inputs:
  consensus_map: str (required)
  particles_star: str (required)
  roi_mask: str (required)
  mask_soft_edge_voxel: int (default 6)
  signal_subtract: bool (default true)
outputs:
  full_map_resolution_a: float
  roi_resolution_a: float
  improvement_a: float
  composite_map_path: str
env: praxis-cryo-base
status: ready_with_simulate
stage: execution
domain: refinement
case_evidence: [cryo-010-focused-refinement]
rule_evidence: [12-soft-edge-mask-mandatory]
status: not-deployed
deploy_blocker: staging .53 缺 relion/cryosparc/motioncor2 等 cryo 工具;待补 cryo env
---
# focused_refine
Focused = mask + signal subtract + only-ROI alignment. Soft edge < 6 voxels = sharp-edge artifacts.

## 输出契约

```json
{
  "skill_id": "focused_refine",
  "n_particles": 0,
  "resolution_a": 0.0,
  "map_path": "",
  "diagnostics": {
    "brain": "cryo",
    "archetype": "cryo"
  }
}
```
