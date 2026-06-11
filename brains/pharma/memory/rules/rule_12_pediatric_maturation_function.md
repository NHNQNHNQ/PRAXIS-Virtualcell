---
rule_id: rule_12_pediatric_maturation_function
rule_type: case_distilled
applies_to: [poppk, pbpk, fih]
evidence_cases:
  - pharma-011-pediatric-tacrolimus-poppk
  - pharma-002-pbpk-modeling
  - pharma-007-poppk-mrgsolve
confidence: high
authoring_date: 2026-04-30
source_synthesis_section: pediatric extrapolation + ontogeny
---

# 儿科 maturation function 必需

Pediatric drug clearance does not scale linearly from adult by body weight
alone. CYP3A4, CYP2C9, CYP2D6, UGT1A1, and renal function all develop on
distinct ontogeny curves that must be modeled when extrapolating adult popPK
to pediatric populations.

## Anderson 2008 sigmoidal Hill maturation

`F_mat(age_postnatal_months) = age^Hill / (TM50^Hill + age^Hill)`

| Function/enzyme | TM50 (months) | Hill | Reference |
|-----------------|---------------|------|-----------|
| GFR (renal) | 14 | 3.4 | Anderson 2008 ARPT 48:303 |
| CYP3A4 | 16-20 | 1.5-3 | Anderson 2002 BJCP 53:625 |
| CYP1A2 | 6-12 | 2-3 | (slow, 2-yr asymptote) |
| CYP2D6 | 1-2 | 2-4 | (fast, near-adult by 6 mo) |
| UGT2B7 | 12 | 2 | (morphine glucuronidation) |

## Mandatory operations

1. **Apply maturation factor** to typical CL when fitting / predicting in pediatric
   populations. Without it, naive popPK underestimates θ_CL_adult by ~30-50%
   because infants pull down the pooled CL/kg estimate.
2. **Age stratification**: neonate (0-28 d), infant (1-12 mo), toddler (1-2 y),
   child (2-12 y), adolescent (12-18 y) — each may have distinct PK behavior.
3. **Body weight scaling exponent** for CL: 0.75 standard adult; consider 0.7
   for pre-school children and 1.0 for neonates (scaling shifts during ontogeny).
4. **Avoid extrapolation to extremes**: don't apply adult maturation curve to
   pre-term neonates (post-menstrual age framework needed; Holford 2013 BJCP).
5. **External validation cohort**: pediatric popPK models trained on one age
   range must be validated against an independent cohort before clinical
   deployment (case-011 lesson; rule_04 generalization).

## Reviewer soft-flag triggers

- Pediatric popPK fit without maturation function → flag (`missing_age_for_maturation`).
- popPK developed on adults applied to pediatrics without explicit refit → reject.
- Drug with maturation-prone metabolic pathway (CYP3A4, UGT2B7 for morphine,
  N-acetyltransferase for INH) used in pediatrics without ontogeny consideration.
