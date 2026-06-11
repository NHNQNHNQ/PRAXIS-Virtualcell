---
rule_id: 03-bulk-de-priors
rule_type: case_distilled
applies_to:
  modality: bulk_RNA_seq
  study_design: [case_control_paired, cohort_subtype]
  tissue_class: ALL
  task: DE
evidence_cases:
  - case_id: omics-004-bulk-tcga-brca-deseq2
    page_hint: "What I actually did step 4 (~ batch + subtype)"
  - case_id: omics-010-bulk-airway-salmon-deseq2
    page_hint: "What I actually did step 6 (~ donor + dex)"
confidence: high
status: active
created: 2026-04-29
---

# Bulk RNA-seq DE priors — counts, design, shrinkage

## Statement
1. **Raw integer counts** required at DE entry. TPM/FPKM/CPM rejected (NB model
   requires raw counts).
2. **Batch must be in design formula** if any batch source exists (lane, plate,
   institution, sequencing run). TCGA: plate. Airway: donor (paired).
3. **Lowly-expressed pre-filter**: keep genes with `rowSums(counts >= 10) >=
   smallest_group_size`. More aggressive filters drop cell-type-specific genes
   in bulk-of-mixture tissue.
4. **LFC shrinkage default-on**: `lfcShrink(type='apeglm')` for ranking +
   downstream pathway analysis. Especially when smaller groups or low-expressed
   genes dominate.
5. **Salmon flags**: `--gcBias --seqBias --validateMappings --libType A`.
   `--libType A` auto-detects but **cross-check log mapping rate**; < 70% is a
   red flag.
6. **MultiQC is mandatory**, not optional: `--detect_adapter_for_pe`, fastp,
   salmon log; gates on adapter > 30% or mapping < 70%.
7. **Reference version lock**: FASTA + GTF + salmon-index from the same GENCODE
   / Ensembl release; provenance must record.

## DE diagnostic checks (post-fit)
- MA plot symmetric (asymmetric = batch / normalization issue).
- p-value histogram reverse-J shape (uniform / U = model misspecification).
- For pathway analysis: rank by Wald `stat`, not raw `log2FoldChange`.

## Why
- Case 010 (airway): omitting `donor` from `~ donor + dex` drops KLF15 LFC from
  5.8 → 2.3, raises padj 100x. Paired design must reflect.
- Case 004 (TCGA): plate batch explains > 10% of variance; not modeling pollutes.
- Case 010: GENCODE v44 index but v40 metadata → 5–10% transcripts "missing".
- Case 010: `--libType ISR` misspecified → quant-all-wrong without error.

## Cold-start fallback
- If batch source unknown: ask user, do not silently default to no batch.
- If counts type unknown: parse first 100 rows; if non-integer or any value
  in [0, 1) → reject and request raw counts.
