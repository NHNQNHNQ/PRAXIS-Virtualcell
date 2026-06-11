---
rule_id: 04-batch-vs-biology
rule_type: case_distilled
applies_to:
  modality: [scRNA_seq, CITE_seq, bulk_RNA_seq, spatial_transcriptomics, scATAC_seq, bulk_multiomics]
  study_design: ALL
  tissue_class: ALL
  task: integration
evidence_cases:
  - case_id: omics-002-scrna-kang-ifnb-integration
    page_hint: "What I actually did step 4 (batch_key=donor not condition)"
  - case_id: omics-003-scrna-tabula-muris-multitech
    page_hint: "Step 3 (scVI batch_key=platform)"
  - case_id: omics-005-scrna-tumor-malignant-id
    page_hint: "Step 6 (Harmony batch=patient)"
  - case_id: omics-012-luecken-2022-integration-overcorrection-failure
    page_hint: "scIB benchmark — over-correction failures from putting biology in batch_key"
  - case_id: omics-015-pijuan-sala-2019-gastrulation-time-course
    page_hint: "Stage is biology not batch; see rule 13 for time-course extension"
  - case_id: omics-026-tung-2017-scrna-batch-effect-classic
    page_hint: "C1 capture order dominates PC1; balanced/blocked design + ERCC + per-PC variance breakdown"
confidence: high
status: active
created: 2026-04-29
---

# Batch-vs-biology decision tree (one of the most common blunders)

## Statement
**`batch_key` = what you want to remove**, NOT what you want to study.
The variable that encodes biology of interest must NEVER be in `batch_key`.

## Decision tree
```
What is the user's question?
├─ "How does X (= condition / cell type / tumor subclone) differ from Y?"
│    → biology_key = X; batch_key ≠ X.
├─ "What is the cell-type composition of tissue Z?"
│    → biology_key = cell_type; batch_key = donor + lane + sample_origin.
└─ "Atlas — across many tissues / platforms"
     → biology_key = (tissue, cell_type); batch_key = platform + donor.
```

## Common right vs wrong batch_key
| Question | RIGHT batch_key | WRONG batch_key |
|---|---|---|
| ctrl vs IFN-β response (case 002) | donor | condition (ablates IFN signal) |
| Subtype DE in TCGA (case 004) | plate / institution | subtype (ablates the comparison) |
| Cross-platform atlas (case 003) | platform + donor | tissue (ablates inter-tissue biology) |
| Tumor vs normal (case 005) | patient | sample_origin (tumor/normal) |
| Multi-organ atlas (case 003) | platform | organ (ablates organ identity) |

## Quantitative quality check
Two metrics, both required:
- **kBET** / iLISI / mixing entropy: batch is well-mixed (high).
- **Biology preserved**: e.g. IFN ISG signature `log2FC stim/ctrl ≥ 2.5` (case 002).
  Sub-1.0 is over-correction.
- Score: PASS only if both pass; FAIL if either fails.

## Why this rule keeps appearing
LLMs and junior analysts often assume "batch = anything that varies between
samples". Conditions vary between samples too — but they are biology, not noise.
**The right framing is: batch is what you want gone; biology is what you want
amplified.**

## Cold-start fallback
- If unsure: ask user explicitly which variable is the question and which is
  the unwanted nuisance. Do NOT guess.
- Refuse to run integration with `batch_key = condition` unless user provides
  written rationale; record the override in provenance.
