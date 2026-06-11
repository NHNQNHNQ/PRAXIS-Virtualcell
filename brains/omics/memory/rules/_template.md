---
rule_id: NN-short-name
rule_type: case_distilled | landscape | cold_start_defaults | anti_rule
applies_to:
  modality: [scRNA_seq | bulk_RNA_seq | spatial_transcriptomics | CITE_seq | scATAC_seq | bulk_multiomics | ALL]
  study_design: [case_control | cohort | reference | ALL]
  tissue_class: [PBMC | epithelial | brain | tumor | ALL]
  task: [QC | DE | integration | annotation | deconvolution | multimodal | ALL]
evidence_cases:
  - case_id: omics-NNN-...
    page_hint: "section name in case"
confidence: high | medium | low
status: active | deprecated | superseded_by:rule_id
created: YYYY-MM-DD
---

# Rule title

## Statement
One-sentence imperative form: "When X, do Y" / "Never do Z when W".

## Rationale
Why this rule exists — what failure mode it prevents.

## Evidence
- omics-XXX shows ... (concrete number/observation)
- omics-YYY confirms ...

## Applicability boundary
- Applies when: ...
- Does NOT apply when: ...
- Cold-start fallback if no case matches: ...

## Linked anti-rule
Pointer to the rule listing the failure mode this rule prevents.
