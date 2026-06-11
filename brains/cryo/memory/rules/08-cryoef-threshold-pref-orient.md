---
rule_id: 08-cryoef-threshold-pref-orient
schema_version: 1
rule_type: case_distilled
applies_to:
  sample_types: [any]
evidence_cases:
  - cryo-006-preferred-orientation
confidence: high
last_updated: 2026-04-29
---

## 规则
**Preferred-orientation diagnostics MUST be run post-refinement; cryoEF < 0.7 is a red flag, < 0.5 is a re-collection trigger.**

| cryoEF range | Severity | Action |
|---|---|---|
| ≥ 0.7 | OK | None |
| 0.5–0.7 | Warn | Tier-1 mitigation: surfactant additive, switch to graphene-oxide / chameleon grid, try UltrAuFoil |
| < 0.5 | Severe | Tier-2: tilted-data acquisition (30°/60°), GraFix crosslinking; re-collect rather than software-rescue |

In addition to cryoEF, ALWAYS report:
- Angular distribution histogram (cryoSPARC `plot_3D_refinement_histograms`).
- 3DFSC directional FSC (worst-vs-best ratio).
- Local resolution map alongside the global FSC.

## Excluded actions
- Reporting "FSC = X Å" without cryoEF / 3DFSC. The single FSC number can hide a 5+ Å worst-direction.
- "Software fix" for a dataset with cryoEF < 0.5 (no algorithm recovers angular information that wasn't collected).

## Reviewer block code
`CRYO_REVIEW_NO_PREF_ORIENT_CHECK`
