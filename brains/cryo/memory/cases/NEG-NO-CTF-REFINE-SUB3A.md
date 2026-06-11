---
case_id: NEG-NO-CTF-REFINE-SUB3A
schema_version: 1
case_polarity: negative
sample_type: soluble_oligomer
target_pdb: null
target_emdb: null
molecular_weight_kda: 480
symmetry_group: O
resolution_target: "<2"
resolution_achieved_a: 2.5
detector_type: K3
detergent_or_lipid: none
method_choice: [no_ctf_refine_no_polishing]
tools: [RELION 5, cryoSPARC v4]
status: anti_pattern
provenance:
  source_type: methodology_anchor
  doi: "10.1016/j.jsb.2020.107545"
  citation: "Wu M, Lander GC, Herzik MA. Sub-2A apoferritin protocol J Struct Biol 2020 — explicitly lists CTF refine + Bayesian polishing as required steps"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
anti_rule_triggered: 11
veto_reason: "Sub-3A reconstruction attempted without per-particle CTF refinement and Bayesian polishing → resolution caps at 2.5A, claimed 'detector limit' actually unrecovered information"
related_positive_cases: [cryo-001-apoferritin-reference]
tags: [NEG, anti_pattern, no_ctf_refine, no_polishing, sub_3A_underperformance]
---

# NEG-NO-CTF-REFINE-SUB3A — sub-3A target without CTF refine / polishing

## Background (failure pattern)
For a sample with the resolution potential of apoferritin (1.5-2.0 Å with sufficient particles + symmetry), skipping per-particle CTF refinement and Bayesian polishing caps the achievable resolution at ~2.5 Å regardless of additional particle collection. The resolution wall is software, not hardware.

## What was actually done (the wrong path)
1. Standard pipeline through 3D refine; FSC stalls at 2.5 Å.
2. Author concludes "detector limit reached"; submits manuscript.
3. Reviewer asks for CTF refine + polishing; resolution drops to 1.8 Å on the same particles.

## ★ Why this is forbidden
- Per-particle CTF refinement recovers defocus inhomogeneity within the dataset (different particles have different effective defocus).
- Bayesian polishing recovers per-frame motion that pre-frame motion correction cannot resolve.
- Skipping either of these caps sub-3 Å reconstructions at the 2.5 Å wall.

## ★ Anti-rule mapping
**anti-rule 11**: resolution_target ∈ {`<2`, `2-3`} AND (`use_polishing=false` OR `use_ctf_refine=false`) → Reviewer veto (`CRYO_REVIEW_NO_POLISHING_AT_HIGH_RES`).

## Mitigation (rule 02-ctf-refine-polishing-mandatory)
- For sub-3 Å reconstructions, both CTF refine AND Bayesian polishing are mandatory.
- Skip only on initial low-resolution screens or with < 50k particles (where both steps overfit).
