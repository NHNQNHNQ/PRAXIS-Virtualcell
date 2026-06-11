---
name: model_angelo_build
description: |
  Run ModelAngelo on a sharpened map + sequence FASTA to produce an atomic
  model with per-residue confidence. Sanity invariant: sequence FASTA is
  REQUIRED (poly-Ala output is unusable downstream); per-residue confidence
  must be reported.
inputs:
  map_mrc: str (required)
  sequences_fasta: str (required, must be non-empty)
  resolution_a: float (required)
  output_cif: str (optional; default model_angelo.cif)
outputs:
  model_cif_path: str
  per_residue_confidence: list   # [{chain, resnum, conf}]
  high_conf_residues: int
  medium_conf_residues: int
  low_conf_residues: int
  unassigned_residues: int
env: praxis-cryo-modelangelo
status: ready_with_simulate
stage: execution
domain: model_building
case_evidence: [cryo-005-modelangelo-buildmodel]
rule_evidence: [06-modelangelo-firstpass-not-final]
status: not-deployed
deploy_blocker: staging .53 缺 relion/cryosparc/motioncor2 等 cryo 工具;待补 cryo env
---
# model_angelo_build
ModelAngelo gives a first-pass atomic model in hours instead of days. Always followed by Phenix real_space_refine + manual fix on low-confidence regions.

## 输出契约

```json
{
  "skill_id": "model_angelo_build",
  "n_particles": 0,
  "resolution_a": 0.0,
  "map_path": "",
  "diagnostics": {
    "brain": "cryo",
    "archetype": "cryo"
  }
}
```
