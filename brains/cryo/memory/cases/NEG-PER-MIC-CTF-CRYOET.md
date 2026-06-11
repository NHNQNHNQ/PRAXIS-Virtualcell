---
case_id: NEG-PER-MIC-CTF-CRYOET
schema_version: 1
case_polarity: negative
sample_type: in_situ_complex
target_pdb: null
target_emdb: null
molecular_weight_kda: null
symmetry_group: C1
resolution_target: "4-6"
resolution_achieved_a: null
detector_type: K3
detergent_or_lipid: none
method_choice: [per_micrograph_ctf_constant_defocus]
tools: [CTFFIND4 (default per-micrograph mode)]
status: anti_pattern
provenance:
  source_type: methodology_anchor
  doi: "10.7554/eLife.50973"
  citation: "Tegunov D, Cramer P. Warp 2019 — Warp's tilt-aware CTF estimation directly addresses the failure mode in this NEG- case"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
anti_rule_triggered: 7
veto_reason: "cryoET tilt series CTF estimated per-micrograph with single defocus; defocus actually changes with tilt → high-tilt phase corrections wrong → STA resolution capped"
related_positive_cases: [cryo-007-cryoet-subtomogram]
tags: [NEG, anti_pattern, per_micrograph_ctf, tilt_defocus_drift, high_tilt_phase_error]
---

# NEG-PER-MIC-CTF-CRYOET — per-micrograph CTF on a tilt series

## Background (failure pattern)
Each tilt in a cryoET series has a different effective defocus because the sample is tilted relative to the beam. A per-micrograph CTF estimate (single defocus per file) is correct for single-particle but wrong for tomography — high-tilt frames get systematically miscorrected, capping STA resolution.

## What was actually done (the wrong path)
1. CTFFIND4 invoked in default per-micrograph mode on each tilt-series stack.
2. Subtomogram averaging proceeds; resolution stalls at ~10 Å.
3. Re-CTF with Warp's tilt-aware mode (per-tilt defocus + dose weighting) → STA 5.5 Å on the same data.

## ★ Why this is forbidden
- A tilted specimen presents a defocus gradient across the field; the gradient grows with tilt angle.
- Modern tools (Warp, M, AreTomo) handle this; falling back to per-micrograph CTF on a tilt series throws away resolution.

## ★ Anti-rule mapping
**anti-rule 7**: cryoET sample with `per_tilt_ctf == false` → Reviewer veto.

## Mitigation (rule 09-cryoet-dose-sym-and-per-tilt-ctf)
- Use Warp / CTFFIND4 tilt-aware mode for every tilt.
- Verify defocus monotone behavior across tilt; outlier tilts are diagnostic of stage drift.
