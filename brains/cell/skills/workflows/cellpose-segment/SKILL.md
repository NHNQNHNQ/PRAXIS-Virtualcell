---
name: cellpose-segment
description: Cellpose 2D 分割 + per-cell features (intensity / shape / Haralick texture) + manual-IoU sanity. cyto2 / nuclei / membrane / custom 模型可选；diameter / flow_threshold / cellprob_threshold 必须 explicit；filter border cell；--simulate 走合成 PSF cells (无需 GPU/Cellpose binary)。Agent 3 (Execution) 任何 segmentation 任务的标准起手。
status: green
host_env: PRAXIS-Cell
---

# cellpose-segment

## 一句话原则
**禁用** Cellpose default diameter；**必须 explicit** 设 `--diameter`、`--flow-threshold`、`--cellprob-threshold`；**必须 filter border cell**；per-cell（不是 per-pixel）quantify。

## 适用阶段
Agent 3 (Execution)，任何 segmentation / 下游 HCS / dose-response / colocalization 起手。

## 输入契约（CLI）
```
--image PATH            # 单张 image (TIFF / PNG / Zeiss CZI)
--diameter FLOAT        # 像素;必填，禁默认
--model {cyto2,nuclei,cyto3,custom}
--channels CH1,CH2      # e.g. 2,1 = green cyto + blue nuclei
--flow-threshold FLOAT  # 推荐 0.4
--cellprob-threshold FLOAT # 推荐 0.0
--out PATH              # 输出目录
--simulate              # 合成数据 + sanity assert (不调 Cellpose)
```

## 输出契约
```json
{
  "mask_path": "out/mask.tif",
  "n_cells": 78,
  "per_cell_features_csv": "out/per_cell_features.csv",
  "overlay_png": "out/overlay.png",
  "iou_vs_manual": 0.78,
  "border_cells_filtered": 12,
  "passed_sanity": true
}
```

## Sanity（来自 case-001）
100 manually-annotated cells IoU vs Cellpose mask ≥ 0.7。`--simulate` 模式生成 100 synthetic cells + ground-truth mask + add Gaussian PSF noise，期望 IoU ≥ 0.7。

## 失败模式（必看）
- Touching cell cluster 分割不彻底 → 调 flow_threshold / 用 cyto3
- Heterogeneous illumination → 上游 BaSiC / rolling-ball
- Auto-fluorescence cell miss → membrane channel 必给
- Tile/stitching artifact → image 边 cell filter

## Cited cases
- cell-001-cellpose-segmentation
