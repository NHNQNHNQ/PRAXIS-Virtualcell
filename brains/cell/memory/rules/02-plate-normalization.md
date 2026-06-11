---
rule_id: 02-plate-normalization
schema_version: 1
scope: case_distilled
applies_to:
  cell_task:
    - high_content_screening_hit_identification
    - morphological_deep_profiling
    - phenotype_landscape_clustering
    - dose_response_curve_fitting
  image_modality: ALL
  sample_dimension: ALL
  assay_format:
    - 96well
    - 384well
    - 1536well
evidence_cases:
  - cell-002-hcs-hit-calling
  - cell-007-deep-profiling
  - cell-010-phenotype-clustering
  - cell-015-bbbc021-caicedo-profiling
confidence: high
rule_type: normalization_strategy
---

# Plate / batch 归一化策略（HCS、Cell Painting、phenotype landscape）

来自 4 篇真实文献：HCS B-score/SSMD（cell-002 Brideau 2003）、DeepProfiler（cell-007）、phenotype landscape（cell-010）、BBBC021/Caicedo profiling（cell-015 Caicedo 2017 Nat Methods）。

## 决策表（按 plate format × signal scale）

| 任务 | 单 plate norm | 跨 plate harmonize | 凭据 |
|---|---|---|---|
| HCS hit calling, |z|>3 strong assay | **B-score**（median polish row+col）+ z-score 双报 | quantile normalize | cell-002 |
| HCS marginal hits, weaker SNR | **SSMD** ≥ 2 (preferred) or NPI | per-batch z-score | cell-002 |
| Cell Painting morphological profile | **per-plate DMSO median + MAD**（robust z-score） | NSCB-aware quantile norm | cell-007, cell-015 |
| Phenotype landscape (UMAP/Leiden) | per-plate median + MAD | sphering / PCA-whitening before clustering | cell-010, cell-015 |
| Dose-response | normalize to plate DMSO + pos ctrl baseline | NA (per-compound) | cell-006 |

## ❌ 禁用模式（Reviewer 必拦）

1. **z-score 不 plate-normalize** — edge effect / row gradient / column drift 让全部 z 偏，假阳率高（cell-002）
2. **B-score 当 default for all** — B-score 假设 row/col effect 主导，不是所有 plate 都成立（cell-002）
3. **mean cell aggregation per well**（不用 median）— 单 outlier cell 拉偏 well-level summary（cell-007）
4. **Per-image profile**（不用 per-well）— image-to-image variability noise inflates variance（cell-007）
5. **No DMSO / no pos ctrl** — normalization 没 anchor；任何 plate 必须 ≥ 12 DMSO + ≥ 4 pos ctrl wells（cell-002）
6. **同 plate 内 single replicate 化合物** — noise 高；至少 2 replicate per plate confirm（cell-002, cell-015）
7. **Cytotoxic compound 不分离打标** — generic cell-death phenotype 污染 specific MoA cluster（cell-007, cell-010）
8. **跨 plate 简单 z-score**（不 batch-correct）— batch effect 主导而非 biology（cell-015）

## ★ 必备 QC（每 plate 出 design 前查）

- DMSO well z 中位数 ∈ [-0.3, 0.3]（B-score 后） — 过此即 plate failed
- Pos ctrl well z > 3 — 否则 assay 没 dynamic range
- Edge effect plot：corner / rim wells 视觉检查；evaporation 必弃
- Cell count drop > 50% in well → cytotoxic flag → MoA cluster 中 separate

## ★ 强制流程顺序

```
per-cell features
  → per-well median (NOT mean)
    → per-plate B-score / DMSO median+MAD
      → cross-plate quantile norm OR NSCB-aware sphering
        → MoA cluster / hit call
```

## 边界（rule 不适用）

- 单 plate < 24 wells（如 24-well）→ B-score row/col 假设不稳，用 z-score
- Time-lapse plate（每 well 时间序列）→ 用 per-well-per-frame normalize（rule 不直接覆盖）
