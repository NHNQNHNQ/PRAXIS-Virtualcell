---
rule_id: rule_06_immune_modulator_mabel_required
rule_type: case_distilled
applies_to: [fih, pkpd]
evidence_cases:
  - pharma-005-fih-dose-escalation
  - pharma-009-pkpd-emax
  - pharma-007-poppk-mrgsolve
confidence: high
authoring_date: 2026-04-29
source_synthesis_section: §一 row 'NOAEL only ignore MABEL'
---

# MABEL approach mandatory for immune-modulator FIH

After the TGN1412 disaster (2006, anti-CD28 superagonist, 6 healthy volunteers
hospitalized with cytokine storm at NOAEL/500), regulators require Minimum
Anticipated Biological Effect Level (MABEL) for any immune-modulating
biologic.

Mandatory:
- **Indication trigger**: FIH for an immune modulator → MABEL design forced.
- **MABEL inputs**: in vitro receptor occupancy (RO) curve → dose for
  ≤10% RO across the most-sensitive cell population.
- **Both NOAEL and MABEL** must be computed; lower of the two governs.
- **Safety factor calibration**: 50–100× for novel immune mechanisms; 10× only
  for well-characterized small molecules.

Reviewer HR-04 fires on `method_choice.primary == 'noael'` for biologic immune
modulator without MABEL co-method.
