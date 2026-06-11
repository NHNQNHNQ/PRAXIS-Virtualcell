---
rule_id: 07-validation-suite-mandatory
schema_version: 1
rule_type: case_distilled
applies_to:
  sample_types: [any]
evidence_cases:
  - cryo-005-modelangelo-buildmodel
confidence: high
last_updated: 2026-04-29
---

## 规则
**Every cryoEM model MUST report the full validation suite: MolProbity + Q-score + EMRinger + Ramachandran outliers.**

A single metric is insufficient to characterize model quality. The default thresholds:

| Metric | Pass threshold | What it catches |
|---|---|---|
| MolProbity score | < 2.0 | Overall geometric quality (rotamer + Ramachandran + clash) |
| Ramachandran outliers | < 0.5% | Backbone outliers |
| Rotamer outliers | < 1.5% | Side-chain outliers |
| Clash score | < 10 | Atom clashes per 1000 atoms |
| Q-score (Phenix) | > 0.5 | Atom-density agreement |
| EMRinger score | ≥ 1.0 | Side-chain rotamer-vs-density agreement |

A model that fails ≥ 2 of these is not publishable.

## Reviewer block code
`CRYO_REVIEW_NO_MOLPROBITY` (when reporting omits any of the 6 metrics)
