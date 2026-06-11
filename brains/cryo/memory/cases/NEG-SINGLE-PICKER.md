---
case_id: NEG-SINGLE-PICKER
schema_version: 1
case_polarity: negative
sample_type: any
target_pdb: null
target_emdb: null
molecular_weight_kda: 200
symmetry_group: C1
resolution_target: "3-4"
resolution_achieved_a: null
detector_type: K3
detergent_or_lipid: any
method_choice: [topaz_only]
tools: [Topaz 0.2.5]
status: anti_pattern
provenance:
  source_type: methodology_anchor
  doi: "10.1038/s41592-019-0575-8"
  citation: "Bepler T, et al. Positive-unlabeled CNNs for particle picking (Topaz). Nat Methods 2019 — explicitly recommends multi-picker consensus to mitigate single-CNN bias"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
anti_rule_triggered: 3
veto_reason: "single Topaz pick → 3D refine, no 2D class junk audit, no second picker for IoU consensus → biased dataset toward Topaz training distribution"
related_positive_cases: [cryo-009-particle-picking]
tags: [NEG, anti_pattern, single_picker, no_2d_audit, topaz_only, picker_bias]
---

# NEG-SINGLE-PICKER — Topaz alone, no 2D audit, biased dataset

## Background (failure pattern)
Topaz is excellent — but every CNN picker has a training-distribution bias. Particles that look unlike the training set are systematically under-picked. Running a single picker, skipping the 2D-classify junk audit, and proceeding straight to 3D refinement produces a reconstruction whose dataset is silently selected by the picker's idiosyncrasies.

## What was actually done (the wrong path)
1. Topaz general model → all-dataset pick.
2. Skipped 2D classification entirely ("CNN already filtered noise").
3. Direct 3D ab-initio + refine.
4. Map looked OK at 3.5 Å; downstream model building revealed an over-represented orientation cluster and an under-represented sub-state. Re-picking with Topaz + crYOLO + blob (consensus IoU > 0.7) recovered the missing population.

## ★ Why this is forbidden
- Single-picker pipelines have no internal consistency check; you cannot know which particles are *missing* from your dataset.
- Skipping 2D classify hides the junk fraction (a > 50% junk fraction is a re-train signal, not a "proceed anyway" signal).

## ★ Anti-rule mapping
**anti-rule 3**: < 2 pickers used OR pairwise IoU < 0.7 between any two pickers → Reviewer veto.

## Mitigation (rule 11-multi-picker-consensus)
- Always run ≥ 2 pickers (Topaz + crYOLO, Topaz + blob, etc.).
- Compute pairwise IoU at the particle-box level; require ≥ 0.7 to accept.
- 2D classify after picking; if junk fraction > 50% → retrain picker, do NOT proceed.
