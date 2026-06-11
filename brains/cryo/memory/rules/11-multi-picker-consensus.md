---
rule_id: 11-multi-picker-consensus
schema_version: 1
rule_type: case_distilled
applies_to:
  sample_types: [any]
evidence_cases:
  - cryo-009-particle-picking
confidence: high
last_updated: 2026-04-29
---

## 规则
**Particle picking MUST use ≥ 2 pickers and reach pairwise IoU ≥ 0.7 before downstream classification.**

Different DL pickers (Topaz, crYOLO, blob) miss different particles. Single-picker pipelines silently bias the dataset toward the picker's training distribution.

## Decision tree
1. Initial blob picker (cryoSPARC) → 2D classify → identify junk fraction.
2. Train Topaz on 200–500 manual picks → re-pick all micrographs.
3. Run crYOLO with general model → fine-tune if junk class fraction > 30%.
4. Compute pairwise IoU between picker outputs at the particle box level.
5. Keep coordinates where ≥ 2 pickers agree (IoU ≥ 0.7 within a single particle box).
6. 2D classify the consensus picks; junk fraction must be < 50% before 3D refine.

## Excluded actions
- Template-based picking with a high-resolution template (model bias).
- Skipping 2D classification after picking (no junk audit).
- Using small-particle (< 100 kDa) DL pickers without manual review (CNNs underperform here).

## Reviewer block code
`CRYO_REVIEW_SINGLE_PICKER`
