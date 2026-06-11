---
case_id: cell-002-hcs-hit-calling
schema_version: 1
task: high_content_screening_hit_identification
input_data: 96-well or 384-well plate × per-cell features × compound
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: generic_cell_line
assay_format: 384well
channel_count: 4
dataset_accession: null
antibodies_rrid: []
software_versions:
  cellprofiler: ">=4.2"
  cellprofiler_analyst: ">=3.0"
  scikit-learn: ">=1.0"
tools: [CellProfiler Analyst, scikit-learn, plate normalization (Bscore, NPI), z-score, SSMD]
key_paper_doi: 10.1177/1087057103258285
provenance:
  source_type: literature
  doi: 10.1177/1087057103258285
  citation: "Brideau C et al. Improved statistical methods for hit selection in high-throughput screening. SLAS Discov. 2003;8(6):634-647."
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
tags: [hcs, high_content_screening, plate_normalization, b_score, ssmd, z_score, hit_calling, edge_effect]
status: validated
---

# HCS hit calling：z-score / B-score / SSMD 三方法对比

## Background
High-content screening (HCS) = 化合物 library × 96/384-well plate × multi-feature image analysis → hit calling。**plate effect** （edge effect / drift / bias）严重影响。**hit calling**：normalize → score → cutoff。

## What I actually did
1. **Per-cell features → per-well summary**：median intensity / cell count / phenotype score
2. **Plate normalization**：
   - **NPI (Normalized Percent Inhibition)**：(well - neg_ctrl) / (pos_ctrl - neg_ctrl)
   - **Z-score**：(well - plate_median) / plate_MAD
   - **B-score**：median polish removes row + col effect → z-score residual
   - **SSMD (Strictly Standardized Mean Difference)**：(μ_test - μ_ref) / sqrt(σ²_test + σ²_ref)
3. **Edge effect detection**：visualize plate map → corner / edge wells systematically high/low
4. **Hit threshold**：|z-score| > 3 OR |SSMD| > 2 OR top 1%
5. **Plate / batch effect normalization**：跨 plate combine 后 quantile normalize
6. **Hit deduplication**：duplicate compound 在 multiple plate confirmation
7. **Pathway / mode-of-action analysis**：cluster hit by phenotype profile (multi-feature)
8. **Output**：hit list + replicate confirmation + dose-response triage candidate

## ★ 排除/不做的事
- **Z-score without plate normalization**：edge effect 假阳率高
- **B-score 当 default for all**：B-score 假设 row/col effect dominant，不 always true
- **Single replicate hit calling**：noise，至少 2 replicate confirm
- **No DMSO / pos-ctrl**：normalization 没 anchor
- **Per-pixel feature for HCS**：per-cell median 才对
- **Hit cutoff 一刀切**：strong assays |z| > 3，weak signals 可能 |z| > 2 是 hit

## ★ 失败模式
- **Edge well evaporation**：边缘 well evaporate 让 concentration 升 → false hit
- **Cell density effect**：seeding density 不一让 readout 偏
- **Compound autofluorescence**：化合物本身 fluorescent → false positive
- **Cytotoxic compound mask**：toxic compound 杀 cell → 显示 phenotype change 但是 死 not 真 effect
- **Color channel bleedthrough**：multi-channel 不 compensate
- **Cherry-picking from single experiment**：reproducibility check 必须

## Lessons → seeds for rules
1. **Plate normalization (B-score) + z-score** combine
2. **Multiple replicate** confirm
3. **Edge effect QC** mandatory
4. **DMSO + pos ctrl anchor**
5. **Cytotoxic filter**：hit 不能 cell count 急降
6. **Autofluorescence filter**：control well per compound 平行
7. **Multi-feature phenotype profile** for MoA cluster
