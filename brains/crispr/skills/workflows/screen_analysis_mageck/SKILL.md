---
skill_id: screen_analysis_mageck
description: Pooled CRISPR screen analysis — library QC (Gini < 0.3 + lorenz), MAGeCK count + MLE β-score + RRA p-value, ≥3 sgRNA consistent direction, DepMap CKE/NE benchmark, pathway enrichment (fgsea / MSigDB), time-series.
inputs:
  - counts: TSV path (sgRNA × sample matrix) OR fastq dir + library design
  - design: JSON {samples, conditions, replicates, control_sgRNAs}
  - library: Brunello / GeCKO / TKOv3
outputs:
  - library_qc: gini_coefficient, lorenz_curve_data, MOI_estimate
  - mageck_results: hit gene table (MLE β + RRA p + LFC)
  - depmap_benchmark: CKE enrichment, NE flatness check
  - pathway_enrichment: top GO/Reactome terms
  - flags: bottleneck warnings, single-time-point warnings
sanity_check: synthetic K562 essential screen — DepMap CKE genes enriched dropout (avg LFC < -1), NE genes flat (|LFC| < 0.3), Gini < 0.3
reference_case: crispr-006-mageck-screen-analysis
---

## Protocol

1. Library QC: Gini coefficient on day-0 counts. Gini > 0.3 → library biased → block hit calling.
2. MOI from cell coverage estimate (target 0.3; ≥ 200x cells per sgRNA).
3. MAGeCK count → normalize (control sgRNAs preferred over median).
4. MLE for β-score (effect size); RRA for p-value.
5. Hit threshold: |LFC| > 0.5, p < 0.001, ≥ 3 sgRNAs consistent direction.
6. DepMap CKE / NE benchmark — CKE should drop out (mean LFC < -1), NE flat.
7. Pathway enrichment with fgsea + MSigDB Hallmark / Reactome.

## Don't

- ❌ Hit-call with Gini > 0.3 library (biased counts).
- ❌ Single time point screen (need day-0 + day-14+).
- ❌ Single biological replicate (no MLE).
- ❌ Skip control sgRNA normalization.

## 输出契约

```json
{
  "skill_id": "screen_analysis_mageck",
  "n_guides": 0,
  "guides_csv": "",
  "best_guide": {
    "seq": "",
    "cfd_score": 0.0,
    "mit_score": 0.0
  },
  "diagnostics": {
    "brain": "crispr",
    "archetype": "crispr"
  }
}
```
