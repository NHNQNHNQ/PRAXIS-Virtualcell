---
rule_id: 05-compositional-aware-da
rule_type: case_distilled
applies_to: {microbiome_task: [da_analysis, multiomics], sample_type: ALL}
confidence: high
evidence_cases: [microbiome-005-ancombc-da, microbiome-007-host-microbe-multiomics]
schema_version: 2
---

# Rule 05: Use compositional-aware DA methods (ANCOM-BC2 / MaAsLin2 / LinDA)

## Statement
Differential-abundance testing on microbiome count tables MUST use a compositional-aware method (ANCOM-BC2, MaAsLin2, LinDA, ALDEx2) — never raw t-test, Wilcoxon, or DESeq2 directly. Run ≥2 methods and require consensus for "high confidence" calls.

## Why
Microbiome data is **compositional** (sums to 1 by construction): when one taxon increases, others appear to decrease. Standard parametric tests (t-test, DESeq2) violate this assumption and inflate false positive rates dramatically (Lin & Peddada 2020, 10.1038/s41467-020-17041-7). Compositional-aware methods either model the bias correction (ANCOM-BC2) or use log-ratio transforms.

## How to apply
- Reviewer gate `MICROBIOME_REVIEW_TTEST_RAW_COUNT`: trigger when `differential_abundance.method ∈ {t_test, wilcoxon, deseq2}` AND `compositional_transform_applied=false`.
- Skill `da_compositional/run.py` enforces ≥2-method execution by default; consensus column flags taxa significant in ≥2 methods.
- Always report effect size (log fold change) AND adjusted p-value, not just p.

## Evidence
- microbiome-005: full failure-mode chain — "t-test / Wilcoxon on raw count" → false positives.
- microbiome-007: multiomics integration uses MaAsLin2 + MOFA — compositional-aware throughout.

## Anti-patterns
- ❌ scipy.stats.ttest_ind on raw counts
- ❌ DESeq2 on raw microbiome counts (assumptions violated)
- ❌ Single-method DA without cross-method consensus
- ❌ Reporting p-values without effect size

## Implementation pointer
`skills/workflows/da_compositional/run.py`
