---
case_id: NEG-FOCUSED-HARD-MASK
schema_version: 1
case_polarity: negative
sample_type: large_complex
target_pdb: null
target_emdb: null
molecular_weight_kda: 600
symmetry_group: C1
resolution_target: "3-4"
resolution_achieved_a: null
detector_type: K3
detergent_or_lipid: none
method_choice: [focused_refine_sharp_edge_mask]
tools: [RELION focused refinement]
status: anti_pattern
provenance:
  source_type: methodology_anchor
  doi: "10.1016/j.jsb.2018.08.007"
  citation: "Bai XC, et al. focused refinement methodology — explicitly recommends soft-edge mask of ≥ 6 voxels"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
anti_rule_triggered: 8
veto_reason: "focused refinement uses sharp-edge (binary) mask with no soft border → FSC artifact at the mask boundary mimics false high-resolution information"
related_positive_cases: [cryo-010-focused-refinement]
tags: [NEG, anti_pattern, sharp_edge_mask, fsc_artifact, focused_refine_misuse]
---

# NEG-FOCUSED-HARD-MASK — sharp-edge focused mask, false-high FSC

## Background (failure pattern)
Focused refinement requires a soft-edge mask. With a binary (sharp-edge) mask, the FSC computed inside the mask is biased upward by the mask-boundary discontinuity (a step function in real space → high-frequency content in Fourier space). The masked-region FSC looks fantastic, but the underlying density is no better than the consensus map.

## What was actually done (the wrong path)
1. Created a binary mask around the ROI (e.g. small subunit) with `relion_mask_create --inimask threshold` and zero soft edge.
2. Ran focused refinement; reported masked FSC = 2.5 Å.
3. Map showed no actual side-chain improvement over the 3.2 Å consensus.
4. Re-ran with soft edge of 6 voxels: masked FSC honestly 2.9 Å, real density gain 0.3 Å.

## ★ Why this is forbidden
- Sharp-edge masks introduce a known FSC artifact at the boundary frequency.
- The artifact inflates the masked FSC without improving the actual map.
- Soft edges of ≥ 6 voxels (Cosine taper or Gaussian) suppress this artifact.

## ★ Anti-rule mapping
**anti-rule 8**: focused refinement with `mask_soft_edge_voxel < 6` → Reviewer veto (skill-level FAIL: `FOCUSED_MASK_HARD_EDGE`).

## Mitigation (rule 12-soft-edge-mask-mandatory)
- Always specify `--soft-edge 6` (or more) in `relion_mask_create`.
- Verify masked FSC against full-map FSC for the same region; gain must be physically plausible (≤ ~1 Å, not 2+).
