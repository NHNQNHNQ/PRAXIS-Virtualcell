---
skill_id: bulk_de_pipeline
status: ready
description: |
  Bulk RNA-seq DE end-to-end: counts → DESeq2 with batch + condition design →
  apeglm LFC shrinkage → MA plot + p-value histogram → fgsea Hallmark/Reactome.
  REJECTS TPM/FPKM/CPM at entry (rule 03).
inputs:
  counts_path: ".tsv / .csv / .rds / SummarizedExperiment with raw integer counts"
  coldata_path: "sample metadata (condition + batch + donor)"
  design_formula: "~ donor + condition  (or per scoping)"
  contrast: "[group, vs_group]"
  min_count_threshold: 10
  shrink_method: apeglm
  pathway_db: ["MSigDB_Hallmark", "Reactome"]
  random_seed: 0
outputs:
  de_table: "runs/<task_id>/de_table.tsv"
  pathway_table: "runs/<task_id>/pathway.tsv"
  figures:
    - "runs/<task_id>/figures/ma_plot.png"
    - "runs/<task_id>/figures/pvalue_histogram.png"
    - "runs/<task_id>/figures/volcano.png"
  metrics:
    n_de_genes_padj_05: int
    fraction_low_count_filtered: float
    ma_plot_symmetry: float       # |fraction up - fraction down| / total
    pvalue_histogram_shape: str   # "reverse_J" | "uniform" | "U_shape"
qc_check:
  must_emit: [n_de_genes_padj_05, ma_plot_symmetry, pvalue_histogram_shape]
  warn_if:
    pvalue_histogram_shape: "U_shape"  # model misspecification
    ma_plot_symmetry: "> 0.4"           # asymmetric → batch / norm issue
  reject_if:
    counts_appears_normalized: true     # rule 03 — TPM/FPKM rejection
evidence_cases:
  - omics-004-bulk-tcga-brca-deseq2
  - omics-010-bulk-airway-salmon-deseq2
related_rules:
  - 03-bulk-de-priors
  - 04-batch-vs-biology
  - 11-anti-rules-failure-modes
  - 12-reproducibility-and-provenance
---

# bulk_de_pipeline

## Purpose
Bulk DE the right way: raw counts + DESeq2 + LFC shrinkage + sanity-checked
diagnostics. Defends against three top failure modes (rule 11):
- TPM/FPKM in NB model → rejected at entry
- Missing batch in design → rejected (rule 04)
- No LFC shrinkage → silent ranking instability

## Algorithm
1. Load counts. **Verify integer counts** — reject if any value in [0, 1) or
   non-integer (rule 03 / rule 11).
2. Load coldata; verify all samples in counts matched.
3. Construct DESeqDataSet with the given `design_formula`. The Reviewer
   enforces batch covariate inclusion.
4. Pre-filter `rowSums(counts >= min_count_threshold) >= smallest_group_size`.
5. Run `DESeq()`; extract results for the `contrast`.
6. **lfcShrink with apeglm** (rule 03 default).
7. Diagnostics:
   - MA plot symmetry: |frac_up - frac_down| / total at padj < 0.05
   - p-value histogram shape: classify as reverse_J (good) / uniform (no signal)
     / U-shape (model misspecified)
8. Pathway:
   - Rank genes by Wald `stat` (rule 03: stat more stable than LFC).
   - Run fgsea on each pathway_db.
9. Sanity anchors per dataset:
   - airway: DUSP1 in dex_up top 50 (case 010)
   - TCGA basal vs LumA: ESR1 down + KRT5 up (case 004)

## Implementation status
**Stub.**

## Reference: case 010
> design = ~ donor + dex — **donor 必须建模**（配对设计）；省略后 KLF15 LFC 5.8 → 2.3。
> Salmon `--gcBias --seqBias --validateMappings --libType A` 必加。
> MultiQC 聚合是 mandatory step；mapping rate < 70% 阻塞 pipeline。

## 输出契约

```json
{
  "skill_id": "bulk_de_pipeline",
  "matrix_path": "",
  "n_cells_post_qc": 0,
  "cluster_sizes": {},
  "marker_genes_per_cluster": {},
  "umap_png": "",
  "diagnostics": {
    "brain": "omics",
    "archetype": "omics_scrna"
  }
}
```
