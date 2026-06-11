---
rule_id: 04-latest-editor-version
rule_type: case_distilled
applies_to:
  edit_type: [base_editing_a_to_g, base_editing_c_to_t, prime_editing, multiplex_knockout]
  cell_context: ALL
evidence_cases: [crispr-003, crispr-004, crispr-005]
confidence: high
---

# Always use the latest-version editor

Older base / prime / Cas12a editors have **5-10× lower activity** than the latest versions. Reviewer hard-blocks legacy versions.

| Class | Use | Block (legacy) |
|---|---|---|
| ABE | **ABE8e** (Richter 2020) or ABE8.20-m | ABE7.10, ABE7.9, ABE6 |
| CBE | **CBE4max**, evoBE4max, eA3A-BE4max | CBE3, BE3, BE4 |
| PE | **PE3 + epegRNA** (Nelson 2022); PE5 with dnMLH1 if MMR-deficient | PE2-only |
| Cas12a multiplex | **enAsCas12a** (Kleinstiver 2019) — TYCV/TATV PAM, higher specificity | LbCas12a (broad PAM, more off-target) |

**Action:** `editor_version_whitelist` QA layer rejects any case with editor in the blocklist (`config/tools.yaml#editors.blocklist`).
