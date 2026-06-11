---
case_id: NEG-SINGLE-TIMEPOINT-SCREEN
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 10
edit_type: pooled_crispr_screen_analysis
target_gene: genome_wide
target_organism: hg38
cell_context: K562
editing_system: SpCas9
delivery_method: lentivirus
tools: [MAGeCK, dropout screen, day-0 vs day-14]
key_paper_doi: 10.1126/science.1246981
provenance:
  source_type: literature
  doi: 10.1126/science.1246981
  citation: "Wang T, Wei JJ, Sabatini DM, Lander ES. Genetic screens in human cells using the CRISPR-Cas9 system. Science. 2014;343(6166):80-84."
  extracted_at: 2026-05-02
  source: praxis_neg_seed
tags: [anti_pattern, single_timepoint, no_day0, no_lfc_reference, dropout_screen]
causal_tag: causal
---

# NEG-SINGLE-TIMEPOINT-SCREEN — Pooled screen with a single time point

## What this NEG- case records
**Anti-pattern**: running a dropout / positive-selection pooled CRISPR screen with only one time point (just day-0 OR just day-14, not both). Without paired time points, log-fold-change cannot be computed, and any "hit" is uninterpretable.

## Where the failure mode was published
Wang T et al. (2014) Science was the first paper to lay out the genome-scale dropout-screen design: lentiviral library at MOI 0.3, day-0 (post-puromycin selection) reference + day-14 to day-21 endpoint. The day-0 distribution is the LFC denominator; without it, no inference of relative dropout/enrichment is possible.

## Mechanism — why it fails
1. Pooled screen counts at any single time point reflect (library_representation × selection_effect × stochastic_drift). Without a reference time point, none of these can be separated.
2. A sgRNA with low day-14 reads might be (a) under-represented in the original library (representation), (b) genuinely dropout (selection), or (c) lost stochastically during cell expansion (drift). Single time point can't distinguish.
3. LFC = log2(day-N / day-0) is the only valid screen readout. Day-0 alone says nothing about phenotype. Day-N alone says nothing about LFC.
4. Time-series screens (day-0 + day-7 + day-14 + day-21) further enable kinetic analysis.

## Concrete numerics (Wang 2014)
- Standard genome-scale screen: day-0 (200x cell coverage post-selection) + day-14 (2 doublings + selection pressure)
- Single time point analysis: 0% interpretable hits (no LFC)
- Two time points (day-0 + day-14): MAGeCK β-score + RRA p-value enable hit-calling
- Time-series (day-0 + day-7 + day-14 + day-21): kinetic models reveal slow vs fast essential genes

## ★ Reviewer hard-stop
Any pooled-screen analysis plan with `time_points: [single_value]` (only one timepoint) must be vetoed. Required: ≥ 2 time points (typically day-0 reference + day-14 endpoint); ideally 3-4 for kinetic analysis.

## Maps to anti-rule
**anti-rule #10**: Pooled screen with a single time point (only day-0 OR only day-14, not both) is forbidden. Required: paired time points (day-0 reference + day-14+ endpoint, minimum).

## Anti-retrieval keywords
single timepoint screen, only day0 screen, only day14 screen, no day0 reference, no time series, no lfc reference, single endpoint screen
