---
rule_id: 01-cross-modality-priors
rule_type: landscape
applies_to:
  modality: ALL
  study_design: ALL
  tissue_class: ALL
  task: ALL
evidence_cases:
  - case_id: omics-001-scrna-pbmc10k-canonical
    page_hint: "Lessons → seeds for rules"
  - case_id: omics-002-scrna-kang-ifnb-integration
    page_hint: "What I actually did → step 4 (batch_key choice)"
  - case_id: omics-003-scrna-tabula-muris-multitech
    page_hint: "Lessons → cross-platform default not integrate"
  - case_id: omics-004-bulk-tcga-brca-deseq2
    page_hint: "Lessons → batch must be modeled"
  - case_id: omics-010-bulk-airway-salmon-deseq2
    page_hint: "Lessons → paired design, MultiQC, ref consistency"
confidence: high
status: active
created: 2026-04-29
---

# Cross-modality priors — the 8 universal principles

Distilled from all 10 reference cases. Apply in every Scoping stage.

## 1. Modality-aware
Every decision starts with "what modality?" — QC / normalization / DE /
integration are entirely different across scRNA, bulk, spatial, CITE, scATAC,
multi-omics. Don't reuse a scRNA pipeline on scATAC. Evidence: cases 001 vs 009
(LSI not PCA), 010 vs 002 (DESeq2 NB not Wilcoxon).

## 2. Tissue-aware
QC thresholds, doublet rate prior, reference choice depend on tissue. Mito% is
**organ-specific**: ~5% (CNS / hepatocyte stress baseline) / ~15% (PBMC, immune
mono) / ~25% (liver, kidney) / up to ~35% (cardio acutely stressed). Evidence:
cases 001, 003, 005.

## 3. Design-first
Before any analysis, identify study_design (paired / case_control / cohort /
time_course / crispr_screen / reference). The statistical model follows. A
paired bulk RNA-seq with `~ condition` instead of `~ donor + condition` loses
half the power. Evidence: case 010 (KLF15 LFC dropped 5.8 → 2.3 when donor
omitted), case 004 (TCGA plate batch in design).

## 4. Provenance everywhere
Each step logs tool + version + parameter + seed. Output a `reproduce.sh` for
every task. Reference version (FASTA + GTF + index) must be the same across the
pipeline. Evidence: case 010 (GENCODE v44 vs v40 mismatch).

## 5. Sanity check on known answers
The pipeline must reproduce a known result for the dataset before we trust new
results. Anchors per dataset:
- airway → DUSP1 in dex_up top 50 (case 010)
- Kang IFN-β → ISG15 stim/ctrl log2FC ≥ 2.5 (case 002)
- PBMC10k → mono fraction 25–35% (case 001)
- TCGA-BRCA basal vs LumA → ESR1 down, KRT5 up (case 004)
- Slide-seq cerebellum → Calb1 spatially restricted to Purkinje layer (case 006)
- CLL multi-omics → factor 1 separates IGHV M vs U (case 008)

## 6. No single-tool finals
Integration / deconvolution / CNV / annotation must use ≥ 2 methods and the
final claim is the consensus. Evidence: case 002 (Harmony + scVI + BBKNN), case
005 (inferCNV + CopyKAT), case 006 (cell2location + Tangram), case 007 (RNA +
ADT marker double-source), case 001 (CellTypist + manual marker check).

## 7. Pseudobulk-first for scRNA DE
Unless cell-level effects are the research goal, DE in scRNA defaults to
pseudobulk + DESeq2 / edgeR, OR MAST + random-effect. Wilcoxon on cell as
sample is pseudoreplication and inflates p-values. Evidence: cases 002, 005,
007.

## 8. Confidence label per recommendation
Every cell-type call gets a confidence; every DE result gets padj + LFC +
(pseudobulk vs. cell-level) tag. Excluded items get a reason, not silence.

## How to apply
- In Scoping stage: walk through points 1–3 explicitly.
- In Design stage: enforce points 6–7 in `excluded_methods` and `pipeline`
  blocks.
- In Reporting stage: enforce points 4, 5, 8 in `summary`, `validation`,
  `confidence_per_finding`.
