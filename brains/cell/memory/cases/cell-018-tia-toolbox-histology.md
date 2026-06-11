---
case_id: cell-018-tia-toolbox-histology
schema_version: 1
task: histology_nuclear_segmentation_classification
input_data: WSI (whole-slide H&E) with tissue-level + cell-level analysis
image_modality: brightfield
sample_dimension: 2d_tissue
cell_type: tumor_tissue
assay_format: slide
channel_count: 3
dataset_accession: null
antibodies_rrid: []
software_versions:
  tiatoolbox: ">=1.5"
  pytorch: ">=2.0"
  openslide-python: ">=1.3"
tools: [TIA Toolbox, OpenSlide, HoVer-Net (via TIA), MoNuSeg, NuClick, PathML]
key_paper_doi: 10.1038/s43856-022-00186-5
provenance:
  source_type: literature
  doi: 10.1038/s43856-022-00186-5
  citation: "Pocock J et al. TIAToolbox as an end-to-end library for advanced tissue image analytics. Commun Med. 2022;2:120."
  extracted_at: 2026-04-30
  extraction_confidence: high
  unverified_details: []
tags: [tia_toolbox, histology_pipeline, wsi_processing, hovernet_wrapper, openslide, tile_streaming, patch_predict]
status: validated
---

# TIA Toolbox：histology WSI 端到端 pipeline 库

## Background
**TIA Toolbox** (Pocock 2022 Commun Med) 是 University of Warwick TIA 中心维护的 H&E WSI 处理库 — 比 HoVer-Net 单一模型更宽，覆盖 (1) WSI I/O (OpenSlide / OME-TIFF / DICOM)；(2) tissue mask；(3) stain normalization (Macenko / Vahadane)；(4) patch extraction at any magnification；(5) HoVer-Net + ResNet 等预训练模型 wrapping；(6) tile-based prediction；(7) graph-based downstream。**为何关键**：单 HoVer-Net 是 model；TIA Toolbox 是 production-ready pipeline glue。

## What I actually did
1. **Input**：multi-GB .svs WSI；目标 — patch-level tissue type classification + nuclear segmentation
2. **WSI I/O**：`tiatoolbox.wsicore.WSIReader.open(svs_path)` — OpenSlide 后端；no full-image load
3. **Tissue mask**：`reader.tissue_mask(method='otsu', resolution=1.25, units='power')` → 区分 tissue vs glass / pen mark
4. **Stain norm**：`tiatoolbox.tools.stainnorm.MacenkoNormalizer.fit(target_image)` → cross-site H&E 一致化
5. **Patch extraction**：`PatchExtractor.predict_wsi(model, patch_input_shape=(256,256), resolution=0, units='level', stride_shape=(192,192))`
6. **Predict tile-by-tile**：HoVer-Net pretrained on PanNuke → nuclear instance + 5-class
7. **Aggregate WSI-level**：tissue type fraction; nuclei density per tissue region
8. **Graph downstream**：optional — build cell graph for spatial analysis (not in default scope)

## ★ 排除/不做的事
- **Load WSI as numpy array**：multi-GB OOM；必须 OpenSlide 流式
- **Skip tissue mask**：predict 在 background 浪费 ~50% compute + 假阳
- **Skip stain norm**：cross-site H&E 性能掉 10-20%（cell-014 同教训）
- **Single-magnification analysis**：tissue context 在 5-10×；nuclei 在 40×；必须 multi-resolution
- **No overlap in patch stride**：boundary nuclei split；stride < patch_size
- **Custom HoVer-Net weights without retrain**：domain shift（kidney vs colon）
- **Run on glass region**：pen mark / dust 假阳

## ★ 失败模式
- **OpenSlide format issues**：vendor proprietary (Aperio / Hamamatsu / Leica) 处理差异
- **Magnification mismatch**：vendor `40×` 实际 0.25 μm/px vs 0.23 μm/px → resolution arg 必须 explicit
- **Pyramid level inconsistency**：scanner 不同导致 level 0 不同；用 `units='power'` 不是 `units='level'`
- **GPU OOM with patch + batch large**：default batch_size=64 + 256×256 patch on 11 GB GPU 边缘
- **Tissue mask threshold**：Otsu fails on slides with strong artifact；用 manual / morphological
- **Patch boundary nuclei**：只在 boundary 附近 cells 分割不连续；merge 启发式不完美

## Lessons → seeds for rules
1. **WSI I/O must be streaming** (OpenSlide / Bio-Formats) — never full load
2. **Tissue mask first** to skip glass / artifact regions
3. **Stain norm mandatory** cross-site
4. **Patch extraction at correct units** (`'power'` for magnification, not `'level'`)
5. **Overlap stride** to handle boundary nuclei
6. **Multi-resolution analysis** (tissue at 5×, cells at 40×)
7. **Pretrained model domain check** before applying — PanNuke ≠ all tissue types
