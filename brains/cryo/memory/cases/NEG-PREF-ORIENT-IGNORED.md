---
case_id: NEG-PREF-ORIENT-IGNORED
schema_version: 1
case_polarity: negative
sample_type: any
target_pdb: null
target_emdb: null
molecular_weight_kda: 480
symmetry_group: C3
resolution_target: "3-4"
resolution_achieved_a: 3.0
detector_type: K3
detergent_or_lipid: none
method_choice: [single_fsc_curve_only]
tools: [cryoSPARC v4]
status: anti_pattern
provenance:
  source_type: methodology_anchor
  doi: "10.1038/nmeth.4347"
  citation: "Tan YZ, et al. Addressing preferred specimen orientation in single-particle cryo-EM through tilting. Nat Methods 2017 (the canonical paper documenting the failure pattern this NEG- case describes)"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
anti_rule_triggered: 1
veto_reason: "post-refinement angular distribution / cryoEF / 3DFSC not reported; FSC=3.0 Å publishable claim hides 5+ Å worst-direction map"
related_positive_cases: [cryo-006-preferred-orientation]
tags: [NEG, anti_pattern, preferred_orientation, false_high_resolution, cryoEF_omitted, 3DFSC_omitted]
---

# NEG-PREF-ORIENT-IGNORED — false-confident FSC without preferred-orientation diagnostics

## Background (failure pattern, NOT a recommendation)
A 480 kDa C3 trimer (e.g. HA / spike) is reconstructed to "FSC = 3.0 Å" by the gold-standard 0.143 cutoff. The map is published, the model is built. Six months later, a re-analysis with cryoEF + 3DFSC reveals the worst-direction local resolution is 5.2 Å — large secondary-structure features in that direction were not reliably resolvable. The original "3.0 Å" claim was a global FSC artifact.

## What was actually done (the wrong path)
1. Standard pipeline (motion → CTF → pick → 2D class → 3D refine).
2. FSC at 0.143 = 3.0 Å reported.
3. Map deposited; model built.
4. **Skipped** post-refinement angular distribution histogram, cryoEF, and 3DFSC.

## ★ Why this is forbidden
- The single global FSC is computed over the entire Fourier shell. With anisotropic angular sampling (preferred orientation), the well-sampled directions dominate; poorly-sampled directions are averaged in but their contribution is small.
- cryoEF (Naydenova & Russo 2017, Nat Methods) puts a number on this anisotropy: efficiency factor ∈ [0, 1]; < 0.7 = bad, < 0.5 = severe. Reporting an FSC without cryoEF is reporting a number whose meaning is partly hidden.

## ★ Anti-rule mapping
**anti-rule 1**: any pipeline that ships final claims without cryoEF + angular distribution + 3DFSC is automatically vetoed by the Reviewer.

## Mitigation (rule 08-cryoef-threshold-pref-orient)
- ALWAYS run `preferred_orientation_diag` post-refinement.
- cryoEF < 0.7 → tier-1 mitigation (surfactant / graphene-oxide grid / UltrAuFoil).
- cryoEF < 0.5 → tier-2 (tilted dataset acquisition); software fix is insufficient — re-collect.
