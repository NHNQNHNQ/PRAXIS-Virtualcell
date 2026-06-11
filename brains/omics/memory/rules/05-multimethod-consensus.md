---
rule_id: 05-multimethod-consensus
rule_type: landscape
applies_to:
  modality: [scRNA_seq, CITE_seq, spatial_transcriptomics, scATAC_seq, bulk_multiomics]
  study_design: ALL
  tissue_class: ALL
  task: [integration, annotation, deconvolution, CNV, doublet]
evidence_cases:
  - case_id: omics-002-scrna-kang-ifnb-integration
    page_hint: "Step 3 (Harmony + scVI + BBKNN)"
  - case_id: omics-005-scrna-tumor-malignant-id
    page_hint: "Step 4 (inferCNV + CopyKAT consensus)"
  - case_id: omics-006-spatial-slideseq-cerebellum
    page_hint: "Step 5 (cell2location + Tangram)"
  - case_id: omics-007-citeseq-bmnc-wnn
    page_hint: "RNA marker × ADT marker double-source annotation"
  - case_id: omics-001-scrna-pbmc10k-canonical
    page_hint: "Step 8 (CellTypist + manual marker)"
confidence: high
status: active
created: 2026-04-29
---

# No single-tool finals — multi-method consensus

## Statement
For high-stakes calls (integration, deconvolution, CNV, doublet, cell-type
annotation), run ≥ 2 methods and take the consensus. Single-tool output is
labeled `confidence: low` and never promoted to a final claim.

## Per-task minimum method sets
| Task | Required ≥ 2 of |
|---|---|
| **scRNA integration** | Harmony, scVI, scANVI, BBKNN, fastMNN |
| **scRNA annotation** | CellTypist + manual marker, Azimuth, SingleR, scType |
| **scRNA doublet** | scrublet, DoubletFinder (cells), or RNA + ADT joint (CITE) |
| **CNV (tumor scRNA)** | inferCNV, CopyKAT, Numbat |
| **Spatial deconvolution** | cell2location, Tangram, RCTD |
| **Multi-modal integration** | Seurat WNN, totalVI, MOFA+ (sample-level only), MultiVI |

## Consensus rules
1. Methods agree → `confidence: high`. Move on.
2. Methods disagree → `confidence: medium` and route to `_review/` for human;
   capture both calls in provenance.
3. Single method only → `confidence: low`; report explicitly.

## Cold-start fallback
- < 5 cases: still required; if user lacks GPU for scVI, fall back to Harmony +
  Seurat-CCA. Never a single method.
- For doublet detection in scATAC, the simulation method (ArchR-builtin, not
  scrublet) is the single canonical choice; pair with TSS-enrichment outlier
  flagging.

## Linked failure modes
- inferCNV alone: 5–15% false positive on regenerating epithelium (case 005).
- CopyKAT alone: false negative on low-CNV-burden tumors (case 005).
- Single deconvolution (cell2location alone): boundary spots get
  pseudo-mixtures from algorithm uncertainty (case 006).
- Single annotator (CellTypist alone): brain tissue accuracy < 60% (case 003).
