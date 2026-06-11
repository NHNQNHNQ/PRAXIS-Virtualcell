---
rule_id: 09-delivery-mode-safety
rule_type: case_distilled
applies_to:
  edit_type: [base_editing_a_to_g, base_editing_c_to_t, prime_editing, multiplex_knockout, in_vivo_gene_therapy, rna_targeting]
  cell_context: ALL
evidence_cases: [crispr-003, crispr-005, crispr-009, crispr-010]
confidence: high
---

# Delivery hierarchy for safety: mRNA+LNP > RNP > AAV-mRNA > lentivirus

Permanent / long-term editor expression accumulates off-target events. Choose the most transient delivery compatible with the experiment.

| Mode | Editor exposure | Use case |
|---|---|---|
| **mRNA + LNP** | hours | clinical (PCSK9 / Verve), HSC, T cell, hepatocyte in vivo |
| **RNP electroporation** | hours | primary T (CAR-T), HSC ex vivo, multiplex |
| **AAV (Cas9)** | months-years | research; clinical only when LNP infeasible (e.g., brain, retina) |
| **AAV (mRNA cargo)** | days-weeks | bridging tropism need with transient exposure |
| **Lentivirus** | permanent | in vitro screens only — clinical BLOCKED |
| **Plasmid transfection** | days | in vitro proof of concept |

**Action:** `delivery_method_compatibility` QA layer enforces these per edit_type (config/tools.yaml#delivery_compat). The Reviewer escalates `lentivirus + clinical` to a hard-stop unless overridden.
