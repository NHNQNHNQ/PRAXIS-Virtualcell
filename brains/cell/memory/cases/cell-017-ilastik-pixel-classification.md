---
case_id: cell-017-ilastik-pixel-classification
schema_version: 1
task: cell_segmentation_fluorescence
input_data: any 2D/3D image with sparse manual pixel labels (foreground / background / membrane / cytoplasm)
image_modality: fluorescence
sample_dimension: 2d_tissue
cell_type: generic_cell_line
assay_format: dish
channel_count: 3
dataset_accession: null
antibodies_rrid: []
software_versions:
  ilastik: ">=1.4"
  napari: ">=0.4.19"
tools: [ilastik (Pixel Classification), Random Forest, vigra, scikit-learn]
key_paper_doi: 10.1038/s41592-019-0582-9
provenance:
  source_type: literature
  doi: 10.1038/s41592-019-0582-9
  citation: "Berg S et al. ilastik: interactive machine learning for (bio)image analysis. Nat Methods. 2019;16(12):1226-1232."
  extracted_at: 2026-04-30
  extraction_confidence: high
  unverified_details: []
tags: [ilastik, random_forest, pixel_classification, interactive_ml, steinbock_upstream, sparse_annotation, weak_supervision]
status: validated
---

# ilastik：interactive Random Forest pixel classifier

## Background
ilastik (Berg 2019 Nat Methods) 是 GUI-based interactive ML，scientist 在 image 上 sparse-paint 几条 stroke 标 class（foreground / background / membrane），后台 Random Forest 学 ~37 维 pixel feature（intensity / Gaussian smoothing / Laplacian / structure tensor / Hessian）→ probability map。**与 DL 区别**：(1) 需 0 GPU；(2) 标注成本极低（几分钟 vs DL 几千 cell）；(3) 跨模态稳（H&E / fluorescence / EM 都可）；(4) 是 IMC pipeline (Steinbock) 的 mandatory upstream pixel classifier 步骤。

## What I actually did
1. **Input**：3-channel fluorescence (DAPI + actin + membrane)；新 dataset 训 separate classifier
2. **Open ilastik Pixel Classification workflow**
3. **Feature selection**：默认 σ ∈ [0.3, 0.7, 1.0, 1.6, 3.5, 5.0, 10.0] × {Gaussian smoothing, Laplacian of Gaussian, Structure Tensor, Hessian of Gaussian eigenvalues}；可以全开（37 features）或筛
4. **Sparse annotation**：3-class（cell / membrane / background）；每 class 5-20 strokes 横跨 ~20 cells
5. **Live update**：RF 每加 stroke 重训，看 probability map 更新；迭代 5-10 轮 stroke
6. **Export**：probability map (HDF5 / TIFF) → 3-channel softmax-like 概率
7. **Downstream**：feed into CellProfiler / Cellpose hybrid，或直接 watershed-on-prob 拿 mask
8. **Cross-image apply**：trained classifier 可应用于同 dataset 其他 image（无需重训）

## ★ 排除/不做的事
- **Single feature scale**：single σ → 学不到 multi-scale；必须多 scale
- **Dense annotation (paint everything)**：浪费时间；sparse 5-20 strokes 已够
- **Cross-modality reuse**：ilastik classifier H&E vs fluorescence 不通用；必须 retrain
- **Pixel classification 当 segmentation 终点**：probability map 不是 mask；要 watershed / argmax
- **不 export feature importance**：可帮 understand RF 学到啥；调试必备
- **跨 dataset reuse without sanity check**：scanner / illumination / cell line 变 → model degrade
- **Skip ilastik for IMC**：Steinbock 默认要 ilastik 做 3-class pixel classifier（cell membrane / cytoplasm / background）

## ★ 失败模式
- **Sparse annotation imbalanced**：某 class stroke 比其他多 10× → biased classifier
- **Imbalanced cell vs background pixel ratio**：tissue 中 background 占 70% → RF 偏 negative
- **Same-cell-type variation**：dim cell vs bright cell 同 class 但 feature 差大 → 需 stroke cover both
- **Out-of-domain image**：trained on cell line, applied to organoid → 大幅 degrade
- **Computational scale**：3D large stack > 1 GB → RF feature 计算慢；分块处理
- **Annotator bias**：不同人画 stroke 风格不同；多人交叉验证

## Lessons → seeds for rules
1. **ilastik = Steinbock IMC pipeline mandatory upstream step**（cell-009 参考）
2. **Sparse > dense annotation**；5-20 strokes per class
3. **Multi-scale feature** (σ ∈ {0.3, ..., 10})
4. **Cross-image reuse OK within same dataset**；retrain on new modality / scanner
5. **Probability map ≠ mask**；下游 watershed / argmax 必需
6. **Class balance** stroke counts to avoid bias
7. **Training takes < 30 min**；scaling beyond DL training cost
