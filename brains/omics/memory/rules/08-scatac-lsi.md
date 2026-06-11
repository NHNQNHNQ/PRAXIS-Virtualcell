---
rule_id: 08-scatac-lsi
rule_type: case_distilled
applies_to:
  modality: scATAC_seq
  study_design: ALL
  tissue_class: ALL
  task: [QC, dimensionality_reduction, peak_calling, motif_analysis]
evidence_cases:
  - case_id: omics-009-scatac-buenrostro-hematopoiesis
    page_hint: "Step 4 (LSI not PCA); Step 6 (iterative peak calling)"
confidence: high
status: active
created: 2026-04-29
---

# scATAC-seq priors — LSI, iterative peaks, motif-level signal

## Statement
1. **LSI not PCA** for scATAC dim-reduction (binary / sparse counts);
   **drop the first LSI component** (correlated with sequencing depth).
2. **Iterative peak calling**: tile → LSI → cluster → MACS3 per cluster →
   union peak set → re-LSI on cell × peak. Single-pass peak calling on bulk
   peaks misses cell-type-specific peaks.
3. **QC = TSS enrichment + nFrag + fragment-size periodicity**, NOT mito%
   (nuclear prep, no mito reads).
4. **Doublet detection by simulation**: ArchR or AMULET, not scrublet (different
   generative model).
5. **Analysis at motif level via chromVAR**, not per-peak DE: per-peak signal
   is too sparse for stable per-cell statistics.

## Threshold defaults
| Metric | Hematopoietic / immune | Brain (more permissive) |
|---|---|---|
| TSS enrichment | ≥ 4 | ≥ 4 |
| nFrag | ≥ 1000 | ≥ 500 (HSPC scenarios) |
| Doublet score | ArchR default | ArchR default |

## chromVAR motif analysis
- Background-correct for GC content (motif activity bias).
- Read-out as bias-corrected deviation z-scores.
- Validate with known TF lineage drivers: GATA1↑ erythroid, PU.1↑ myeloid (case 009).

## Multi-omic (RNA + ATAC same cell)
- Use Signac / MultiVI / WNN; do NOT process RNA and ATAC independently.
- Cell barcodes must match exactly.

## Cold-start fallback
- Unknown tissue / organism: use TSS ≥ 4, nFrag ≥ 500, ArchR default doublet,
  iterative peak calling with default tile size 500bp. Confidence: medium until
  validated against a known marker (e.g. GATA1 in erythroid).
