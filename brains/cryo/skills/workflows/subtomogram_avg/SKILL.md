---
name: subtomogram_avg
description: |
  cryoET tilt-series → tomogram (AreTomo) → subtomogram averaging (Warp + M
  or RELION 4 STA). Sanity invariants: dose-symmetric tilt scheme present,
  per-tilt CTF estimation enabled, missing-wedge-aware refinement on, ≥ 5
  tomograms in dataset.
inputs:
  tilt_series_dir: str (required)   # contains *.mrc + tilt_angles.csv + dose_per_tilt.csv
  pixel_size_a: float (required)
  tilt_scheme: str (default dose_symmetric)
  per_tilt_ctf: bool (default true)
  missing_wedge_aware: bool (default true)
  template_mrc: str (optional)
outputs:
  n_tomograms: int
  n_subtomograms: int
  sta_resolution_a: float
  missing_wedge_anisotropy: float
  template_bias_check: str
env: praxis-cryo-aretomo
status: ready_with_simulate
stage: execution
domain: cryoet
case_evidence: [cryo-007-cryoet-subtomogram]
rule_evidence: [09-cryoet-dose-sym-and-per-tilt-ctf]
status: not-deployed
deploy_blocker: staging .53 缺 relion/cryosparc/motioncor2 等 cryo 工具;待补 cryo env
---
# subtomogram_avg
Dose-symmetric scheme is mandatory; continuous tilt-down burns sample at the wrong place. Per-tilt CTF is mandatory; standard CTF assumes constant defocus.

## 输出契约

```json
{
  "skill_id": "subtomogram_avg",
  "n_particles": 0,
  "resolution_a": 0.0,
  "map_path": "",
  "diagnostics": {
    "brain": "cryo",
    "archetype": "cryo"
  }
}
```
