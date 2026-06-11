---
rule_id: 01-segmentation-tool-selection
schema_version: 1
scope: case_distilled
applies_to:
  cell_task: cell_segmentation_fluorescence
  image_modality: ALL
  sample_dimension: ALL
evidence_cases:
  - cell-001-cellpose-segmentation
  - cell-008-3d-spheroid-segmentation
  - cell-011-mesmer-tissue-segmentation
  - cell-014-hovernet-histology
confidence: high
rule_type: tool_selection
---

# 分割工具决策树（按 sample_dimension × image_modality × tissue context）

来自 4 篇真实文献：Cellpose（cell-001）、Cellpose 3D / Stardist 3D（cell-008）、Mesmer/TissueNet（cell-011）、HoVer-Net（cell-014）。

## 决策表（用于 Design 阶段 tool_choice 必读）

| sample_dimension | image_modality | cell context | **首选工具** | 备选 | 凭据 case |
|---|---|---|---|---|---|
| 2d_single_cell | fluorescence | monolayer / dish | **Cellpose 3 (cyto2 or cyto3)** | Stardist | cell-001 |
| 2d_tissue | fluorescence (multiplex) | tissue (CODEX, IF) | **Mesmer (TissueNet)** | DeepCell | cell-011 |
| 2d_tissue | brightfield (H&E) | histology / WSI | **HoVer-Net** | StarDist H&E, QuPath | cell-014 |
| 2d_tissue | IMC | metal-tagged tissue | **Mesmer + Steinbock** preprocess | ImcSegmentationPipeline | cell-009 (Steinbock) + cell-011 (Mesmer) |
| 3d_organoid | confocal / light_sheet | spheroid / organoid | **Cellpose 3D** | Stardist 3D, plant-seg | cell-008 |
| time_lapse | fluorescence | live cell | **Cellpose nuclear + LAP linker** (TrackMate) | Btrack | cell-004 |

## ❌ 禁用模式（Reviewer 必拦）

1. **Watershed default** — 仅适合 simple separated objects；现代 DL 准很多。
2. **Cellpose default `diameter`** — image-specific；估错让分割全错。必须 explicit set。
3. **Cellpose 2D 跑 3D 数据** — 损 z-axis continuity；3D 必用 Cellpose 3D / Stardist 3D / plant-seg。
4. **Cellpose for tissue (H&E)** — Cellpose 训练在 single-cell；tissue 用 Mesmer / HoVer-Net。
5. **HoVer-Net without stain normalization** — 跨 site/scanner H&E 性能掉 10-20%；Macenko/Vahadane 必备。
6. **Forget border-cell filter** — partial cell 给 wrong area；任何 segmentation 后处理必删边缘细胞。

## ★ 必填参数（不能用默认）

- Cellpose: `diameter`, `flow_threshold`, `cellprob_threshold`, `model`
- Stardist: `n_tiles`, `prob_thresh`, `nms_thresh`
- Mesmer: `image_mpp`（microns-per-pixel） — 默认 0.5 μm 会让 0.325 μm 数据 over-segment
- Cellpose 3D: anisotropy ratio (z_voxel / xy_voxel)
- HoVer-Net: 5-class output (neoplastic / stromal / immune / dead / non-neoplastic-epithelial)

## ★ Validation gate（出 design 前必有）

- 2D / 3D segmentation: IoU ≥ 0.7 vs 100 manual cell
- HoVer-Net classification: F1 ≥ 0.65 (PanNuke baseline)
- Mesmer tissue: F1 ≥ 0.85 (TissueNet baseline)

## 边界（rule 不适用）

- EM 重建（不在 case 中）
- Super-resolution localization（用 cell-012 / ThunderSTORM 路径）
- Calcium imaging ROI（用 cell-013 / CaImAn 路径，CNMF 不是 segmentation）
