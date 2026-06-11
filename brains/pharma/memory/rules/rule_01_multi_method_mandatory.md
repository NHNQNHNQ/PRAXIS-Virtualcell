---
rule_id: rule_01_multi_method_mandatory
rule_type: case_distilled
applies_to: [ddi, fih, nca, poppk, ppb]
evidence_cases:
  - pharma-003-cyp3a4-ddi
  - pharma-005-fih-dose-escalation
  - pharma-006-nca-pk
  - pharma-007-poppk-mrgsolve
confidence: high
authoring_date: 2026-04-29
source_synthesis_section: §一 row 'PRR alone no comparator' & §七 #1
---

# Multi-method mandatory

For high-stakes pharmacology decisions, never rely on a single method. Use ≥2
complementary approaches and report agreement / disagreement explicitly:

| Domain | Required pairing |
|---|---|
| **DDI** | static FDA model + dynamic PBPK (case-003) |
| **FIH dose** | NOAEL + MABEL for any immune-modulating mechanism (case-005) |
| **PK estimation** | NCA + popPK or NCA + IVIVE (case-006, case-007) |
| **Plasma protein binding** | equilibrium dialysis + ultrafiltration (case-008) |
| **FAERS signals** | PRR + ROR + IC25 (case-004) |

If only one method is feasible, downgrade `confidence_label` ≥ 1 step and add
to `flags`: `single_method_only`.
