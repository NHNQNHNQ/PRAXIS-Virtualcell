---
name: af_cryoem_hybrid
description: |
  AF + cryoEM hybrid model building. Predict structure with AlphaFold3 / ESMFold,
  dock into the cryoEM map (Phenix dock_in_map), then flexfit (ChimeraX +
  ISOLDE). Sanity invariant: every per-residue output is labeled `from_AF` /
  `from_map_remodel` / `disordered_low_plddt_low_density`.
inputs:
  map_mrc: str (required)
  af_model_cif: str (required)
  resolution_a: float (required)
  af_plddt_per_residue: list (optional)
outputs:
  hybrid_cif_path: str
  per_residue_source: list  # [{chain, resnum, source, plddt, map_local_res_a}]
  agreement_count: int
  remodel_count: int
  disordered_count: int
env: praxis-cryo-base
status: ready_with_simulate
stage: execution
domain: model_building
case_evidence: [cryo-008-af-cryoem-hybrid]
rule_evidence: [10-af-cryoem-hybrid-flexfit]
status: not-deployed
deploy_blocker: staging .53 缺 relion/cryosparc/motioncor2 等 cryo 工具;待补 cryo env
---
# af_cryoem_hybrid
AF prediction → dock_in_map → flexfit. AF-vs-map difference is *biology*, not noise; per-residue source labeling makes that explicit.

## 输出契约

```json
{
  "skill_id": "af_cryoem_hybrid",
  "n_particles": 0,
  "resolution_a": 0.0,
  "map_path": "",
  "diagnostics": {
    "brain": "cryo",
    "archetype": "cryo"
  }
}
```
