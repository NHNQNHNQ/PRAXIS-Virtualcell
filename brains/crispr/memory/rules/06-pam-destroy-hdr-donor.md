---
rule_id: 06-pam-destroy-hdr-donor
rule_type: case_distilled
applies_to:
  edit_type: [knock_in_hdr, saturation_genome_editing_sge]
  cell_context: ALL
evidence_cases: [crispr-007, crispr-008]
confidence: high
---

# HDR donor MUST destroy the PAM

If the integrated allele still presents a NGG PAM at the original cut site, Cas9 will **re-cut** the integrated locus, leading to indel reversal of the HDR product.

**How to destroy:**
1. Best: **silent codon swap** that breaks the PAM (e.g., NGG → NGT in a synonymous codon).
2. Acceptable: **single base substitution** at PAM[2] or PAM[3] that does not affect the protein (synonymous if in CDS).
3. For sgRNA targeting in non-coding region: any base change at PAM is fine.

**Reviewer hard-stop:** any HDR donor without `pam_destruction_changes` is BLOCKED.

**Action:** hdr_donor_design skill calls `tools.seq_utils.silent_mutate_pam` and reports the change in `pam_destruction_changes`. The Reviewer rejects designs where `pam_destroyed=false`.
