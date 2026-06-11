---
case_id: NEG-WATERSHED-DEFAULT
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 1
task: cell_segmentation_fluorescence
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: generic_cell_line
assay_format: dish
channel_count: 1
dataset_accession: null
antibodies_rrid: []
software_versions:
  scikit-image: ">=0.22"
tools: [scikit-image watershed, distance transform, threshold + watershed]
key_paper_doi: 10.1038/s41592-020-01018-x
provenance:
  source_type: literature
  doi: 10.1038/s41592-020-01018-x
  citation: "Stringer C, Wang T, Michaelos M, Pachitariu M. Cellpose: a generalist algorithm for cellular segmentation. Nat Methods. 2021;18(1):100-106. (Fig 1c benchmarks watershed vs Cellpose F1)"
  extracted_at: 2026-05-02
  extraction_confidence: high
  unverified_details: []
tags: [anti_pattern, watershed_only, no_dl, touching_cells, segmentation]
causal_tag: causal
---

# NEG-WATERSHED-DEFAULT — Default watershed segmentation on touching cells

## What this NEG- case records
**Anti-pattern**: using vanilla `scikit-image.segmentation.watershed` (or `threshold_otsu` + `watershed`) as the default segmentation when the data contains touching cells, without first trying a learned model (Cellpose / StarDist / Mesmer).

## Where the failure mode was published
Stringer 2021 Cellpose Nat Methods Fig 1c: on the Cellpose-trained dataset (~70k cells from 7 microscopy modalities), watershed achieves F1 ≈ 0.45 (touching cells split or merged); Cellpose cyto2 F1 ≈ 0.85.

## Mechanism — why it fails
Watershed depends on a distance-transform topography. At touching-cell boundaries, the distance gradient vanishes, so watershed places markers at false minima or merges true neighbours. Without a learned cell-shape prior, no per-image tuning fixes this.

## Concrete numerics
- Watershed F1 ≈ 0.45 on touching-cell data (Stringer 2021)
- Cellpose cyto2 F1 ≈ 0.85 on same data (Stringer 2021)
- Margin ≈ +89 % F1 by switching method

## ★ Reviewer hard-stop
Any design plan that lists "watershed only" or "scikit-image watershed" as the segmentation step on touching-cell data must be vetoed. Acceptable only when (a) cells are clearly isolated (sparse < 5/100k px²) AND (b) DL model confidence is low (out-of-domain).

## Maps to anti-rule
**anti-rule #1**: Default-watershed segmentation on touching-cell fluorescence is forbidden. Required: try Cellpose / StarDist first.

## Anti-retrieval keywords
watershed, scikit-image segmentation, distance transform, threshold + watershed, default segmentation, no DL, no cellpose
