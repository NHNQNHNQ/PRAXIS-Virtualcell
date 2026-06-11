---
case_id: NEG-IN-SILICO-ONLY-CLINICAL
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 2
edit_type: off_target_landscape
target_gene: any
target_organism: hg38
cell_context: any
editing_system: SpCas9
delivery_method: any
tools: [CFD, MIT, Cas-OFFinder]
key_paper_doi: 10.1038/nbt.3117
provenance:
  source_type: literature
  doi: 10.1038/nbt.3117
  citation: "Tsai SQ, Zheng Z, Nguyen NT, et al. GUIDE-seq enables genome-wide profiling of off-target cleavage by CRISPR-Cas nucleases. Nat Biotechnol. 2015;33(2):187-197."
  extracted_at: 2026-05-02
  source: praxis_neg_seed
tags: [anti_pattern, in_silico_only, no_guideseq, no_changeseq, clinical_grade, ind_filing]
causal_tag: causal
---

# NEG-IN-SILICO-ONLY-CLINICAL — In silico CFD/MIT alone for clinical sgRNA

## What this NEG- case records
**Anti-pattern**: declaring an sgRNA "off-target safe for clinical / IND filing" based only on in silico CFD or MIT scores or Cas-OFFinder enumeration, without orthogonal wet-lab off-target validation (GUIDE-seq, CHANGE-seq, CIRCLE-seq, Discover-seq).

## Where the failure mode was published
Tsai SQ et al. (2015) GUIDE-seq Nat Biotechnol Fig 3 + Suppl Table 2 documents that ~95% of in-silico-flagged off-target candidates are NOT cut by Cas9 in cells (false positives), AND that GUIDE-seq routinely detects 5-30 actual cleavage sites that have NO predicted in-silico match (false negatives at higher mismatch counts and via DNA/RNA bulges). Both directions of error make in-silico-only unsafe for therapeutic claims.

## Mechanism — why it fails
1. CFD/MIT use seed-region position weights from cell-line saturation experiments — they don't capture chromatin accessibility, methylation, or Cas9 protein concentration.
2. Bulge-tolerant off-targets (DNA bulge or RNA bulge with mismatch) are missed by Cas-OFFinder default mode.
3. Personalized off-targets in patient-specific SNPs aren't in reference genome → in-silico false negatives.
4. FDA IND guidance (Sep 2024) explicitly states orthogonal wet-lab assays are required for off-target evidence.

## Concrete numerics (Tsai 2015 + follow-up)
- In silico CFD top-100 → CHANGE-seq verifies only 5-15 actually cleave (~10-15% confirmation rate)
- GUIDE-seq detects 5-30 real off-targets per typical sgRNA, of which ~30-40% have NO in-silico match (mismatch > 4 OR bulge-tolerant)
- IND-grade evidence: GUIDE-seq + CHANGE-seq + amplicon-seq verification of top 20 candidates

## ★ Reviewer hard-stop
Any design plan with `clinical=True` OR `delivery=AAV/LNP+mRNA in vivo` that lacks `wetlab_off_target_assays: [GUIDE-seq, CHANGE-seq]` (or similar) must be vetoed. Required: explicit orthogonal off-target panel + amplicon-seq verification of top 20 in-silico candidates.

## Maps to anti-rule
**anti-rule #2**: In silico CFD/MIT alone for clinical / IND-grade off-target evidence is forbidden. Required: GUIDE-seq + CHANGE-seq (or equivalent orthogonal wet-lab assay).

## Anti-retrieval keywords
in silico only off target, cfd alone clinical, no guideseq, no changeseq, no circleseq, no wet lab off target, ind off target evidence
