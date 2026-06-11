---
rule_id: 12-soft-edge-mask-mandatory
schema_version: 1
rule_type: case_distilled
applies_to:
  sample_types: [supercomplex, ribonucleoprotein, large_complex]
evidence_cases:
  - cryo-010-focused-refinement
confidence: high
last_updated: 2026-04-29
---

## 规则
**Focused refinement masks MUST have a soft edge of ≥ 6 voxels.**

Sharp-edge masks introduce FSC artifacts at the mask boundary that mimic high-resolution information. The soft edge tapers the mask gradient over ≥ 6 voxels, suppressing this artifact without sacrificing the focused signal.

## Additional focused-refinement rules
- Use signal subtraction only when the ROI is < 1/3 of the consensus map (otherwise the gain is marginal).
- One ROI per focused refinement run; do NOT mask multiple regions in a single run.
- Composite map outputs MUST document which region came from which refinement (focused vs full-rigid vs multibody).
- Particle count check: focused refinement uses ALL particles, but only the ROI signal — needs the same count as full-map refinement.

## Excluded actions
- Mask edge < 6 voxels.
- Masking a region smaller than its known atomic interactions (cuts off contacts).
- Reporting composite maps without indicating which parts were stitched.

## Reviewer block code
`CRYO_REVIEW_FOCUSED_HARD_MASK`
