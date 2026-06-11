---
case_id: NEG-K1-ON-HETEROGENEOUS
schema_version: 1
case_polarity: negative
sample_type: heterogeneous_complex
target_pdb: null
target_emdb: null
molecular_weight_kda: 500
symmetry_group: C1
resolution_target: "3-4"
resolution_achieved_a: 3.5
detector_type: K3
detergent_or_lipid: nanodisc
method_choice: [k1_single_class_refine]
tools: [RELION 5]
status: anti_pattern
provenance:
  source_type: methodology_anchor
  doi: "10.1038/s41592-020-01049-4"
  citation: "Zhong ED, et al. CryoDRGN: reconstruction of heterogeneous cryo-EM structures using neural networks. Nat Methods 2021 — explicitly motivated by this anti-pattern"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
anti_rule_triggered: 10
veto_reason: "K=1 single-class refinement on a heterogeneous sample → FSC sharp but map is averaged-out smear; functional state mixing hidden"
related_positive_cases: [cryo-004-heterogeneity-3dclass]
tags: [NEG, anti_pattern, k1_on_heterogeneous, fsc_misleading, smeared_map]
---

# NEG-K1-ON-HETEROGENEOUS — K=1 refine on a multi-state sample

## Background (failure pattern)
A sample with 60% pre-translocation / 25% intermediate / 15% post-translocation states is refined with K=1 (single class). The FSC is sharp because the alignment converges, but the map is the ensemble average — functional regions appear smeared, side-chain density is poor exactly where the conformational change happens.

## What was actually done (the wrong path)
1. K=1 ab-initio + 3D refine.
2. FSC = 3.5 Å, looks publishable.
3. Map shows blurry density at the inter-subunit interface.
4. Reviewer flags this as suspicious; re-running with K=3 reveals 3 distinct functional states, each at 3.0–3.5 Å sharper than the K=1 average.

## ★ Why this is forbidden
- Heterogeneity is the rule, not the exception. Almost every interesting biological sample mixes states.
- K=1 forces the alignment to find a single "pose" per particle; the resulting FSC reflects pose convergence, not biological homogeneity.
- The cure (K ∈ [3, 5] discrete + 3DVA + cryoDRGN triangulation) is cheap relative to publishing a smeared map.

## ★ Anti-rule mapping
**anti-rule 10**: sample_type = heterogeneous_complex AND `classify.k_3d == 1` → Reviewer veto (`CRYO_REVIEW_HETEROGENEITY_IGNORED`).

## Mitigation (rule 05-heterogeneity-three-tools-triangulate)
- Always run discrete 3D class with K ∈ [3, 5] first.
- Cross-check with cryoSPARC 3DVA (linear PCs).
- For continuous landscapes, add cryoDRGN as the third tool.
- Trust only when ≥ 2 tools agree on the dominant axis of motion.
