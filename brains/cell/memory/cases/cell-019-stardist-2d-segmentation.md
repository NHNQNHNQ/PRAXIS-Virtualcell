---
case_id: cell-019-stardist-2d-segmentation
schema_version: 1
task: cell_segmentation_fluorescence
input_data: 2D fluorescence with star-convex objects (nuclei, blobs, ribozymes)
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: generic_cell_line
assay_format: 96well
channel_count: 1
dataset_accession: null
antibodies_rrid: []
software_versions:
  stardist: ">=0.8"
  csbdeep: ">=0.7"
  tensorflow: ">=2.13"
tools: [StarDist, CSBDeep, scikit-image, Cellpose (alternative), Mesmer (alternative)]
key_paper_doi: 10.1007/978-3-030-00934-2_30
provenance:
  source_type: literature
  doi: 10.1007/978-3-030-00934-2_30
  citation: "Schmidt U et al. Cell Detection with Star-Convex Polygons. MICCAI 2018; LNCS 11071:265-273."
  extracted_at: 2026-04-30
  extraction_confidence: high
  unverified_details: []
tags: [stardist, star_convex_polygon, nuclear_segmentation, dl_segmentation, fluorescence, dapi, alternative_to_cellpose]
status: validated
---

# StarDist：star-convex polygon 检测 — 核分割 SOTA

## Background
**StarDist** (Schmidt 2018 MICCAI) 用 star-convex polygon 表示 cell/nucleus mask（每像素预测 N=32 方向到边界的距离 + object probability）→ 后处理 NMS → instance mask。**优势**：(1) 对 touching cells 极其稳健（每 instance 形态由 N 个 ray 唯一定义，不像 watershed 依 boundary）；(2) 训练数据 ~50-200 annotated cells 即可超越 watershed；(3) 模型小（~2 MB），CPU 推理快；(4) 在 nuclei (DAPI) 上特别强。**与 Cellpose 区别**：Cellpose 处理任意形态（star-convex 不成立的 polarized cell）；StarDist 是 DL nuclei segmentation 黄金；HCS DAPI channel 应用首选。

## What I actually did
1. **Input**：96-well plate DAPI channel；~5000 cells per well
2. **Pretrained model**：`StarDist2D.from_pretrained('2D_versatile_fluo')`（fluorescence 通用 nuclei）；可 swap '2D_versatile_he' 用 H&E
3. **Inference**：`model.predict_instances(img_normalized, prob_thresh=0.5, nms_thresh=0.4, n_tiles=(2,2))`；large image 必 tile
4. **Tile + stitch**：`n_tiles=(2,2)` for 1024×1024 image；boundary handling 自动
5. **Per-cell features**：area, perimeter, intensity per channel within polygon mask
6. **Post-process**：filter `prob_thresh < 0.5`（low confidence segments）+ border touching
7. **Validation**：100 manual annotated nuclei → IoU ≥ 0.85（StarDist 在 nuclei 普遍优于 Cellpose 0.05-0.1）

## ★ 排除/不做的事
- **StarDist for non-star-convex shapes**：polarized epithelial cells / elongated muscle / dendrite — 用 Cellpose
- **Use default `prob_thresh=0.5` for all data**：H&E / IF / EM tune separately
- **Skip `nms_thresh` tuning**：触合 nuclei 用 0.3-0.4；分离 nuclei 用 0.5-0.6
- **Single-tile predict on large image**：>2048 px 推理 OOM；必 `n_tiles`
- **Forget normalize before predict**：StarDist 训练在 normalized 0-1；raw 16-bit 性能差
- **Tile boundary nuclei split**：默认处理，但极大 nuclei 跨 tile 时仍可能 split — 加 overlap
- **Train from scratch on 50 cells**：< 200 annotated 训不动；用 pretrained + finetune

## ★ 失败模式
- **Heterogeneous nucleus shape**：dividing nuclei (anaphase) 形态非 star-convex → split
- **Touching nuclei (S phase)**：两 daughters 紧贴 → NMS 合并；调 `nms_thresh` 至 0.3
- **Out-of-focus**：blurry → low `prob_thresh` 不达
- **Large dim nuclei**：normalization 让 dim cells 更暗 → miss
- **Stain heterogeneity (necrosis, mitosis)**：训练分布外
- **Channel mismatch**：训 DAPI 用到 GFP-H2B → 性能 degrade（intensity 分布不同）
- **Post-finetune overfitting**：< 50 finetune cell → 学到 specific lab artifacts

## Lessons → seeds for rules
1. **StarDist for nuclei** (DAPI / DRAQ5) — 优于 Cellpose 0.05-0.1 IoU
2. **Cellpose for whole cells** — 处理 non-star-convex
3. **Pretrained model first** (`2D_versatile_fluo` / `2D_versatile_he`)
4. **`n_tiles` mandatory** for image > 1024 px
5. **`nms_thresh` tune per dataset** (touching → 0.3; isolated → 0.5)
6. **Normalize 0-1 before predict** (CSBDeep `normalize` helper)
7. **Border + low-confidence filter** post-segment (rule 05)
