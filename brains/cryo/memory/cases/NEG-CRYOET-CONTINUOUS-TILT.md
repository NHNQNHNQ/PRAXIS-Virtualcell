---
case_id: NEG-CRYOET-CONTINUOUS-TILT
schema_version: 1
case_polarity: negative
sample_type: in_situ_complex
target_pdb: null
target_emdb: null
molecular_weight_kda: null
symmetry_group: any
resolution_target: "4-6"
resolution_achieved_a: null
detector_type: K3
detergent_or_lipid: none
method_choice: [continuous_tilt_-60_to_+60]
tools: [SerialEM]
status: anti_pattern
provenance:
  source_type: methodology_anchor
  doi: "10.7554/eLife.50973"
  citation: "Tegunov D, Cramer P. Real-time cryo-EM data preprocessing with Warp. eLife 2019 — references the dose-symmetric tilt scheme (Hagen 2017) that this NEG- case violates"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
anti_rule_triggered: 6
veto_reason: "cryoET tilt series acquired with continuous -60° → +60° scheme; low-tilt frames receive accumulated dose damage at the most-information angles"
related_positive_cases: [cryo-007-cryoet-subtomogram]
tags: [NEG, anti_pattern, continuous_tilt, dose_damage, hagen_2017_violated]
---

# NEG-CRYOET-CONTINUOUS-TILT — continuous tilt scheme overdoses early frames

## Background (failure pattern)
Continuous tilt schemes (start at -60°, sweep to +60°) deposit dose monotonically. By the time the stage reaches the high-information low-tilt range, the sample has accumulated significant radiation damage. The dose-symmetric scheme (Hagen 2017) — start at 0°, alternate ±3° outward — preserves the low-tilt frames at low cumulative dose.

## What was actually done (the wrong path)
1. SerialEM tilt series scripted as -60° → +60° in 3° steps.
2. ~20 tilts × ~3 e⁻/Å² each.
3. Tomogram reconstruction proceeds; subtomogram averaging stalls at ~12 Å.
4. Re-collection with dose-symmetric scheme reaches 5.5 Å on the same target.

## ★ Why this is forbidden
- Continuous tilt damages high-information frames the most.
- Hagen 2017 demonstrated 2× resolution improvement from dose-symmetric scheme; it is the field-standard since.

## ★ Anti-rule mapping
**anti-rule 6**: cryoET sample (sample_type=in_situ_complex) with `tilt_scheme != dose_symmetric` → Reviewer veto.

## Mitigation (rule 09-cryoet-dose-sym-and-per-tilt-ctf)
- Always use dose-symmetric tilt scheme in SerialEM / Tomo5 / EPU-D acquisition scripts.
- Start at 0°, alternate ±3° outward to ±60°.
