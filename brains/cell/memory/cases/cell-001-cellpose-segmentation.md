---
case_id: cell-001-cellpose-segmentation
schema_version: 1
task: cell_segmentation_fluorescence
input_data: 2-channel fluorescence (DAPI + cell membrane marker)
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: generic_cell_line
assay_format: 96well
channel_count: 2
dataset_accession: null
antibodies_rrid: []
software_versions:
  cellpose: ">=3.0"
  stardist: ">=0.8"
  cellprofiler: ">=4.2"
tools: [Cellpose 3, Stardist, CellProfiler 4, Mesmer (TissueNet), DeepCell, Napari]
key_paper_doi: 10.1038/s41592-020-01018-x
provenance:
  source_type: literature
  doi: 10.1038/s41592-020-01018-x
  citation: "Stringer C et al. Cellpose: a generalist algorithm for cellular segmentation. Nat Methods. 2021;18(1):100-106."
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
tags: [segmentation, fluorescence, cellpose, deep_learning, generalist_model, dapi, membrane_marker]
status: validated
---

# Cellpose：DL-based 通用细胞分割（替代 watershed/manual）

## Background
Cellpose（Stringer 2021 Nature Methods）训练在跨多 modality（fluorescence, brightfield, EM）+ 多 cell type → 通用 generalist model。**比传统 watershed 准 + 不需逐 dataset 调参**。Cellpose 3（2024）加 super-resolution + denoising。是 cell biology 影像分析 first-tier tool。

## What I actually did
1. **Input**：96-well plate fluorescence image，channel 1 = DAPI (nucleus), channel 2 = cell mask marker
2. **Cellpose 'cyto2' model**：predict 2-channel image → mask
3. **`diameter` parameter**：预估 cell diameter (pixels)，决定 model scale；自动 estimate 或 manual set
4. **Flow threshold + cellprob threshold**：tune to balance over/under-segmentation
5. **Post-processing**：remove cells touching image border, area filter (10 < pix < 50000)
6. **Per-cell features**: area, perimeter, solidity, intensity per channel, texture (Haralick)
7. **Multi-channel intensity quantification**：每 cell 在 channel 2/3/4 的 mean / total intensity
8. **Output**：mask file + per-cell feature CSV + visualization overlay
9. **Validation**：100 manually-annotated cells → IoU (intersection over union) > 0.7 = success

## ★ 排除/不做的事
- **Watershed default**：现代 DL 准很多；watershed 仅适合 simple separated objects
- **Cellpose default diameter**：image-specific，估错让分割全错
- **Single channel segmentation when membrane marker available**：双 channel input 准很多
- **不 filter border cells**：partial cells 给 wrong area
- **Per-pixel intensity not per-cell**：HCS 需 per-cell stat
- **Cellpose for tissue (H&E)**：tissue 用 Mesmer / HoVerNet，Cellpose 是 single-cell

## ★ 失败模式
- **Touching cells not separated**：dense cell cluster 分割不彻底
- **Out-of-focus regions**：blurry → low confidence segment
- **Auto-fluorescence**：low signal cell 被 miss
- **Tile / stitching artifact**：multi-tile image 边界 cell 切断
- **Heterogeneous cell shape (3D, polarized)**：generalist model 偏 simple 形态
- **Heterogeneous illumination**：rolling-ball or BaSiC correction first

## Lessons → seeds for rules
1. **DL segmentation > watershed** as default
2. **Cellpose `cyto2` + 2 channel input** 推荐
3. **Diameter parameter set explicitly**
4. **Border cell filter** mandatory
5. **Per-cell quantification not per-pixel**
6. **Validation IoU vs manual annotation** ≥ 0.7
7. **Illumination correction** preprocessing
