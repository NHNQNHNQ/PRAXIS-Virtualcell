---
case_id: omics-NNN-{modality}-{shorthand}        # kebab-case
schema_version: 1
modality: scRNA_seq | bulk_RNA_seq | spatial_transcriptomics | CITE_seq | scATAC_seq | bulk_multiomics | proteomics | metabolomics
study: "Author et al YEAR, study title"          # human-readable citation
public_accession: GSE12345 | TCGA-PROJ | ICGC-...| ENA-... | 10x_demo
doi: 10.xxxx/xxxxx                                # CrossRef-verified
organism: Homo sapiens | Mus musculus | ...      # NCBI scientific name
tissue: "tissue or list[tissue]"
study_design: case_control_paired | cohort | reference | time_course | crispr_screen | cohort_atlas | cohort_subtype | cohort_factor_analysis
assay_subtype: 10x_chromium_v3 | smartseq2 | slide_seq_v2 | cite_seq_25abs | scATAC_fragments | bulk_paired_short_read | bulk_multiomics_4_views | ...
cell_type_focus: [list of cell types or focus tags]
tools:                                            # principal tools + version
  - Scanpy 1.10
  - scvi-tools 1.1
method_choice: [tool/method tags used]            # for retrieval channel
status: validated | proposed | failed | partial
validated: true                                   # praxis QA flag
source: praxis_seed | distilled_from_paper | inhouse
provenance:
  source_type: literature | inhouse | demo
  doi: 10.xxxx/xxxxx
  extracted_at: YYYY-MM-DD
tags: [optional free-form tags]
---

# {Title — modality + key finding}

## Background
- Why this study matters; known baselines/answers (used as sanity-check anchors).
- Sample size, design summary.

## What I actually did
1. Numbered decision steps.
2. Tool name + version + key parameters at each step.
3. Cite "why this parameter" instead of just "I used X".

## ★ 排除的样本/基因/细胞 (mandatory; QA enforced)
- QC-failed samples: thresholds + rationale (mito% / nFeature / total_counts; ≥ 2 markers).
- Lowly-expressed genes filtered: criterion + threshold.
- Doublet cells removed: detection method + expected rate + tissue prior.
- Even if "未报道" / "not reported", state explicitly — empty section is rejected by QA.

## ★ 失败的分析路径 (mandatory; QA enforced)
- Methods tried and abandoned, with reason (e.g. Wilcoxon → MAST + random effect because pseudoreplication).
- Reviewer-rejected interpretations.
- Common field-observed failure modes for this modality/tissue.
- Even "未报道" must be explicit.

## ★ 方法选择决策链 (mandatory)
- DESeq2 vs edgeR — why one not the other.
- Harmony vs scVI vs BBKNN — choice rationale (size, batch complexity, GPU).
- batch_key definition — what is "the variable to remove" vs "biology to keep".
- HVG count, n_PCs, Leiden resolution — and why these defaults differ from the case.

## ★ QC sanity check on known answers (mandatory)
- airway → DUSP1 in dex_up top 50.
- Kang IFN-β → ISG15 stim/ctrl log2FC ≥ 2.5.
- PBMC10k → mono fraction 25–35%.
- TCGA-BRCA basal vs LumA → ESR1 down, KRT5 up.
- Slide-seq cerebellum → Calb1 spatially restricted to Purkinje layer.
- For a new case: pick a published answer the pipeline must reproduce.

## Lessons → seeds for rules
- 1–5 generalizable rules this case validates or refines.
- These rules feed into `memory/rules/*.md` after promotion (≥3 evidence cases).

## Provenance pointers
- raw_data: data/_fetch_<case_id>.sh
- intermediate: runs/<task_id>/
- figures: runs/<task_id>/figures/
- reproduce: runs/<task_id>/reproduce.sh
