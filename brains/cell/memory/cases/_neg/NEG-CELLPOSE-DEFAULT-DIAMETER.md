---
case_id: NEG-CELLPOSE-DEFAULT-DIAMETER
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 11
task: cell_segmentation_fluorescence
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: generic_cell_line
assay_format: dish
channel_count: 1
dataset_accession: null
antibodies_rrid: []
software_versions:
  cellpose: ">=3.0"
tools: [cellpose, default diameter=30, no per-image diameter estimation, no scale calibration]
key_paper_doi: 10.1038/s41592-020-01018-x
provenance:
  source_type: literature
  doi: 10.1038/s41592-020-01018-x
  citation: "Stringer C, Wang T, Michaelos M, Pachitariu M. Cellpose: a generalist algorithm for cellular segmentation. Nat Methods. 2021;18(1):100-106. (defines diameter as critical hyperparameter; recommends per-dataset estimation)"
  extracted_at: 2026-05-02
  extraction_confidence: high
  unverified_details: []
tags: [anti_pattern, cellpose_default_diameter, no_per_image_diameter, no_scale_calibration]
causal_tag: causal
---

# NEG-CELLPOSE-DEFAULT-DIAMETER — Cellpose with hardcoded default diameter

## What this NEG- case records
**Anti-pattern**: calling `cellpose.eval(diameter=30)` (the historical default) on every image regardless of actual cell size in pixels. Cellpose's diameter parameter directly controls the model's spatial scale; mismatched diameter produces over-segmentation (diameter too small) or merging (diameter too large).

## Where the failure mode was published
Stringer 2021 Cellpose Nat Methods — `diameter` is documented as the single most-important hyperparameter. Cellpose 3 added `--diameter 0` for auto-estimation but defaults to 30 if neither manual nor auto is set.

## Mechanism — why it fails
- Cellpose's flow-field network is trained on size-normalized cells.
- It re-scales input images by `diameter / 30` so that internal features see ~30-px cells.
- If you pass `diameter=30` for an image where cells are actually 80 px (e.g., U2OS at 20× objective), Cellpose down-samples by 1× when it should down-sample by 2.7× → cell predictions get broken into many small ovals.
- If you pass `diameter=30` for an image where cells are 10 px (e.g., bacteria at 60× objective), Cellpose up-samples wrongly → cells get merged.

## Concrete numerics (from PRAXIS-Cell tests)
- cell-001 validated_run: 100 synthetic disks at 12-px radius (diameter=24), explicit `diameter=24` → IoU **0.9044**
- cell-real-biology-skimage: 1 cell mid-mitosis at 80-px size, explicit `diameter=80` → 1 cell detected, area 15 137 px (correct)
- cell-real-biology-cellpose-vs-stardist: GT median diameter 23.7 px, explicit `diameter=23.7` → 104/183 matched at IoU≥0.5
- All three would fail catastrophically if `diameter=30` (default) were used regardless of actual scale

## ★ Reviewer hard-stop
Any cellpose-based design plan that does not specify a `diameter` value (relying on default 30 instead of explicit per-image estimation OR `--diameter 0` auto-estimate) must be vetoed. Required: explicit diameter from prior knowledge (objective + cell type) OR cellpose `--diameter 0` auto-estimate.

## Maps to anti-rule
**anti-rule #11**: Cellpose with default diameter (no per-image estimation) is forbidden. Required: explicit diameter or cellpose auto-estimate.

## Anti-retrieval keywords
cellpose default diameter, diameter=30, no diameter, no scale calibration, no auto-estimate diameter, hardcoded diameter
