---
case_id: NEG-NO-PAM-DESTROY-HDR
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 5
edit_type: knock_in_hdr
target_gene: any
target_organism: hg38
cell_context: iPSC
editing_system: SpCas9
delivery_method: ssODN_RNP
tools: [SpCas9, ssODN, dsDNA donor, Benchling, primer3]
key_paper_doi: 10.1038/nature17664
provenance:
  source_type: literature
  doi: 10.1038/nature17664
  citation: "Paquet D, Kwart D, Chen A, et al. Efficient introduction of specific homozygous and heterozygous mutations using CRISPR/Cas9. Nature. 2016;533(7601):125-129."
  extracted_at: 2026-05-02
  source: praxis_neg_seed
tags: [anti_pattern, no_pam_destroy, recutting, indel_revert, hdr_donor]
causal_tag: causal
---

# NEG-NO-PAM-DESTROY-HDR — HDR donor that does not destroy the PAM

## What this NEG- case records
**Anti-pattern**: HDR donor (ssODN, dsDNA, AAV) that delivers the desired edit but leaves the original NGG PAM (or NNGRRT for SaCas9) intact in the integrated allele. Cas9 re-cuts the integrated locus → indel formation reverts the HDR product to a mosaic of indels.

## Where the failure mode was published
Paquet 2016 Nature Fig 2-3 establishes the PAM-blocking principle: introducing silent mutations in the PAM (e.g., NGG → NGT) on the donor produces 10-100× higher pure-HDR rate than donors that preserve the PAM. The paper became the standard reference for HDR donor design.

## Mechanism — why it fails
1. After HDR uses the donor as template, the integrated allele still presents the original protospacer + intact PAM.
2. Cas9-sgRNA RNP is still present in the cell for hours-to-days post-delivery.
3. Re-cleavage at the integrated allele triggers another round of NHEJ — typically introduces an indel (frameshift) at the cut site.
4. The "successful" HDR clone now has an indel-at-cut-site allele, indistinguishable from a non-HDR allele by junction PCR.
5. Net result: 60-80% of "HDR-positive" clones in bulk are actually indel-reverted.

## Concrete numerics (Paquet 2016)
- iPSC APP-Swedish point mutation, donor without PAM destroy: 4% pure HDR + 30% indel revert at the same site
- Same locus, donor with synonymous PAM-destroy (silent codon swap): 22% pure HDR + 5% indel revert
- 6-fold improvement in pure-HDR rate just from PAM destroy

## ★ Reviewer hard-stop
Any HDR donor design (ssODN, dsDNA, AAV) without `pam_destruction_changes` field listing at least one base substitution at PAM[2] or PAM[3] (preferably synonymous codon swap if in CDS) must be vetoed. Required: silent PAM-destroying mutation in donor.

## Maps to anti-rule
**anti-rule #5**: HDR donor without PAM destruction is forbidden. Required: silent codon swap or synonymous mutation that breaks NGG → NGN/NNN at PAM positions 2-3.

## Anti-retrieval keywords
no pam destroy, hdr donor recut, indel revert hdr, intact pam donor, no silent mutation pam, donor recut by cas9
