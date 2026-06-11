---
rule_id: 08-compositional-network-methods
rule_type: case_distilled
applies_to: {microbiome_task: [network], sample_type: ALL}
confidence: high
evidence_cases: [microbiome-008-cooccurrence-network]
schema_version: 2
---

# Rule 08: Use compositional-aware network inference (SparCC / SPIEC-EASI / FlashWeave)

## Statement
Microbial co-occurrence networks MUST use compositional-aware inference methods: SparCC (sparse correlations for compositional data), SPIEC-EASI (graphical lasso on CLR-transformed data), or FlashWeave (constraint-based, conditional independence). Pearson / Spearman correlation on raw counts is invalid and produces >50% spurious edges (Friedman & Alm 2012, 10.1371/journal.pcbi.1002687).

## Why
Compositional bias creates spurious negative correlations between abundant taxa (since they share the unit-sum constraint). Indirect associations also confound: A→B and A→C make B–C appear correlated. SparCC iteratively estimates the underlying basis correlations; SPIEC-EASI uses sparse inverse covariance to distinguish direct from indirect; FlashWeave uses graphical model independence tests.

## How to apply
- Reviewer gate `MICROBIOME_REVIEW_PEARSON_NETWORK`: trigger when `task=cooccurrence_network` AND `network.method ∈ {pearson, spearman_on_raw_count}`.
- Skill `cooccurrence_network/run.py` (P1 stub) implements SparCC + SPIEC-EASI + FlashWeave.
- Minimum sample size: ≥50 for stable correlation estimates; ideally ≥100.
- Cluster network with Louvain / Leiden for module detection.

## Evidence
- microbiome-008: explicit anti-pattern — "Pearson on raw count for network".

## Anti-patterns
- ❌ scipy.stats.pearsonr on raw count matrix
- ❌ Network from <50 samples (unstable)
- ❌ Reporting only edge weights without significance filtering
- ❌ Ignoring indirect associations (no conditional independence test)

## Implementation pointer
`skills/workflows/cooccurrence_network/run.py` (P1 stub)
