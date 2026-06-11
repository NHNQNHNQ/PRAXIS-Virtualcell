---
rule_id: rule_08_population_variability_explicit
rule_type: case_distilled
applies_to: [allometric, pbpk, poppk, pkpd, tdm, fih]
evidence_cases:
  - pharma-001-allometric-scaling
  - pharma-002-pbpk-modeling
  - pharma-009-pkpd-emax
  - pharma-010-tdm-narrow-therapeutic
confidence: high
authoring_date: 2026-04-29
source_synthesis_section: §七 #4
---

# Subgroup analysis required for any dose recommendation

Average-population dose recommendations are clinically unsafe — every report
must include explicit subgroup adjustments where they are physiologically
meaningful:

- **Renal impairment**: eGFR strata for renally-cleared drugs (case-007 vanco).
- **Hepatic dysfunction**: Child-Pugh strata for hepatic-extraction drugs
  (case-002 PBPK midazolam).
- **Pharmacogenomic**: CYP2D6 / CYP3A5 strata when fm > 0.3 in those CYPs
  (case-010 tacrolimus).
- **Pediatric**: age-banded with maturation function (case-002).
- **Special**: pregnancy (case-by-case), critical illness (case-007 ICU vanco).

Output `dose_recommendation.subgroup_adjustments` must be non-empty when any
of the above strata are clinically relevant for the drug class. Reviewer
soft-warning: missing subgroup_adjustments downgrades confidence by 1.
