---
rule_id: 06-pseudobulk-de-scrna
rule_type: case_distilled
applies_to:
  modality: [scRNA_seq, CITE_seq]
  study_design: [case_control_paired, cohort, time_course]
  tissue_class: ALL
  task: DE
evidence_cases:
  - case_id: omics-002-scrna-kang-ifnb-integration
    page_hint: "Step 5 (MAST + random effect, not Wilcoxon)"
  - case_id: omics-005-scrna-tumor-malignant-id
    page_hint: "★失败 (subcluster DE without random effect)"
  - case_id: omics-007-citeseq-bmnc-wnn
    page_hint: "ADT-aware DE warning"
confidence: high
status: active
created: 2026-04-29
---

# Pseudobulk-first for scRNA differential expression

## Statement
**Default DE for scRNA**: pseudobulk per (donor, condition, cell_type) →
DESeq2 / edgeR. Alternative: MAST with `donor` as random effect.
**Never naive Wilcoxon on cells**: 8 donors with 1k cells each is NOT 8000
independent observations. This is pseudoreplication — p-values are wildly
optimistic.

## Decision tree
```
Question: "Is gene X differentially expressed between conditions in cell type C?"
├─ Donor / sample replicates exist (n ≥ 3 per condition)?
│    ├─ YES → pseudobulk + DESeq2
│    └─ NO → MAST(condition + (1|donor)) but report power explicitly
└─ Question: "Is X differential between two cells / states (no donor concept)?"
     → MAST or Wilcoxon on cells is OK; this is genuinely cell-level.
```

## Pseudobulk recipe
1. Group cells by (donor, condition, cell_type).
2. Sum raw counts per group → matrix `n_groups × n_genes`.
3. Construct DESeq2 / edgeR with `~ donor + condition` (or `~ subject + condition` for paired).
4. Apply LFC shrinkage (`apeglm`).
5. Multiple-testing correct across genes within cell type, then optionally
   global FDR across all (gene, cell_type) tests.

## When it's safe to skip pseudobulk
- Cell-state mapping where the unit of inference is the cell, not the donor
  (e.g. "What genes vary along pseudotime within this trajectory?").
- Single-donor pilot (no biological replication) — explicitly tag results
  `confidence: low`, not generalizable.

## Why
- Case 002 (Kang IFN-β): 8 donors. naive Wilcoxon on cells reports nominal
  p < 1e-300 for many genes; pseudobulk DESeq2 yields realistic distributions.
  ISG15 stim/ctrl LFC ≥ 2.5 still robust; weakly DE genes are filtered out.
- Case 007 (CITE-seq BMNC): RNA-protein discordance is real biology, not noise;
  DE on protein needs distinct stats (e.g. Wilcoxon on CLR) but still requires
  donor as random effect.

## Cold-start fallback
- If donor count < 3 per group → flag `cohort_too_small`; recommend
  MAST + (1|donor) and degrade confidence to `low`.
- Always report the chosen method (pseudobulk vs MAST vs Wilcoxon) in the
  output `method_choice` field of the DE table.
