---
rule_id: rule_02_confidence_interval_required
rule_type: case_distilled
applies_to: [allometric, poppk, tdm, ppb, pkpd]
evidence_cases:
  - pharma-001-allometric-scaling
  - pharma-007-poppk-mrgsolve
  - pharma-008-protein-binding-fu
  - pharma-010-tdm-narrow-therapeutic
confidence: high
authoring_date: 2026-04-29
source_synthesis_section: §七 #3
---

# 95% CI required on every PK estimate

Any PK parameter (CL, V, t1/2, AUC), allometric exponent, or dose
recommendation must report a 95% confidence interval. Point estimates alone
are misleading and trigger Reviewer HR-01 for allometric scaling.

Required forms:
- **Allometric**: `slope ± t(0.975, df=n-2) × stderr` from log-log regression
  (case-001).
- **popPK**: bootstrap or asymptotic SE on θ; ω² from η variance (case-007).
- **TDM**: predicted next-trough CI from individual posterior + residual error
  (case-010).
- **fu**: replicate measurements + propagate error (case-008).

Single-point predictions without CI: `flags: ["no_confidence_interval"]` →
Reviewer downgrade.
