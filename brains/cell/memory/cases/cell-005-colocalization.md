---
case_id: cell-005-colocalization
schema_version: 1
task: marker_colocalization_quantification
input_data: 2-channel fluorescence (e.g., GFP-protein + organelle marker)
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: generic_cell_line
assay_format: dish
channel_count: 2
dataset_accession: null
antibodies_rrid: []
software_versions:
  fiji: ">=2.14"
  jacop: ">=2.1"
  coloc2: ">=3.0"
  scikit-image: ">=0.22"
tools: [Fiji JACoP / Coloc 2, scikit-image, ImageJ Mander's, Costes randomization]
key_paper_doi: 10.1111/j.1365-2818.2006.01706.x
provenance:
  source_type: literature
  doi: 10.1111/j.1365-2818.2006.01706.x
  citation: "Bolte S, Cordelières FP. A guided tour into subcellular colocalization analysis in light microscopy. J Microsc. 2006;224(Pt 3):213-232."
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
tags: [colocalization, pearson, manders, costes, subcellular, organelle_marker, two_channel, randomization]
status: validated
---

# Colocalization：Pearson / Manders / Costes randomization

## Background
两 fluorescent marker 共定位是 cell biology 常问问题（蛋白 X 在 ER vs Golgi vs mitochondria？）。**Pearson r** measure correlation；**Manders M1/M2** measure overlap（一 channel 中信号 fraction overlap with other channel）；**Costes randomization** 给 statistical significance。

## What I actually did
1. **Image prep**：subtract background per channel (rolling ball)，crop to relevant cell region
2. **Pearson correlation r**：每 pixel 两 channel intensity correlation
   - r = 1: perfect coloc
   - r = 0: random
   - r = -1: anti-coloc
3. **Manders M1, M2**：
   - M1 = Σ (ch1_pix where ch2 > threshold) / Σ ch1
   - M2 same with channels swap
4. **Threshold determination**：Otsu / Costes auto-threshold（避 manual bias）
5. **Costes randomization**：scramble pixel positions in one channel, recompute r → distribution → P value
6. **Per-cell**：mask 每 cell 单算，distribution → reduce bias from 异质 cell
7. **3D vs 2D**：z-stack 时 3D coloc more accurate, 2D projection 有 false coloc

## ★ 排除/不做的事
- **Whole-image average coloc**：mixed cell types confound; per-cell required
- **Manual threshold without auto-method**：bias
- **Pearson alone**：strongly affected by outlier; M1/M2 + Costes 必需
- **2D projection 当 3D**：z-projected 3D 给 false high coloc
- **No background subtraction**：autofluorescence inflate coloc
- **Spectral bleedthrough not corrected**：channel cross-talk false coloc
- **Photobleaching不一致**：channel 1 vs channel 2 bleach rate 差让 Pearson 偏

## ★ 失败模式
- **Resolution-limited coloc**：diffraction limit ~250 nm，below 这 vesicle 内不可分
- **Spatially adjacent vs co-localized**：邻近 ≠ 共定位（same compartment vs touching compartment）
- **Sparse signals**：low intensity Pearson noise
- **Different exposure times**：channels imaged sequentially with different settings 给 bias
- **Compartment 大小 difference**：ER (large network) vs vesicle (small) 影响 Manders interpretation
- **Bound vs free fraction confound**：cyto + organelle 同时 bind

## Lessons → seeds for rules
1. **Pearson + Manders M1/M2 + Costes 三方**
2. **Auto-threshold (Costes)**
3. **Per-cell quantification**
4. **3D imaging > 2D** for accurate coloc
5. **Spectral bleedthrough correction** mandatory
6. **Background subtraction** preprocessing
7. **Resolution awareness** (diffraction limit ~250 nm)
