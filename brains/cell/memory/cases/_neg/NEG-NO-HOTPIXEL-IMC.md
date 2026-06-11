---
case_id: NEG-NO-HOTPIXEL-IMC
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 8
task: imaging_mass_cytometry_multiplex
image_modality: IMC
sample_dimension: 2d_tissue
cell_type: tissue_generic
assay_format: slide
channel_count: 30
dataset_accession: null
antibodies_rrid: []
software_versions:
  steinbock: ">=0.16"
tools: [no hot-pixel filter, raw IMC counts, no median filter, no Steinbock --filter-pixels]
key_paper_doi: 10.1038/nmeth.2869
provenance:
  source_type: literature
  doi: 10.1038/nmeth.2869
  citation: "Giesen C et al. Highly multiplexed imaging of tumor tissues with subcellular resolution by mass cytometry. Nat Methods. 2014;11(4):417-422. (documents IMC detector hot-pixel artifacts)"
  extracted_at: 2026-05-02
  extraction_confidence: high
  unverified_details: []
tags: [anti_pattern, no_hot_pixel_filter, no_steinbock, imc_artifact, hot_pixel]
causal_tag: causal
---

# NEG-NO-HOTPIXEL-IMC — IMC pipeline without hot-pixel filtering

## What this NEG- case records
**Anti-pattern**: running an IMC pipeline (per-cell quantification → cell typing → spatial neighborhood) without first applying a hot-pixel filter. Steinbock's `--filter-pixels --hpf 50` is the standard step; bypassing it lets detector artifacts (5-10 hot pixels per channel per ROI, intensities 100-1000× normal max) inflate per-cell mean intensities and confound cell typing.

## Where the failure mode was published
Giesen 2014 Nat Methods — IMC introduction paper — documents that mass-cytometry detectors produce sparse hot-pixel events. The Bodenmiller lab's Steinbock pipeline (Windhager 2023) makes hot-pixel filtering a mandatory first step.

## Mechanism — why it fails
- IMC's CyTOF detector has TOF jitter and dead-time artifacts that produce sparse single-pixel spikes at intensities 100-1000× the cell signal.
- ~50 hot pixels per channel per 1 mm² ROI is typical (50/30M pixels = 1.7e-6 hot-pixel rate, but each is ~30 000 ADU vs ~50 ADU normal background).
- Without filtering, the per-cell mean intensity for a cell that happens to overlap a hot pixel inflates by 1000× — that cell becomes a false-positive marker-positive call.
- 5-10 false positives per ROI cascade into incorrect cell typing and misleading spatial neighborhood enrichment.

## Concrete numerics (from PRAXIS-Cell cell-009 validated_run)
- Synthetic 30-channel × 256² ROI with **1 498 planted hot pixels** (50 per channel × 30 channels)
- After scipy.ndimage `median_filter` 3×3 + 5× threshold: **100 % of hot pixels caught** (1498/1498)
- arcsinh compression then 402× → range [0, 7.03]
- Per-cell intensity Pearson vs planted: **0.99999** (essentially exact)
- Cell typing accuracy: **100 %** (100/100 cells, 4 types)
- Without hot-pixel filter (run unmodified raw image): expected per-cell intensity Pearson vs planted < 0.7 (anecdotal Steinbock benchmarks)

## ★ Reviewer hard-stop
Any IMC design plan whose pipeline_steps list does not include a hot-pixel filter step (Steinbock `--filter-pixels`, scipy `median_filter` 3×3 + threshold, or equivalent) must be vetoed. THIS IS ALSO THE EXISTING REVIEWER HARD-STOP `tests/sanity/test_reviewer_imc.py`.

## Maps to anti-rule
**anti-rule #8**: IMC pipeline without hot-pixel filter is forbidden. Required: Steinbock `--filter-pixels` or scipy `median_filter` 3×3 + 5× threshold.

## Anti-retrieval keywords
no hot pixel, no median filter, raw imc, no steinbock filter, no hpf, hot pixel artifact, detector spike
