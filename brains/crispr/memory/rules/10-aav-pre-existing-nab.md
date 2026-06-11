---
rule_id: 10-aav-pre-existing-nab
rule_type: case_distilled
applies_to:
  edit_type: [in_vivo_gene_therapy, knock_in_hdr]
  cell_context: [hepatocyte_in_vivo, in_vivo_organ]
  delivery_method: [AAV, AAV8, AAV9, AAV-LK03, AAV5, AAV6]
evidence_cases: [crispr-010]
confidence: high
---

# AAV clinical delivery requires pre-existing neutralizing-antibody (NAb) screen

~30-70% of the human population has pre-existing NAb to common AAV serotypes (AAV2 highest, AAV8 lower but still 30-50%). NAb-positive patients receive **no therapeutic dose** — capsid is neutralized in circulation.

**Required workflow for AAV clinical:**
1. **Pre-screen serum** for serotype-specific NAb (typically luciferase-based assay).
2. **Exclude NAb-positive** patients from enrollment.
3. **Document seroprevalence** for the chosen serotype in the trial population.
4. **Consider LNP+mRNA alternative** if seroprevalence > 50% (e.g., Verve VERVE-101 chose LNP precisely for this reason).

**Reviewer hard-stop:** any in_vivo_gene_therapy with `delivery_method` containing "AAV" AND `clinical=True` MUST include `nab_screen_required: true` in the report.

**Action:** in_vivo_delivery_planner skill emits the NAb screen requirement automatically when `clinical=True`.
