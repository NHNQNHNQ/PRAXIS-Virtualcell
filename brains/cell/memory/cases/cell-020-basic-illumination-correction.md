---
case_id: cell-020-basic-illumination-correction
schema_version: 1
task: cell_segmentation_fluorescence
input_data: HCS plate or tile-stitched WSI with uneven illumination
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: generic_cell_line
assay_format: 384well
channel_count: 4
dataset_accession: null
antibodies_rrid: []
software_versions:
  basicpy: ">=1.0"
  scikit-image: ">=0.22"
  pybasic: ">=0.0.4"
tools: [BaSiC, BaSiCPy, CellProfiler IllumCorrect, scikit-image rolling_ball, Fiji BaSiC]
key_paper_doi: 10.1038/ncomms14836
provenance:
  source_type: literature
  doi: 10.1038/ncomms14836
  citation: "Peng T et al. A BaSiC tool for background and shading correction of optical microscopy images. Nat Commun. 2017;8:14836."
  extracted_at: 2026-04-30
  extraction_confidence: high
  unverified_details: []
tags: [basic, illumination_correction, shading_correction, hcs_preprocessing, rolling_ball, vignetting, plate_consistency]
status: validated
---

# BaSiC：HCS / WSI illumination + shading correction

## Background
**BaSiC** (Peng 2017 Nat Commun) 通过对一组 image 的 sparse + low-rank 分解估出 (1) flat-field (multiplicative shading) (2) dark-field (additive offset)：image = (true × flat-field) + dark-field + noise. **解决**：(1) HCS plate 中 vignetting (corner darker)；(2) tile-stitched WSI 拼接边亮度跳变；(3) cycle-to-cycle CODEX intensity drift；(4) IF cell-painting plate 间 illumination 不一。**与 rolling-ball 区别**：rolling-ball 是 per-image local；BaSiC 用 plate-level / dataset-level 信息估真 flat-field，物理意义更强。

## What I actually did
1. **Input**：384-well plate × 4 channel × ~50 fields per well = 76800 image
2. **Per-channel processing**：BaSiC 对每 channel 独立估 flat-field + dark-field
3. **Estimation**：`basic = BaSiC()`; `basic.fit(images)`（subset 1000 random images 已够，full 数据集太慢）
4. **Apply**：每张 image `corrected = (raw - dark_field) / flat_field`
5. **Validation**：corner-vs-center wells 应 illumination 平等；DMSO control 在每 well 一致
6. **Verify before downstream**：跑 segmentation 前后对比 — corrected image 上 Cellpose 性能升 ~5% IoU
7. **Cycle correction (CODEX)**：每 cycle 单独估 flat-field（cycle 1-10 illumination 不一）

## ★ 排除/不做的事
- **Rolling-ball as substitute**：仅 background subtract，不 shading correct；HCS 必用 BaSiC
- **Single global flat-field across plates**：plate-to-plate variation；per-plate 估
- **Skip dark-field**：CCD camera dark current 是真存在；忽略让 dim signal 假高
- **Apply corrected image to downstream model trained on raw**：训练时 illumination distribution 含 vignetting；corrected 后 distribution shift；要么 retrain 要么也 raw
- **Estimate from < 100 image**：sample 数少 → 假 flat-field
- **Forget log domain**：当 dynamic range 大（>1000×）应在 log 域估
- **Mix channels**：DAPI + Cy5 一起估 → BaSiC 假设 channel 独立违背

## ★ 失败模式
- **Cell-rich vs cell-sparse field 混合**：BaSiC 假设 image = true × flat；cell-rich 让 flat 估偏 cell shape
- **HDR sample (mostly black + few bright)**：sparse 假设违背
- **Camera replacement**：scope upgrade 后 flat-field 完全变；旧 model 失效
- **Stage drift**：long acquisition 中 stage 偏 → flat-field 实际 drift
- **Auto-fluorescence drift across cycle**：CODEX 长时 imaging 让 baseline 涨
- **Saturation pixel**：clipped pixel 让 flat-field 估异常

## Lessons → seeds for rules
1. **BaSiC > rolling-ball** for HCS plate / tile-stitch / multi-cycle
2. **Per-channel + per-plate** estimation
3. **Subset 1000 image** sufficient for fit; full dataset too slow
4. **Cycle-aware correction** for CODEX
5. **Validate corner-vs-center DMSO** post-correction
6. **Retrain downstream model on corrected** OR keep both raw
7. **Pre-segmentation step** in any large-scale pipeline (HCS / WSI / time-lapse)
