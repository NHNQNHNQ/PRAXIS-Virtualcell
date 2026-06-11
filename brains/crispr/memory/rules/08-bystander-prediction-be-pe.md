---
rule_id: 08-bystander-prediction-be-pe
rule_type: case_distilled
applies_to:
  edit_type: [base_editing_a_to_g, base_editing_c_to_t, prime_editing]
  cell_context: ALL
evidence_cases: [crispr-003, crispr-004]
confidence: high
---

# Bystander edits must always be predicted

Base editors edit **all** A's (ABE) or C's (CBE) within the protospacer 4-8 window — not just the targeted base. Unintended bystanders can:
- introduce missense variants (impacts function)
- disrupt splicing (if near splice sites)
- change protein register (if synonymous changes coincidence)

**Tool:** BE-Hive (Arbab 2020) for base editors; PrimeDesign + scaffold-incorporation check for prime editors.

**Reviewer hard-stop:** every BE / PE design must include `bystander_edits[]` (even if empty list "no bystanders predicted").

**Action:** base_editor_design and prime_editor_pegrna skills emit per-window edit-rate tables and flag if max bystander rate ≥ 5%.
