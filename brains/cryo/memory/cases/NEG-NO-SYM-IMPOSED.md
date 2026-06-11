---
case_id: NEG-NO-SYM-IMPOSED
schema_version: 1
case_polarity: negative
sample_type: soluble_oligomer
target_pdb: null
target_emdb: null
molecular_weight_kda: 480
symmetry_group: O
resolution_target: "<2"
resolution_achieved_a: 3.5
detector_type: K3
detergent_or_lipid: none
method_choice: [c1_refine_high_sym_sample]
tools: [RELION 5, cryoSPARC v4]
status: anti_pattern
provenance:
  source_type: methodology_anchor
  doi: "10.1016/j.jsb.2020.107545"
  citation: "Wu M, Lander GC, Herzik MA. Sub-2 Angstrom resolution structure determination using single-particle cryo-EM at 200 keV. J Struct Biol 2020 — sets the apoferritin O-symmetry calibration baseline this NEG- case violates"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
anti_rule_triggered: 2
veto_reason: "octahedral apoferritin run with C1 symmetry → effective particle count divided by 24, FSC stalls at 3.5 Å instead of 1.5–2.0 Å"
related_positive_cases: [cryo-001-apoferritin-reference]
tags: [NEG, anti_pattern, symmetry_imposition_skipped, particle_count_wasted, sub_2A_failure]
---

# NEG-NO-SYM-IMPOSED — refined apoferritin in C1 instead of O

## Background (failure pattern)
Apoferritin (24-mer, octahedral 432 symmetry) is the cryoEM facility-calibration sample. With O symmetry imposed, ~50k particles routinely reach 1.5–2.0 Å. Without it, ~50k particles → ~3.5 Å (the asymmetric-unit count is 24× smaller).

## What was actually done (the wrong path)
1. Standard pipeline as cryo-001-apoferritin-reference.
2. **Forgot** to set `--sym O` in the 3D auto-refine; ran C1.
3. Final FSC = 3.5 Å. Author concluded "detector / grid is bad."
4. Re-ran with O symmetry → 1.8 Å. The detector / grid were fine.

## ★ Why this is forbidden
- Symmetry imposition is the cheapest signal multiplier in cryoEM. Skipping it on a known-symmetric sample is throwing away a 24× particle equivalent.
- Worse, the C1 result misled diagnosis: blame fell on detector/grid hardware before the trivial fix was tried.

## ★ Anti-rule mapping
**anti-rule 2**: high-symmetry sample (Cn≥3, Dn, T, O, I) without `refinement.symmetry_imposed` matching the group → Reviewer veto.

## Mitigation (rule 01-symmetry-imposition)
- Identify symmetry from biology + 2D-class rotational averaging.
- Always set `refinement.symmetry_imposed` for high-symmetry samples.
- If symmetry uncertain: run C1 ab-initio first, then verify against symmetrized reconstruction.
