---
name: particle_pick_consensus
description: |
  Multi-picker consensus particle picking. Runs Topaz + crYOLO + cryoSPARC blob,
  then keeps coordinates where ≥ 2 of 3 pickers agree (IoU > 0.7 inside a single
  particle box). Sanity invariant: ≥ 2 pickers must report > 0 picks AND
  pairwise IoU between any two pickers must exceed 0.7. Implements rule
  11-multi-picker-consensus.
inputs:
  micrographs_dir: str (required)
  particle_box_size_px: int (required)
  pickers: list (default [topaz,crYOLO,blob])
  topaz_threshold: float (default 0.0)
  cryolo_threshold: float (default 0.3)
  blob_min_diameter_a: float (default 100)
  blob_max_diameter_a: float (default 200)
outputs:
  coords_star_path: str
  per_picker_counts: dict
  pairwise_iou: dict
  consensus_count: int
  junk_class_fraction_estimate: float
env: praxis-cryo-base
status: ready_with_simulate
stage: execution
domain: pre_processing
case_evidence: [cryo-009-particle-picking]
rule_evidence: [11-multi-picker-consensus]
status: not-deployed
deploy_blocker: staging .53 缺 relion/cryosparc/motioncor2 等 cryo 工具;待补 cryo env
---

# particle_pick_consensus

The single-picker trap: each DL picker (Topaz, crYOLO, blob) misses different
particles. Running ≥ 2 + checking IoU against each other catches mode failure.

## Real-binary mode
Requires at least 2 of: `topaz`, `cryolo` (cryolo_predict.py), or cryoSPARC blob
picker. Each runs independently; coordinates are merged via box-IoU > 0.7.

## --simulate mode
Generates 3 synthetic picker outputs with overlap deterministically chosen to
exceed the IoU threshold (test sanity-passes the invariant).

## 输出契约

```json
{
  "skill_id": "particle_pick_consensus",
  "n_particles": 0,
  "resolution_a": 0.0,
  "map_path": "",
  "diagnostics": {
    "brain": "cryo",
    "archetype": "cryo"
  }
}
```
