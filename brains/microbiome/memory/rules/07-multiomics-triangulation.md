---
rule_id: 07-multiomics-triangulation
rule_type: case_distilled
applies_to: {microbiome_task: [multiomics], sample_type: ALL}
confidence: high
evidence_cases: [microbiome-007-host-microbe-multiomics]
schema_version: 2
---

# Rule 07: Multi-omics integration uses MOFA + per-omics + mediation

## Statement
Host-microbe multi-omics integration (16S/shotgun + host RNA-seq + metabolomics) requires three parallel methods: (1) unsupervised factor analysis (MOFA+) on jointly normalized matrices, (2) per-omics statistical association (MaAsLin2 / mixOmics), (3) mediation analysis (MIMOSA, NetCoMi) to identify metabolite intermediaries. Each method has known failure modes; agreement across at least two is required for biological claims.

## Why
Inter-individual variability in microbiome data exceeds inter-condition variability for most diseases (Schirmer et al. 2019, 10.1126/science.aau5812). A single integration method captures only one form of association — MOFA+ finds shared latent factors but misses small-effect-size associations; MaAsLin2 finds significant pairs but cannot disentangle direct from indirect effects; MIMOSA explicitly models metabolite mediation. Triangulating reduces false positives.

## How to apply
- Skill `multiomics_integration/run.py` (P1 stub) coordinates the three methods.
- Required preprocessing: per-omics CLR / log transform; common-sample subset across omics layers.
- Time-lag effects are common (microbe→metabolite→host with hours-to-days delay) — longitudinal sampling preferred for causal claims.

## Evidence
- microbiome-007: explicit anti-pattern — "Per-omics independent integration" listed as failure.

## Anti-patterns
- ❌ Concatenating raw matrices into one PCA
- ❌ Single-method integration without cross-validation
- ❌ Claiming causality without mediation or longitudinal evidence
- ❌ Ignoring batch effects across omics platforms

## Implementation pointer
`skills/workflows/multiomics_integration/run.py` (P1 stub)
