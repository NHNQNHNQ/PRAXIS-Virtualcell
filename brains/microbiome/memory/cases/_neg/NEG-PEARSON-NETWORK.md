---
case_id: NEG-PEARSON-NETWORK
case_type: anti_pattern
microbiome_task: network_inference
failure_mode: Pearson/Spearman correlation on relative abundance produces spurious co-occurrence networks
maps_to_anti_rule: 8
maps_to_reviewer_block: MICROBIOME_REVIEW_PEARSON_NETWORK
evidence_doi: 10.1371/journal.pcbi.1002687
evidence_quote: "Pearson correlation on compositional data (e.g., 16S relative abundance) systematically reports negative correlations between every pair of abundant taxa as an artifact of the unit-sum constraint. SparCC, SPIEC-EASI, and CCREPE were designed specifically to break this closure and recover the underlying interactions."
status: validated_neg
schema_version: 2
---

# NEG-PEARSON-NETWORK — Pearson on relative abundance for network inference

## Pattern
Building a microbial co-occurrence network by computing pairwise Pearson (or Spearman) correlation on the **relative-abundance** table, then thresholding |r| > 0.5 (or any cutoff) to draw edges. Frequently visualized as a Cytoscape network with claims about "ecological interactions" or "keystone taxa."

## Why it fails
- Friedman & Alm 2012 proved: in compositional data the **expected** Pearson correlation between two random (independent) features is NEGATIVE, with magnitude growing as feature count shrinks
- The unit-sum constraint forces: if taxon A goes up in some samples, the SUM of all other taxa goes down → spurious negative edges everywhere
- Spearman (rank) does NOT fix the closure — same problem in monotonic form
- Result: network is dominated by **artifactual** negative edges between high-abundance taxa, completely obscuring real ecological signal
- SparCC (iterative log-ratio + sparsity), SPIEC-EASI (graphical lasso on CLR), FastSpar (C++ SparCC), CCLasso, and PropR were all built specifically to break compositional closure

## Real failure example
A 2018 soil microbiome paper drew a 200-node "interaction network" from Pearson on relative abundance and identified 5 "keystone" Proteobacteria. Re-analysis with SparCC + 100 bootstraps on the SAME OTU table produced only 12 robust edges (none involving the original 5 "keystones"). The Pearson network was 95%+ closure artifact; the actual ecology was much sparser and centered on *Bradyrhizobium*–*Mesorhizobium* mutualism (real biology, missed by Pearson).

## Anti-pattern detector
- `design_plan.computational_pipeline.task = network_inference`
- AND `design_plan.computational_pipeline.method` ∈ {`pearson`, `spearman`, `correlation`, `cor`, `np.corrcoef`}
- AND input units ∈ {`relative_abundance`, `proportion`, `count_normalized`}
- → MICROBIOME_REVIEW_PEARSON_NETWORK

## Recovery
- Use **SparCC** (Friedman & Alm 2012) or **SPIEC-EASI** (Kurtz 2015) or **FastSpar** (Watts 2019) — all consume raw counts and do CLR / log-ratio internally
- Always bootstrap (≥100 iterations) and threshold by p-value, not by raw |r|
- Report sparsity statistics (edge count, edge density) — real microbial networks are sparse
- Cite `microbiome-008-network-inference` + `08-sparcc-or-spieceasi-not-pearson` + `NEG-PEARSON-NETWORK`
