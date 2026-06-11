---
rule_id: 03-off-target-clinical-wetlab
rule_type: case_distilled
applies_to:
  edit_type: [knockout_indel, base_editing_a_to_g, base_editing_c_to_t, prime_editing, knock_in_hdr, in_vivo_gene_therapy]
  cell_context: ALL
evidence_cases: [crispr-002, crispr-010]
confidence: high
---

# Clinical sgRNAs require WET-LAB off-target validation

In silico CFD scoring is **necessary but not sufficient** for clinical applications. ~95% of in-silico-flagged off-targets are not actually cleaved (Tsai 2015).

**Required orthogonal assays for IND filing:**
1. **GUIDE-seq** (Tsai 2015) — dsODN integration at actual cut sites; sensitive in cells.
2. **CHANGE-seq** (Lazzarotto 2020) — circular in-vitro, highest sensitivity.
3. **CIRCLE-seq** (Tsai 2017) — circularized genome in vitro.

**Action:** if `clinical=True`, the off_target_predict skill MUST emit `CLINICAL_WETLAB_REQUIRED` flag and the Reviewer must block report finalization until wetlab data is attached.

**Bonus:** chromatin accessibility (ATAC-seq) further filters in-silico off-targets — closed-chromatin sites usually don't get cut even when in silico scores high.
