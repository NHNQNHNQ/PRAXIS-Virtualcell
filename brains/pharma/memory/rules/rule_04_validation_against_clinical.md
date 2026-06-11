---
rule_id: rule_04_validation_against_clinical
rule_type: case_distilled
applies_to: [pbpk, poppk, pkpd]
evidence_cases:
  - pharma-002-pbpk-modeling
  - pharma-007-poppk-mrgsolve
  - pharma-009-pkpd-emax
confidence: high
authoring_date: 2026-04-29
source_synthesis_section: §一 row 'PBPK 不 verify clinical' & §七 #2
---

# PBPK / popPK / PK-PD predictions require clinical validation

No model output is acceptable without validation against observed clinical
data:

- **PBPK**: predicted Cmax / Tmax / AUC must fall within 2-fold of published
  clinical PK before downstream use (case-002). Otherwise: regulator-rejectable.
- **popPK**: VPC mandatory (case-007); ≥80% of binned timepoints' observed
  median must fall within simulated 90% prediction interval.
- **PK-PD**: E-R analysis required for oncology BLA (FDA mandate, case-009).

Reviewer HR-02 fires on PBPK without `validation_type ==
'clinical_pk_comparison'`.
