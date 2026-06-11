---
case_id: NEG-PER-IMAGE-PROFILE
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 2
task: morphological_deep_profiling
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: generic_cell_line
assay_format: 384well
channel_count: 6
dataset_accession: null
antibodies_rrid: []
software_versions:
  cellprofiler: ">=4.2"
  pycytominer: ">=1.0"
tools: [CellProfiler, raw per-image features, no per-cell aggregation, no per-well median]
key_paper_doi: 10.1038/nmeth.4397
provenance:
  source_type: literature
  doi: 10.1038/nmeth.4397
  citation: "Caicedo JC et al. Data-analysis strategies for image-based cell profiling. Nat Methods. 2017;14(9):849-863. (defines per-well median > per-image; quantifies signal loss when per-image used)"
  extracted_at: 2026-05-02
  extraction_confidence: high
  unverified_details: []
tags: [anti_pattern, per_image, no_aggregation, hcs, profiling]
causal_tag: causal
---

# NEG-PER-IMAGE-PROFILE — Per-image (not per-well) profile for HCS / Cell Painting

## What this NEG- case records
**Anti-pattern**: using per-image feature vectors (or per-pixel features) as the unit of analysis for HCS / Cell Painting, without first aggregating per-cell features to a per-well median.

## Where the failure mode was published
Caicedo 2017 Nat Methods — the canonical methodology paper for image-based profiling — explicitly recommends per-well median (or per-cell distribution moments) and shows that per-image profiles inflate variance and dominate downstream MoA recall by image-to-image noise.

## Mechanism — why it fails
- A 384-well Cell Painting plate has ~5000 cells per well across ~12 fields. Per-image features average ~400 cells per image, but field-to-field acquisition variance (focus, illumination, registration) injects ~20–40 % CV into the profile vector.
- Per-cell aggregation collapses per-cell biological heterogeneity to a per-well median, which is robust to field-level outliers.
- Downstream MoA classification accuracy on BBBC021: per-cell+per-well-median pipeline reports NSC accuracy 70-94 % (Caicedo 2017); per-image-only profile drops this 10-20 pp.

## ★ Reviewer hard-stop
Any HCS / Cell Painting design plan that aggregates only at per-image level (no per-cell aggregation, no per-well median) must be vetoed. Required pipeline: per-cell features → per-well median → per-treatment median (after batch correction).

## Maps to anti-rule
**anti-rule #2**: Per-image-only profile for HCS profiling is forbidden. Required: per-cell features → per-well median.

## Anti-retrieval keywords
per-image profile, per-pixel hcs, no aggregation, raw image features, no per-cell, no median aggregation, mean instead of median
