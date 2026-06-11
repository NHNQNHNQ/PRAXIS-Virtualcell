---
rule_id: rule_03_cyp3a5_genotype_for_tacro
rule_type: case_distilled
applies_to: [tdm, poppk]
evidence_cases:
  - pharma-010-tdm-narrow-therapeutic
  - pharma-003-cyp3a4-ddi
  - pharma-007-poppk-mrgsolve
confidence: high
authoring_date: 2026-04-29
source_synthesis_section: §七 #6
---

# CYP3A5 genotype mandatory for tacrolimus / Asian / African ancestry TDM

Tacrolimus dose-response depends strongly on CYP3A5 expression. *1 carriers
(*1/*1 or *1/*3) have ~1.5–1.6× higher CL than *3/*3 non-expressers and need
proportionally higher doses. Asian and African ancestry have higher *1
prevalence (~30–50%).

Mandatory:
- TDM call without CYP3A5 genotype → `flags: ["missing_genotype_for_tacro"]`,
  Reviewer downgrades confidence by 1 step.
- popPK fits should include CYP3A5 genotype as a covariate when available.
- Initial dose recommendations differ ≥30% between expresser and non-expresser
  → starting dose error if genotype skipped.
