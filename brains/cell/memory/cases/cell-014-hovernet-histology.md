---
case_id: cell-014-hovernet-histology
schema_version: 1
task: histology_nuclear_segmentation_classification
input_data: H&E whole-slide histology (multi-tissue), RGB
image_modality: brightfield
sample_dimension: 2d_tissue
cell_type: tumor_tissue
assay_format: slide
channel_count: 3
dataset_accession: null
antibodies_rrid: []
software_versions:
  hovernet: ">=1.0"
  monai: ">=1.3"
  qupath: ">=0.5"
  stardist: ">=0.8"
tools: [HoVer-Net, StarDist H&E, QuPath, MONAI Pathology, CellProfiler 4 H&E module]
key_paper_doi: 10.1016/j.media.2019.101563
provenance:
  source_type: literature
  doi: 10.1016/j.media.2019.101563
  citation: "Graham S et al. Hover-Net: Simultaneous segmentation and classification of nuclei in multi-tissue histology images. Med Image Anal. 2019;58:101563."
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
tags: [hovernet, histology, h_and_e, nuclear_segmentation, classification, brightfield, wsi, qupath]
status: validated
---

# HoVer-Net：H&E whole-slide nuclear segmentation + 类型分类

## Background
H&E (hematoxylin & eosin) 染色 brightfield histology 是病理金标准，但 nuclei 触摸 + 形态多样 + 染色异质 → 自动分割困难。**HoVer-Net**（Graham 2019 Med Image Anal）通过水平+垂直距离图（hover map）解决 touching nuclei 分割，并同时分类（neoplastic / stromal / immune / dead / non-neoplastic epithelial 5 类，按 PanNuke 训练）。

## What I actually did
1. **Input**：H&E WSI（whole-slide image，multi-GB, .svs / .ndpi / .tiff 格式）
2. **Pre-process**：tile WSI into 256x256 px patches at 40× equiv（0.25 μm/px）；stain normalization (Macenko / Vahadane) **mandatory** for cross-site/scanner variation
3. **HoVer-Net inference per tile**:
   - Branch 1: binary nucleus mask (NP)
   - Branch 2: hover map (HV) — horizontal + vertical distance from nucleus center
   - Branch 3: nuclear classification (NC) — 5-class softmax
   - Watershed using hover map → instance segmentation
4. **Tile stitching**：merge patches with overlap; resolve boundary nuclei (NP-overlap rule)
5. **Per-cell features**：area, eccentricity, hematoxylin/eosin intensity ratio, type
6. **Tissue context**：neighborhood class composition (e.g., immune-rich region vs tumor stroma)
7. **Validation**: PanNuke F1 ~ 0.66 for instance + classification jointly; Acc on classification ~ 0.78

## ★ 排除/不做的事
- **Skip stain normalization**：site-to-site H&E vary → model performance drops 10-20%
- **Process whole WSI without tiling**：~10 GB image OOM
- **Watershed alone (no hover map)**：misses touching nuclei
- **CellProfiler default for H&E**：CellProfiler is fluorescence-oriented; H&E specific tools recommended
- **One-class classifier**：HoVer-Net 5-class is more useful than binary
- **Forget tile boundaries**：boundary nuclei split incorrectly without overlap rule
- **Mix scanner / objective without finetune**：40× Aperio vs 40× Hamamatsu have different stain profile

## ★ 失败模式
- **Out-of-domain tissue (e.g., bone marrow)**: PanNuke training set didn't include
- **Necrosis / autolysis**：dead tissue → poor segmentation
- **Cytoplasm-dense areas (e.g., adipose, smooth muscle)**: nuclei sparse → false negatives
- **Pen mark / artifact**：black pen → false positives
- **Stain intensity drift**：fading slides → low NP confidence
- **Nuclei size extreme**：megakaryocytes very large; lymphocytes very small → outliers
- **Unusual cell types (RBC, melanin)**: pigmented cells confound

## Lessons → seeds for rules
1. **Stain normalization (Macenko / Vahadane)** mandatory cross-site
2. **Tile + overlap stitching** for WSI
3. **Hover map (instead of watershed alone)** for touching nuclei
4. **5-class classification** (or task-specific finetune) better than binary
5. **Per-tissue model selection**：HoVer-Net for general; finetune for niche tissues
6. **Per-tile QC**：reject ROIs with > 30% pen mark / < 5% nuclei
7. **Boundary nuclei rule** for tile stitching (e.g., ≥ 50% area in tile = keep)
