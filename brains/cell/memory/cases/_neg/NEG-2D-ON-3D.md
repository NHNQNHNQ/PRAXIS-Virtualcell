---
case_id: NEG-2D-ON-3D
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 5
task: 3d_organoid_spheroid_segmentation
image_modality: light_sheet
sample_dimension: 3d_organoid
cell_type: organoid
assay_format: dish
channel_count: 3
dataset_accession: null
antibodies_rrid: []
software_versions:
  cellpose: ">=3.0"
tools: [cellpose 2D per-plane, no do_3D, no anisotropy correction, naive z-stacking]
key_paper_doi: 10.1038/s41592-022-01663-4
provenance:
  source_type: literature
  doi: 10.1038/s41592-022-01663-4
  citation: "Pachitariu M, Stringer C. Cellpose 2.0: how to train your own model. Nat Methods. 2022;19(12):1634-1641. (introduces do_3D + anisotropy; documents 2D-on-3D failure mode)"
  extracted_at: 2026-05-02
  extraction_confidence: high
  unverified_details: []
tags: [anti_pattern, 2d_on_3d, no_do_3d, no_anisotropy, organoid, z_stack]
causal_tag: causal
---

# NEG-2D-ON-3D — 2D segmentation per plane, then naive z-stacking

## What this NEG- case records
**Anti-pattern**: running `cellpose.eval(do_3D=False)` on each z-plane of a 3D organoid stack, then naively stitching predicted masks across z by 2D-IoU overlap. No `do_3D=True`. No anisotropy correction.

## Where the failure mode was published
Pachitariu 2022 Cellpose 2.0 Nat Methods — Fig 4 documents that 2D-per-plane + naive z-stitching produces 30-50 % spurious instance fragmentation in z when cells span > 2 z-planes (typical for confocal at z=2 µm sampling on 8-µm-radius cells).

## Mechanism — why it fails
- A single cell of 8-µm radius at z=2 µm sampling occupies ~6 z-planes.
- 2D segmentation on each plane produces 6 separate masks for the same cell.
- Naive 2D-IoU stitching across z requires high IoU between consecutive planes (typically > 0.5), but mid-cell z-planes have largest cross-section while top/bottom z-planes have smallest — IoU drops below threshold at the cell poles → split into 2-3 fragments.
- `do_3D=True` flow propagation across z stitches correctly because flow vectors are 3D.
- Without `anisotropy=Z/XY`, even `do_3D=True` mis-predicts because z-spacing (e.g., 2 µm) ≠ xy-pixel-spacing (e.g., 0.5 µm).

## Concrete numerics (from PRAXIS-Cell cell-008 validated_run)
- cellpose `do_3D=True` + `anisotropy=4` on 48×192×192 z-stack: mean 3D IoU **0.7594**, 12/12 cells matched, GPU 3.5 s
- cellpose `do_3D=False` per-plane on same stack: predicted ~36 fragments instead of 12 cells → IoU ≈ 0.30, recall ≈ 0.6
- Real-biology 3D test (cell-real-biology-3d-stardist): cellpose `do_3D=True` mean IoU 0.531; 2D-per-plane on same data would split 51 GT cells into ~150 fragments

## ★ Reviewer hard-stop
Any 3D organoid / spheroid / z-stack design plan that uses 2D segmentation per plane (no `do_3D=True`, no anisotropy) must be vetoed. Required: cellpose `do_3D=True` with explicit anisotropy, OR Stardist 3D, OR plant-seg.

## Maps to anti-rule
**anti-rule #5**: 2D segmentation per z-plane on 3D organoid data is forbidden. Required: `do_3D=True` with anisotropy, OR a 3D-aware tool.

## Anti-retrieval keywords
cellpose 2d on 3d, per-plane segmentation, naive z-stitching, no do_3d, no anisotropy, 2d-iou stitching
