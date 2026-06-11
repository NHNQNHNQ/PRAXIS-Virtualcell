---
case_id: NEG-NO-LIBRARY-QC-SCREEN
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 9
edit_type: pooled_crispr_screen_analysis
target_gene: genome_wide
target_organism: hg38
cell_context: K562
editing_system: SpCas9
delivery_method: lentivirus
tools: [MAGeCK, Brunello library, Gini coefficient, Lorenz curve]
key_paper_doi: 10.1038/nprot.2017.016
provenance:
  source_type: literature
  doi: 10.1038/nprot.2017.016
  citation: "Joung J, Konermann S, Gootenberg JS, et al. Genome-scale CRISPR-Cas9 knockout and transcriptional activation screening. Nat Protoc. 2017;12(4):828-863."
  extracted_at: 2026-05-02
  source: praxis_neg_seed
tags: [anti_pattern, no_library_qc, no_gini, biased_library, biased_counts, no_moi]
causal_tag: causal
---

# NEG-NO-LIBRARY-QC-SCREEN — Pooled CRISPR screen analyzed without library QC

## What this NEG- case records
**Anti-pattern**: running MAGeCK / DrugZ / BAGEL2 / RRA hit-calling on a pooled-CRISPR-screen counts table without first verifying the day-0 library distribution (Gini coefficient, Lorenz curve, reads-per-sgRNA distribution, MOI ≤ 0.3, ≥200x cell coverage). Hit calls on a biased library are dominated by sgRNA-representation artifacts, not true biology.

## Where the failure mode was published
Joung J et al. (2017) Nat Protocols Box 4 + Doench 2016 Nat Biotechnol both establish the QC baseline: Gini coefficient ≤ 0.3 on day-0 counts is required for hit-calling to be valid; library bottlenecks during selection (cells/sgRNA < 200x) produce stochastic dropouts that mimic biological dropouts.

## Mechanism — why it fails
1. Cloning + lentiviral packaging introduces representation bias — some sgRNAs are 10-100× over-represented.
2. If day-0 distribution is biased (Gini > 0.3), hit-calling normalization (median or control-sgRNA) cannot rescue under-represented sgRNAs from being called dropout-hits.
3. MOI > 0.3 means many cells have 2+ sgRNAs → counts blend signals across multiple genes.
4. Cell coverage < 200x sgRNA at infection means stochastic loss of sgRNAs during selection — looks like dropout but is just bottleneck.
5. Single time point (only day-0 OR day-14) provides no LFC reference — see anti-rule #10.

## Concrete numerics (Joung 2017 + Doench 2016)
- Gini ≤ 0.3 on day-0: required for hit-calling to be valid
- MOI 0.3 (Poisson 25% multi-guide rate): standard
- Cell coverage 200-1000x sgRNA: standard at infection
- Replicates ≥ 2 (preferably 3): required for MAGeCK MLE β-score
- Single-cell-per-sgRNA bottleneck = artefactual 30-50% false-positive hits

## ★ Reviewer hard-stop
Any pooled-CRISPR-screen analysis plan without an explicit `library_qc` block reporting `{gini_day0, lorenz_curve_path, moi_estimate, cell_coverage, n_replicates}` AND `gini_day0 ≤ 0.3` must be vetoed. Required: QC pass before hit-calling.

## Maps to anti-rule
**anti-rule #9**: Pooled CRISPR screen hit-calling without library QC (Gini, Lorenz, MOI, coverage, replicates) is forbidden. Required: Gini ≤ 0.3 on day-0 + MOI 0.3 + cell coverage ≥ 200x + ≥ 2 biological replicates.

## Anti-retrieval keywords
no library qc, no gini coefficient, no lorenz curve, no moi check, no cell coverage check, biased library, no replicate screen, single replicate screen
