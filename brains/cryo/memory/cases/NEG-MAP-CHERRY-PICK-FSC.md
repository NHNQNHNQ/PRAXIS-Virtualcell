---
case_id: NEG-MAP-CHERRY-PICK-FSC
schema_version: 1
case_polarity: negative
sample_type: any
target_pdb: null
target_emdb: null
molecular_weight_kda: 300
symmetry_group: C1
resolution_target: "3-4"
resolution_achieved_a: 3.0
detector_type: K3
detergent_or_lipid: none
method_choice: [single_direction_fsc_no_gold_standard]
tools: [cryoSPARC v4]
status: anti_pattern
provenance:
  source_type: methodology_anchor
  doi: "10.1016/j.jsb.2020.107545"
  citation: "FSC 0.143 gold-standard convention is field-wide consensus; the Wu/Lander/Herzik protocol is the canonical reference"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
anti_rule_triggered: 12
veto_reason: "FSC reported at non-gold-standard threshold (e.g. 0.5 or 0.333) OR claimed resolution does not match measured FSC at 0.143 → cherry-picked metric"
related_positive_cases: [cryo-001-apoferritin-reference, cryo-006-preferred-orientation]
tags: [NEG, anti_pattern, fsc_cherry_pick, non_gold_standard, resolution_overstated]
---

# NEG-MAP-CHERRY-PICK-FSC — FSC reported at the wrong threshold

## Background (failure pattern)
The gold-standard FSC threshold is 0.143 (computed from independent half-maps). Reporting an FSC at 0.5 (the older, more permissive threshold) inflates the claimed resolution by ~0.3-0.5 Å. Worse: reporting an FSC value extracted at a single direction (without 3DFSC) hides preferred-orientation anisotropy.

## What was actually done (the wrong path)
1. Author reports "FSC = 2.8 Å at 0.5 cutoff" without specifying which cutoff.
2. The half-map FSC at 0.143 is 3.4 Å.
3. Map deposited with the inflated claim; downstream model builders waste time fitting side-chains that the map does not actually support.

## ★ Why this is forbidden
- The 0.143 threshold (Rosenthal & Henderson 2003) is the field-wide consensus and corresponds to a defined SNR.
- Cherry-picking a single direction's FSC without 3DFSC hides preferred-orientation anisotropy.
- Any resolution claim must include: (a) the cutoff used, (b) how it was computed (mask, half-maps), (c) the worst-direction value if relevant.

## ★ Anti-rule mapping
**anti-rule 12**: resolution claim without explicit `fsc_threshold = 0.143` AND/OR claim mismatches the measured FSC by > 0.3 Å → Reviewer veto (`CRYO_REVIEW_FSC_NOT_GOLD_STANDARD`).

## Mitigation (rules 01, 08)
- Always report FSC at the gold-standard 0.143.
- Always pair with cryoEF + 3DFSC to characterize anisotropy.
- The signature `resolution_method` QA layer cross-checks claim vs EMDB-reported value (within ± 0.5 Å).
