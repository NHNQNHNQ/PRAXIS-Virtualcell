---
rule_id: 10-multiomics-mofa
rule_type: case_distilled
applies_to:
  modality: bulk_multiomics
  study_design: cohort_factor_analysis
  tissue_class: ALL
  task: factor_analysis
evidence_cases:
  - case_id: omics-008-mofa-cll-multiomics
    page_hint: "What I actually did + Lessons"
confidence: high
status: active
created: 2026-04-29
---

# Multi-omics MOFA / factor-analysis priors

## Statement
1. **Per-modality independent normalization to comparable scale** (z-score or
   unit variance) before MOFA. Skipping leads to high-dimensional modality
   (e.g. methylation 450k) dominating low-dim ones (mutation 50).
2. **n_factors via elbow analysis**: variance-explained vs n_factors curve.
   Typical 5–15. Higher → "phantom factors" explain noise in 1 modality.
3. **Sparsity prior on (spike-and-slab)** is default for interpretability.
4. **Cross-modality validation**: a robust factor explains ≥ 5% variance in
   ≥ 2 modalities. Single-modality factors are technical or batch.
5. **Multi-seed reproducibility**: ≥ 10 seeds; keep factors with cosine
   similarity > 0.8 across runs.
6. **MOFA factor ≠ cluster**. It's a continuous latent; do not hard-discretize.

## DIABLO vs MOFA decision
- **MOFA (unsupervised)**: cohort discovery; "what drives heterogeneity?"
- **DIABLO (supervised)**: outcome known; "predict X using all modalities".

## Pre-flight rejects
- Different sample sets across modalities → align first; drop samples missing
  a modality (do NOT impute before MOFA — it has native missing support).
- Pre-PCA each modality before MOFA → defeats the purpose; MOFA is the
  dimensionality reduction.

## Cold-start fallback
- Unknown patient cohort heterogeneity: try `n_factors ∈ {5, 10, 15}`, pick
  by elbow; confidence: medium until factors are biologically grounded
  (e.g., factor 1 separates known IGHV M vs U for CLL — case 008 anchor).
