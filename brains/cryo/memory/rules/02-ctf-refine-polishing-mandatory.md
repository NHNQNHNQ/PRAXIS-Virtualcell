---
rule_id: 02-ctf-refine-polishing-mandatory
schema_version: 1
rule_type: case_distilled
applies_to:
  resolution_targets: ["<2", "2-3"]
evidence_cases:
  - cryo-001-apoferritin-reference
  - cryo-005-modelangelo-buildmodel
confidence: high
last_updated: 2026-04-29
---

## 规则
**For sub-3 Å reconstructions, per-particle CTF refinement AND Bayesian polishing are mandatory.**

These steps recover information lost to (a) defocus inhomogeneity within the dataset and (b) beam-induced motion that pre-frame motion correction cannot resolve. Skipping either of them caps resolution at ~2.5 Å regardless of particle count.

## When to apply
- Final-stage refinement of a target ≤ 3.0 Å.
- Apoferritin / hard-sample / facility-calibration runs.

## When to skip
- Initial low-resolution screens (CTF refine adds wallclock without value at > 4 Å).
- Sub-particle counts (< 50k particles → both steps overfit).

## Reviewer block code
`CRYO_REVIEW_NO_POLISHING_AT_HIGH_RES` (soft warning, not a hard block).
