---
case_id: cell-006-dose-response-fitting
schema_version: 1
task: dose_response_curve_fitting
input_data: per-compound × per-concentration × % effect
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: generic_cell_line
assay_format: 384well
channel_count: 2
dataset_accession: null
antibodies_rrid: []
software_versions:
  drc: ">=3.0"
  scipy: ">=1.11"
  graphpad_prism: ">=9.0"
tools: [drc R package, GraphPad Prism, scipy.optimize, Hill equation, four-parameter logistic]
key_paper_doi: 10.1371/journal.pone.0146021
provenance:
  source_type: literature
  doi: 10.1371/journal.pone.0146021
  citation: "Ritz C et al. Dose-response analysis using R. PLoS One. 2015;10(12):e0146021."
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
tags: [dose_response, ec50, hill_coefficient, four_parameter_logistic, drc, curve_fitting, potency]
status: validated
---

# Dose-response 拟合：EC50 + Hill coefficient + 拟合质量

## Background
Dose-response 是 cell-based assay 标准 deliverable。**Four-parameter logistic (4PL)** 模型: y = bottom + (top - bottom) / (1 + (EC50/x)^Hill)。Output：EC50 (potency)、top/bottom (efficacy)、Hill (cooperativity)。**陷阱**：dose range 不充分 → bottom/top 不收敛 → EC50 不可信。

## What I actually did
1. **Data**：8-12 concentration × 3 replicate per compound
2. **Concentration range**：log scale, 至少 4 orders of magnitude（preferably 10 nM to 100 μM for typical drug）
3. **Fit 4PL with drc R / scipy curve_fit**
4. **Initial guess**：bottom = min, top = max, EC50 = mid concentration, Hill = 1
5. **Quality assessment**：
   - 95% CI on EC50 not span > 10× → reliable
   - Hill ~ 1 (typical receptor); >> 1 = positive cooperativity (suspect); << 1 = bad fit
   - R² > 0.9
6. **Top / bottom plateau**：actual data must reach plateau → if not, EC50 估计 highly uncertain
7. **Outlier handling**：median of replicates, MAD-based outlier detect
8. **Output**：EC50 + 95% CI + Hill + curve plot + classification (active / inactive / partial agonist)

## ★ 排除/不做的事
- **Concentration range 不够 4 orders**：plateau 不达，EC50 假
- **Single replicate per dose**：no error estimate
- **Force fit 4PL when data 不 sigmoidal**：bell-shape / non-monotonic 用 different model
- **Top free vs fixed**：full dose-response 用 free top；short range 用 fixed top from positive control
- **EC50 absolute number without CI**：misleading
- **Hill not reported**：Hill ~ 4+ 通常不真，是 fit artifact 或 cooperativity rare case

## ★ 失败模式
- **Bell-shaped (non-monotonic)**：toxic at high dose / hormesis / receptor desensitization
- **Plateau 不达**：EC50 远超 max tested concentration → estimate 误差大
- **Multiple binding sites**：biphasic curve，single 4PL fit 错
- **Solubility limit**：high concentration 化合物 precipitate → effect drop apparent
- **Time of measurement**：too early signal 不达；too late confounded by death
- **Receptor reserve**：true affinity vs apparent EC50 differ for partial agonist with reserve

## Lessons → seeds for rules
1. **8-12 concentrations + 4 orders of magnitude** range
2. **3+ replicates** per dose
3. **4PL with constraints** (top, bottom physical reasonable)
4. **CI on EC50** mandatory
5. **Hill ~ 1 sanity check**, > 4 suspicious
6. **Plateau check**：if not reached, EC50 lower-bound only
7. **Bell-shape detection** before fitting
