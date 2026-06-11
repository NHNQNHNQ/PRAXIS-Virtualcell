---
name: motion_correct_ctf
description: |
  Movie motion correction (MotionCor2 / RELION own implementation) followed by
  CTF estimation (CTFFIND4). The first step of any single-particle cryoEM
  pipeline. Sanity invariant: output micrograph count == input movie count
  (after corruption screening) and CTF cross-correlation > 0.05.
inputs:
  movies_dir: str (required)         # directory containing .tif/.eer/.mrcs movies
  pixel_size_a: float (required)     # Å/pixel
  voltage_kv: int (default 300)
  cs_mm: float (default 2.7)
  amplitude_contrast: float (default 0.1)
  total_dose_e_per_a2: float (default 50)
  dose_per_frame_e_per_a2: float (default 1.0)
  patches: list (default [5,5])
  motion_method: str (motioncor2|relion_own; default motioncor2)
  ctf_method: str (ctffind4|gctf; default ctffind4)
outputs:
  micrographs_dir: str
  ctf_star_path: str
  n_movies_input: int
  n_micrographs_output: int
  median_ctf_cc: float
  fraction_corrupted: float
  astigmatism_max_a: float
env: praxis-cryo-base
status: ready_with_simulate
stage: execution
domain: pre_processing
case_evidence: [cryo-001-apoferritin-reference]
rule_evidence: [02-ctf-refine-polishing-mandatory]
status: not-deployed
deploy_blocker: staging .53 缺 relion/cryosparc/motioncor2 等 cryo 工具;待补 cryo env
---

# motion_correct_ctf

Movie motion correction + CTF estimation. Standard cryoEM pre-processing.

## Real-binary mode
Requires `motioncor2` (or RELION's own motion correction) **and** `ctffind4`.
Both binaries discovered through `config/tools.yaml`. Movies in `--movies-dir`
are processed with patch-based motion correction; per-frame dose weighting
uses `total_dose / dose_per_frame`.

## --simulate mode
Activates when either binary is missing. Produces:
- 1 fake micrograph filename per movie file in the input directory
- a CTF table with deterministic-but-realistic CC values (centered around 0.08)
- 0% corruption flagged

This lets sanity tests on a dev machine without GPU/binaries still verify the
output schema and downstream skill compatibility.

## Sanity invariants checked at exit
- `n_micrographs_output == n_movies_input - n_corrupted` (always)
- `median_ctf_cc > 0.05` (warn if below)
- `astigmatism_max_a < 200` (warn if above)

## 输出契约

```json
{
  "skill_id": "motion_correct_ctf",
  "n_particles": 0,
  "resolution_a": 0.0,
  "map_path": "",
  "diagnostics": {
    "brain": "cryo",
    "archetype": "cryo"
  }
}
```
