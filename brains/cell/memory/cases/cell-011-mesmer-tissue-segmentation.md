---
case_id: cell-011-mesmer-tissue-segmentation
schema_version: 1
task: cell_segmentation_fluorescence
input_data: multiplex tissue image (CODEX / IMC / IF), nucleus + membrane channels
image_modality: fluorescence
sample_dimension: 2d_tissue
cell_type: tonsil_tissue
assay_format: slide
channel_count: 2
dataset_accession: null
antibodies_rrid: []
software_versions:
  mesmer: ">=0.4"
  deepcell: ">=0.12"
  tissuenet: ">=1.0"
tools: [Mesmer (deepcell), TissueNet, DeepCell, scikit-image, Napari]
key_paper_doi: 10.1038/s41587-021-01094-0
provenance:
  source_type: literature
  doi: 10.1038/s41587-021-01094-0
  citation: "Greenwald NF et al. Whole-cell segmentation of tissue images with human-level performance using large-scale annotation and deep learning. Nat Biotechnol. 2022;40(4):555-565."
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
tags: [mesmer, tissuenet, tissue_segmentation, deepcell, nucleus_membrane, multiplex, codex, imc]
status: validated
---

# Mesmer / TissueNet：tissue context segmentation（Cellpose 是 single-cell）

## Background
Mesmer（Greenwald 2022 Nat Biotech）训练在 **TissueNet**（>1M annotated cells across 9 tissue types with paired nucleus + membrane channels）→ tissue 影像通用 segmentation。**与 Cellpose 区别**：(1) 训练数据来自 tissue（非 monolayer cell line）；(2) requires both nucleus + membrane channels；(3) 输出 nucleus mask + whole-cell mask 双层；(4) 在 multiplex (CODEX/IMC) 上 SOTA。

## What I actually did
1. **Input**: 2-channel tissue image — channel 1 = nucleus (DAPI / DRAQ5 / Iridium-DNA1 for IMC); channel 2 = membrane (CD45 / E-cadherin / pan-cytokeratin)
2. **Model selection**: Mesmer pre-trained `whole-cell` model (no fine-tuning needed for typical tissue)
3. **Pre-process**: optional histogram normalize per channel; downsample for very large WSI
4. **Inference**: `app.predict(image, image_mpp=0.5)` — **explicit `image_mpp`**（microns-per-pixel）必填，模型按此 scale 输入
5. **Output**: `nucleus_mask` + `whole_cell_mask` (cytoplasm derived as wholecell - nucleus)
6. **Per-cell features**: marker quantification within whole_cell mask; nucleus / cytoplasm ratio computable
7. **Validation**: Greenwald 2022 reports F1 ≥ 0.85 vs human annotators on TissueNet test split; tonsil sub-domain F1 ≈ 0.88

## ★ 排除/不做的事
- **Cellpose default for tissue context**：Cellpose 训练于 single-cell / monolayer，组织上下文表现下降 ~10%
- **Single channel input**：Mesmer 强制要求 nucleus + membrane 双 channel；缺一报错
- **Forget `image_mpp`**：默认 0.5 μm/px 会让 0.325 (Akoya 20×) 数据 over-segment
- **Mesmer for organoid 3D**：Mesmer is 2D only；3D 用 Cellpose 3D
- **No tissue-domain finetune for novel tissue**：默认 model 在 brain/spinal-cord 表现下降，需 finetune

## ★ 失败模式
- **Membrane signal gradient**：tissue 中 membrane 强弱不均（centro vs perif）
- **Touching cells in tightly-packed epithelium**：仍需后处理 split
- **Cell death / apoptosis**：dying cells 形态异常 → 假分割
- **Auto-fluorescence of erythrocytes**：blood vessel 假阳
- **Fixation artifacts**：folded / torn region segmentation 不可信
- **Very large WSI**：>1 GB image 需 tile + stitch（boundary cells 处理）

## Lessons → seeds for rules
1. **Tissue context → Mesmer; single-cell context → Cellpose**
2. **Nucleus + membrane dual channel** mandatory
3. **`image_mpp` explicit**（不能默认）
4. **Tile + stitch** for WSI（boundary cell merge）
5. **Tissue-specific finetune** for novel tissue types
6. **F1 ≥ 0.85** as production threshold
7. **Per-cell: nucleus + whole-cell + cytoplasm** triple mask
