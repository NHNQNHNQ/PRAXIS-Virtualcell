---
case_id: NEG-NO-BYSTANDER-PRED
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 7
edit_type: base_editing_a_to_g
target_gene: any
target_organism: hg38
cell_context: HEK293T
editing_system: ABE8e
delivery_method: LNP+mRNA
tools: [BE-Hive, BEEP, BE-Designer, CRISPResso2 base editing mode]
key_paper_doi: 10.1016/j.cell.2020.05.037
provenance:
  source_type: literature
  doi: 10.1016/j.cell.2020.05.037
  citation: "Arbab M, Shen MW, Mok B, et al. Determinants of Base Editing Outcomes from Target Library Analysis and Machine Learning. Cell. 2020;182(2):463-480.e30."
  extracted_at: 2026-05-02
  source: praxis_neg_seed
tags: [anti_pattern, no_bystander, no_be_hive, missense_byproduct, splicing_disruption]
causal_tag: causal
---

# NEG-NO-BYSTANDER-PRED — Base editor design without bystander prediction

## What this NEG- case records
**Anti-pattern**: shipping a base editor (ABE / CBE / their successors) sgRNA design without explicitly predicting per-window bystander A or C edit rates. Same-window non-target A's and C's are co-edited at 10-80% efficiency depending on position — these unintended edits can introduce missense mutations, disrupt splicing, or change protein register.

## Where the failure mode was published
Arbab M et al. (2020) Cell "BE-Hive" trained ML models on >100k base-editor target/outcome pairs across multiple editor variants. Fig 3 + Suppl Fig S6 show that within the canonical 4-8 protospacer window, every A or C is edited at a position-dependent rate (peak at position 6, drop-off ±2 positions). Up to 10% of intended-edit events also produce non-synonymous bystander missense mutations within the protospacer.

## Mechanism — why it fails
1. ABE TadA-8e deaminates A→I (read as G) within the ~5-nt protospacer window; window edges have lower but nonzero rates.
2. CBE4max APOBEC1 deaminates C→T similarly.
3. If the protospacer 4-8 window contains any non-target A (for ABE) or C (for CBE), it WILL be edited at 10-50% of the on-target rate.
4. Bystanders adjacent to splice sites can disrupt splicing → exon skipping or cryptic splicing.
5. Bystanders within a CDS create missense mutations that may alter protein function.
6. Without BE-Hive prediction (or equivalent), the design is blind to these confounders.

## Concrete numerics (Arbab 2020)
- ABE8e on a protospacer with 3 A's in window 4-8: target A (pos 6) edits at 75%; bystander A (pos 4) at 35%; bystander A (pos 8) at 25%
- BE-Hive RMSE on bystander rate prediction: ~6% per A — useful for selecting protospacers with ≤ 1 bystander A in window
- Real-world impact: TGFB1 enhancer design, alternate sgRNAs with 1 vs 3 window A's: 1-A version 0% missense, 3-A version 18% missense

## ★ Reviewer hard-stop
Any BE / PE design plan without `bystander_predictions` field (a list of {position, base, predicted_edit_rate} for every same-window A or C) must be vetoed. Required: BE-Hive (or equivalent position-weighted heuristic) per-window prediction reported.

## Maps to anti-rule
**anti-rule #7**: Base editor / prime editor design without per-window bystander A or C edit-rate prediction is forbidden. Required: BE-Hive prediction or equivalent (every A in window 4-8 must have an explicit predicted rate).

## Anti-retrieval keywords
no bystander prediction, no be-hive, no per-window rate, missense bystander, splicing bystander, no a c editing prediction, base editor blind window
