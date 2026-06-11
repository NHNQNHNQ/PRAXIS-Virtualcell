---
case_id: NEG-LINEAR-IMC
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 6
task: imaging_mass_cytometry_multiplex
image_modality: IMC
sample_dimension: 2d_tissue
cell_type: tissue_generic
assay_format: slide
channel_count: 30
dataset_accession: null
antibodies_rrid: []
software_versions:
  numpy: ">=1.20"
tools: [linear intensity scaling, no arcsinh, no log, raw IMC counts]
key_paper_doi: 10.1038/nmeth.2869
provenance:
  source_type: literature
  doi: 10.1038/nmeth.2869
  citation: "Giesen C et al. Highly multiplexed imaging of tumor tissues with subcellular resolution by mass cytometry. Nat Methods. 2014;11(4):417-422. (introduces IMC; documents 0-10000 ADU dynamic range; arcsinh recommended downstream)"
  extracted_at: 2026-05-02
  extraction_confidence: high
  unverified_details: []
tags: [anti_pattern, linear_imc, no_arcsinh, dynamic_range, mass_cytometry]
causal_tag: causal
---

# NEG-LINEAR-IMC — Linear intensity scaling for IMC / CODEX (no arcsinh)

## What this NEG- case records
**Anti-pattern**: feeding raw IMC (Hyperion mass-cytometry) per-cell intensity values directly into downstream cell-typing / clustering / Z-score normalization without first applying `arcsinh(x / cofactor)` (Bodenmiller convention cofactor=5).

## Where the failure mode was published
Giesen 2014 Nat Methods — the canonical IMC introduction paper — documents the 4-order-of-magnitude dynamic range typical for IMC ([0, 10 000] ADU per channel) and recommends arcsinh transform downstream. The Bodenmiller lab's Steinbock pipeline encodes this as a default step.

## Mechanism — why it fails
- IMC dynamic range often spans 0 to 10 000 ADU per marker channel.
- Raw distribution: median typically 5-50 ADU (background) with bright tail at 1 000-10 000 ADU (positive cells).
- Linear z-score on this distribution: bright outlier cells dominate; positive vs background discrimination fails because mean is dragged towards bright outliers.
- arcsinh(x / 5) compresses upper tail by ~400× while preserving low-signal resolution → cell-typing thresholds become stable.

## Concrete numerics (from PRAXIS-Cell cell-009 validated_run)
- Raw IMC range [0, 30 000] ADU after hot-pixel removal
- After arcsinh(/ 5): range [0, 7.0] (compression 402×)
- Cell-typing accuracy on 4-class T/B/Epi/Stromal: **100 %** with arcsinh; with linear input + naive Z, expected accuracy < 70 % per Giesen 2014 anecdotal report

## ★ Reviewer hard-stop
Any IMC or CODEX design plan that scales per-cell intensity linearly (no arcsinh / log transform) before downstream typing or clustering must be vetoed. Required: arcsinh with cofactor=5 (IMC) or cofactor in [3, 10] (CODEX).

## Maps to anti-rule
**anti-rule #6**: Linear intensity for IMC / CODEX (no arcsinh) is forbidden. Required: arcsinh transform with cofactor=5.

## Anti-retrieval keywords
linear imc, no arcsinh, raw imc counts, raw codex, linear z-score on imc, no log transform
