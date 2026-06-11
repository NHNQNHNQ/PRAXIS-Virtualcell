---
rule_id: 12-reproducibility-and-provenance
rule_type: landscape
applies_to:
  modality: ALL
  study_design: ALL
  tissue_class: ALL
  task: ALL
evidence_cases:
  - case_id: omics-010-bulk-airway-salmon-deseq2
    page_hint: "Lessons → reference consistency"
  - case_id: omics-008-mofa-cll-multiomics
    page_hint: "Lessons → multi-seed reproducibility"
confidence: high
status: active
created: 2026-04-29
---

# Reproducibility and provenance — every run must be auditable

## Statement
Every run produces:
1. `reproduce.sh` — the exact command sequence, with pinned versions.
2. `runs/<task_id>/skill_log.json` — per-step tool, version, parameters,
   stderr summary, runtime_sec, status.
3. Reference fingerprint: FASTA / GTF / index / annotation versions all logged.
4. Random seeds explicit at each stochastic step (HVG, scVI, Harmony, MOFA, UMAP).

## Required provenance per analysis stage
- **Counts ingestion**: counts type (raw / TPM / FPKM), source (recount3 / GDC /
  10x / CellRanger version), reference release.
- **Normalization**: method, target_sum / scale_factor, scaled or not.
- **HVG**: flavor (seurat_v3 / cell_ranger / dispersion), n_top_genes.
- **Dim-reduction**: method (PCA / LSI / scVI), n_components, seed.
- **Integration**: method, batch_key, biology_key, hyperparameters, post-integration metric (kBET / iLISI).
- **Clustering**: method, resolution, seed.
- **DE**: method (DESeq2 / edgeR / limma-voom / MAST / Wilcoxon), design formula, pseudobulk-or-not, shrinkage.
- **Pathway**: database version (MSigDB v2024.1.Hs / Reactome v90 / KEGG release).

## Reference version lock
- FASTA + GTF + salmon index from same GENCODE / Ensembl release.
- Cellranger reference release.
- ArchR genome reference (BSgenome.Hsapiens.UCSC.hg38.masked, version pinned).

## Multi-seed for stochastic methods
- MOFA, scVI, UMAP: ≥ 3 seeds; report sensitivity in summary.
- For "is this factor robust?" questions: MOFA ≥ 10 seeds, cosine similarity > 0.8.

## Cold-start fallback
- Unknown reference release: ask user; do not silently use latest.
- Unknown random seed: emit `seed: 0` and explicitly log.
