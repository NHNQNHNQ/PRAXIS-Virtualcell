---
rule_id: _default_bootstrap
schema_version: 1
rule_type: bootstrap
applies_to:
  sample_types: [any]
confidence: medium
last_updated: 2026-04-29
---

# Cold-start cryoEM workflow checklist

When the case library has no good match for the user's `(sample_type, resolution_target)`, fall back to this generic recipe.

## Acquisition
- [ ] Apoferritin facility calibration within last 30 days (rule 01)
- [ ] K3 (or equivalent) detector with super-resolution mode
- [ ] Pixel size + magnification calibrated against known apoferritin map
- [ ] 50 e⁻/Å² total dose / 40–50 frames / dose-weighted MotionCor2

## Pre-processing
- [ ] Motion correct + CTF estimate (`motion_correct_ctf`)
- [ ] Pre-screen movies for corruption (~1–2% expected fail)
- [ ] CTF CC > 0.05 cutoff; astigmatism < 200 Å

## Picking
- [ ] ≥ 2 pickers (Topaz + crYOLO + blob), pairwise IoU > 0.7 (rule 11)
- [ ] 2D classify → drop junk classes; junk fraction < 50% to proceed

## 3D
- [ ] Symmetry imposed for known-symmetric samples (rule 01)
- [ ] If FSC under-shoots claim or local map blurring: explore heterogeneity (rule 05)
- [ ] CTF refine + Bayesian polishing for sub-3 Å targets (rule 02)

## Diagnostics
- [ ] cryoEF + 3DFSC + angular distribution post-refinement (rule 08)
- [ ] Local resolution map alongside global FSC

## Model building
- [ ] AF prediction → dock_in_map → ISOLDE flexfit (rule 10)
- [ ] OR ModelAngelo → Phenix real_space_refine + Coot (rule 06)
- [ ] Sequence FASTA REQUIRED for ModelAngelo

## Validation
- [ ] MolProbity / Q-score / EMRinger / Ramachandran (rule 07)
- [ ] All thresholds met before publishing claims

## Reporting
- [ ] FSC reported at gold-standard 0.143
- [ ] Validation table + issues report (red/yellow/green)
- [ ] reproduce.sh capturing software versions + GPU h
- [ ] Confidence label: `cold_start` (this rule was used because no specific case matched)

## Cross-PRAXIS hooks (consider proposing)
- → PRAXIS-Protein: experimental_structure_for_binder
- → PRAXIS-Dock: experimental_receptor_for_docking
- ← PRAXIS-MD: heterogeneity_state_explanation (if K_3d > 1)
- ← PRAXIS-Protein: af_model_as_building_prior
