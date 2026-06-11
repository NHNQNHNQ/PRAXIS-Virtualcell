---
rule_id: rule_05_concomitant_drug_dynamic_review
rule_type: case_distilled
applies_to: [ddi, tdm]
evidence_cases:
  - pharma-003-cyp3a4-ddi
  - pharma-010-tdm-narrow-therapeutic
  - pharma-005-fih-dose-escalation
confidence: high
authoring_date: 2026-04-29
source_synthesis_section: §一 row 'Concomitant drug list 不更新'
---

# Concomitant medication review at every visit

DDI risk is dynamic: starting / stopping a CYP3A inhibitor or inducer changes
substrate AUC by 2–10× within days–weeks. Mandatory review steps:

- **TDM visit**: re-pull current concomitant drug list before each dose
  recommendation; flag any new/stopped strong CYP3A perpetrator.
- **DDI prediction**: must explicitly enumerate ALL concurrent perpetrators,
  not just the headline one. Multiplicative effects (rule_01).
- **TGN1412-style escalation**: in FIH, monitor concomitant medication during
  ramp-up; flag new perpetrator within 48 h before next escalation step.
