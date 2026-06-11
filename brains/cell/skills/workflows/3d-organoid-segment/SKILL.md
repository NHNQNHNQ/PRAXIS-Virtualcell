---
name: 3d-organoid-segment
description: 3D z-stack 类器官分割 — Cellpose 3D / Stardist 3D / plant-seg；anisotropic voxel correction；depth-based illumination correction；per-zone（center vs periphery）feature。`--simulate` 合成 spheroid，期望 volume estimate ±20%。
status: green
host_env: PRAXIS-Cell
---

# 3d-organoid-segment

## 一句话原则
**3D-aware tool 必备**（不可 2D per-plane）；**anisotropic voxel correction**（xy 0.5 vs z 2 μm）；**depth illumination correction**（deeper 较暗）；per-zone（center / periphery）feature 不能 whole-organoid average。

## 输入契约
```
--zstack PATH               # 3D TIFF z-stack
--voxel X Y Z               # μm; e.g. 0.5 0.5 2.0
--tool {cellpose3d,stardist3d,plant-seg}
--out PATH
--simulate
```

## 输出契约
```json
{
  "mask_3d_tif": "out/mask_3d.tif",
  "per_cell_3d_features_csv": "out/per_cell_3d_features.csv",
  "zone_assignment_csv": "out/zone_assignment.csv",
  "n_cells_3d": 312,
  "estimated_volume_um3": 1.45e6,
  "true_volume_um3": 1.50e6,
  "volume_error_frac": 0.033,
  "passed_sanity": true
}
```

## Sanity（case-008）
合成 sphere（已知体积 V0）→ Cellpose-3D-like predicted volume V → |V/V0 - 1| ≤ 0.2。

## Cited cases
- cell-008-3d-spheroid-segmentation
