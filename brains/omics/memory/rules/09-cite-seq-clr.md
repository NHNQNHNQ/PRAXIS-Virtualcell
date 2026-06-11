---
rule_id: 09-cite-seq-clr
rule_type: case_distilled
applies_to:
  modality: CITE_seq
  study_design: ALL
  tissue_class: ALL
  task: [normalization, integration, doublet, annotation]
evidence_cases:
  - case_id: omics-007-citeseq-bmnc-wnn
    page_hint: "Step 1 (ADT CLR); ★失败 (antibody capture noise)"
confidence: high
status: active
created: 2026-04-29
---

# CITE-seq priors — ADT normalization, dual-modal doublet, WNN

## Statement
1. **ADT normalization = CLR (centered log-ratio)**, NOT log-normalize. CITE
   ADT counts are compositional; total ADT per cell varies a lot but
   compositions are what matter.
2. **Isotype control subtraction**: subtract per-cell mean isotype signal from
   each ADT before WNN. Panels without isotype controls cannot reach high
   confidence.
3. **Doublet detection on RNA + ADT jointly**, not RNA alone: CITE doublets
   show CD3+CD19 co-positivity that RNA-only methods miss.
4. **Multi-modal integration via WNN / totalVI / muon**, never `cbind` raw RNA
   and ADT into one matrix for PCA — count scales differ by 100x.
5. **Annotation = RNA marker × ADT marker double-source**; cluster with
   discordant signal (e.g. RNA = Treg, CD25 protein low) routed to `_review`.

## Why
- ADT log-normalize ignores compositional structure — "high CD4" can mean cell
  picked up more antibodies overall, not more CD4 specifically (case 007).
- CITE doublet (case 007 failure mode): T+B doublet shows CD3+CD19 — invisible
  to RNA-only doublet detector.
- Antibody-capture noise (bead residual) → "all cells positive": detect via
  ADT density bimodality plot.

## RNA-protein discordance is biology, not noise
CD69 / inducible markers: protein lags or leads mRNA by hours. Cells with
high CD69 protein but low `Cd69` mRNA are real activated cells; do not filter.

## Cold-start fallback
- Panel lacks isotype controls → flag `confidence: medium`; report all ADT
  results with caveat.
- Panel < 10 antibodies → annotation must lean RNA-heavy (lower WNN ADT
  weight floor).
