---
rule_id: _default_bootstrap
rule_type: cold_start_defaults
applies_to:
  modality: ALL
  study_design: ALL
  tissue_class: ALL
  task: ALL
evidence_cases: []
confidence: domain_knowledge
status: active
created: 2026-04-29
---

# Cold-start defaults — always loaded as fallback

When the retrieval library has < 5 cases relevant to a query, this rule provides
a safe default workflow. Rules below are derived from cross-modality consensus
in the omics field.

## Universal pre-flight
1. **Identify modality first.** scRNA / bulk / spatial / CITE / scATAC / multi-omics
   — every downstream choice (QC, normalization, DE, integration) differs.
2. **Identify study design.** paired | case_control | cohort | time_course |
   crispr_screen | reference. Statistics model follows.
3. **Identify batch source.** lane | plate | donor | sample_origin | platform.
   *batch_key is what you want to remove*; *biology_key* is what you want to keep.
   Setting biology in batch_key destroys signal (see rule `04-batch-vs-biology`).

## Universal sanity gates
- Counts must be raw integer for DE (NB / quasi-likelihood). TPM/FPKM rejected at entry.
- Doublet detection runs **before** normalization (scRNA / CITE-seq / scATAC).
- ≥ 2 markers per cell type for annotation; never single-marker.
- ≥ 2 methods for any high-stakes call (integration / deconvolution / CNV / annotation).
- All DE results report padj + LFC + (for scRNA) pseudobulk vs. cell-level.
- Library type, mapping rate, mito%, doublet rate logged per sample.

## Confidence policy
- Cold-start (n_lib < 5 cases relevant): label `cold_start`, recommend conservative
  defaults, request user confirmation before high-cost runs.
- n_lib ≥ 5 same modality: `low` → `medium` confidence depending on case quality.
- ≥ 3 evidence cases for a specific decision: `high`.

## Always-applicable anti-rules (any modality)
- ❌ Use TPM/FPKM in DE NB models.
- ❌ Set `batch_key = condition` when condition is the biology of interest.
- ❌ Skip doublet detection in single-cell modalities.
- ❌ Annotate clusters from a single marker.
- ❌ Trust single-tool output for high-stakes calls.
- ❌ Run the pipeline without writing `reproduce.sh` (provenance lock).
