---
case_id: cell-008-3d-spheroid-segmentation
schema_version: 1
task: 3d_organoid_spheroid_segmentation
input_data: light-sheet or confocal z-stack of organoid
image_modality: light_sheet
sample_dimension: 3d_organoid
cell_type: organoid
assay_format: dish
channel_count: 3
dataset_accession: null
antibodies_rrid: []
software_versions:
  cellpose: ">=3.0"
  stardist: ">=0.8"
  plant-seg: ">=1.5"
  cellprofiler: ">=4.2"
tools: [Cellpose 3D, Stardist 3D, plant-seg, MCMICRO, CellProfiler 3D, ITK Snap]
key_paper_doi: 10.1038/s41592-022-01663-4
provenance:
  source_type: literature
  doi: 10.1038/s41592-022-01663-4
  citation: "Pachitariu M, Stringer C. Cellpose 2.0: how to train your own model. Nat Methods. 2022;19(12):1634-1641."
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
tags: [3d_segmentation, organoid, spheroid, light_sheet, anisotropic_voxel, z_stack, depth_correction, necrotic_core]
status: validated
---

# 3D 球体 / organoid 分割：z-stack 处理

## Background
3D 类器官 / spheroid 越来越主流（药筛、developmental biology）。**比 2D 难**：(1) z-stack 大数据；(2) z-axis resolution 差 vs xy；(3) 染色穿透有 gradient (deeper cells dimmer)；(4) anisotropic voxel。

## What I actually did
1. **Image stack**：confocal z-stack ~50-100 plane, voxel 0.5 × 0.5 × 2 μm (anisotropic)
2. **Pre-process**：denoise (DeepCAD / Noise2Void), illumination correction by depth, deconvolution if PSF known
3. **3D segmentation tool**：
   - **Cellpose 3D**：generalist, anisotropy aware
   - **Stardist 3D**：star-convex shapes
   - **plant-seg**：membrane-based for tightly packed cells
4. **Per-cell features in 3D**：volume, surface area, sphericity, marker intensity sum
5. **Spatial position in spheroid**：center vs periphery, zone assignment by distance to spheroid surface
6. **Visualization**：Napari / paraview / ChimeraX
7. **Specific challenges**：
   - **Hypoxia gradient**：center cells dying / quiescent → segmentation differ
   - **Necrotic core**：center 完全 dark
   - **Polar cell**：cells in epithelial monolayer 形态非 球形

## ★ 排除/不做的事
- **2D segmentation per plane + stack**：misses 3D continuity, breaks at z-axis
- **Cellpose 2D on 3D data**：3D context lost
- **Forget anisotropic voxel**：xy 0.5 vs z 2 → metric calculation 偏
- **No depth-based illumination correction**：deeper cells underestimated
- **Per-plane intensity not 3D integration**：cell signal split across planes
- **Whole-organoid feature without per-zone**：center/periphery 差异 lost

## ★ 失败模式
- **Photobleaching with depth**：deeper plane signal weak
- **Light scattering**：deep imaging low resolution
- **Necrotic core anomaly**：center can be over/under-segmented
- **Imaging speed vs sample motion**：long acquisition spheroid drifts
- **Compute resources**：3D z-stack 100 GB+ 常态
- **Heterogeneous organoid composition**：multi-cell type → segmentation needs per-type strategy

## Lessons → seeds for rules
1. **3D-aware segmentation** (Cellpose 3D / Stardist 3D)
2. **Anisotropic voxel** correction
3. **Depth-based illumination correction**
4. **Per-zone analysis** (center vs periphery)
5. **Light-sheet > confocal** for deep imaging
6. **Compute / storage planning** (TB scale)
7. **Necrotic core flag** for analysis
