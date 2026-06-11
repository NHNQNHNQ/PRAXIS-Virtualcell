---
rule_id: 02-scrna-qc-priors
rule_type: case_distilled
applies_to:
  modality: [scRNA_seq, CITE_seq]
  study_design: ALL
  tissue_class: ALL
  task: QC
evidence_cases:
  - case_id: omics-001-scrna-pbmc10k-canonical
    page_hint: "What I actually did step 2 (mito 15%)"
  - case_id: omics-003-scrna-tabula-muris-multitech
    page_hint: "Lessons 2 (organ-specific QC table)"
  - case_id: omics-005-scrna-tumor-malignant-id
    page_hint: "What I actually did step 1 (initial QC)"
  - case_id: omics-013-young-2020-ambient-rna-neglect-failure
    page_hint: "Ambient RNA correction (SoupX/CellBender) is mandatory in solid tissue scRNA"
  - case_id: omics-015-pijuan-sala-2019-gastrulation-time-course
    page_hint: "Per-stage QC thresholds (cell size / metabolism shift with stage)"
confidence: high
status: active
created: 2026-04-29
---

# scRNA QC priors — organ-specific thresholds + doublet ordering

## Statement
1. mito% threshold is organ-specific. Do not use a flat 5% for all tissues.
2. Doublet detection runs on raw counts **before** normalization, before HVG.
3. nFeature ≥ 200 + nCount ≥ 500 is a baseline; tighten per tissue.

## Organ-specific mito% upper bounds
| Tissue / cell class | mito% upper | Source case |
|---|---|---|
| CNS (neuron) | 5% | Tabula Muris Lessons (case 003) |
| PBMC immune mono activated | 15% | PBMC10k step 2 (case 001) |
| Hepatocyte / kidney tubule | 25% | Tabula Muris Lessons (case 003) |
| Cardiomyocyte (acute stress) | 35% | Tabula Muris Lessons (case 003) |

## Doublet detection ordering (hard order)
1. Read raw counts.
2. Compute QC metrics; mark cells failing per-tissue thresholds.
3. **Run scrublet (or DoubletFinder) on raw counts** with
   `expected_doublet_rate = 0.075 * (n_loaded / 10000)`.
4. Drop doublets and QC-failures BEFORE `normalize_total + log1p`.
5. Then HVG, then PCA / Harmony / scVI, then clustering.

## Why
- mito flat 5% on PBMC clears ~30% of real mono (case 001).
- Doublet on normalized counts: HVG inherits doublet artifact, propagates to
  cluster boundaries (case 001 anti-rule).
- Tissue-aware doublet rate: liver hepatocytes are naturally bi-nucleate so
  doublet detector falsely flags real cells (case 003 failure mode).

## Cold-start fallback (no tissue match)
- Use mito% ≤ 15% as a generic upper bound.
- nFeature ≥ 200 + nCount ≥ 500.
- Doublet rate prior 7.5% per 10k loaded cells.
- Flag the entire QC step `confidence: low`; ask user to confirm tissue type.
