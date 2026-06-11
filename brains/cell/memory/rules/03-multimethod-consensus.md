---
rule_id: 03-multimethod-consensus
schema_version: 1
scope: case_distilled
applies_to:
  cell_task:
    - marker_colocalization_quantification
    - high_content_screening_hit_identification
    - morphological_deep_profiling
    - phenotype_landscape_clustering
  image_modality: ALL
  sample_dimension: ALL
evidence_cases:
  - cell-005-colocalization
  - cell-002-hcs-hit-calling
  - cell-007-deep-profiling
  - cell-010-phenotype-clustering
confidence: high
rule_type: multi_method_validation
---

# 多方法 consensus（避免单点失败）

来自 4 篇真实文献：colocalization 三方（cell-005 Bolte 2006）、HCS 多 normalization（cell-002）、CellProfiler+DeepProfiler 双 backend（cell-007）、UMAP+Leiden+hdbscan multi-resolution（cell-010）。

## 核心原则

**任何一个 metric 都可被 outlier / threshold / dynamic range 偏置；多方法交叉才稳。**

## 必须 multi-method 的场景表

| 场景 | 必备 ≥ N method | 凭据 |
|---|---|---|
| **Colocalization** | Pearson **AND** Manders M1/M2 **AND** Costes randomization (3-of-3 必备) | cell-005 |
| **HCS hit threshold** | B-score **AND** z-score 双报；或 z-score **AND** SSMD 双报 | cell-002 |
| **Morphological profile backend** | CellProfiler 手工 **AND** DeepProfiler embedding 双 backend cross-check | cell-007 |
| **Phenotype clustering** | Leiden **AND** hdbscan，多 resolution sweep（0.5 / 1.0 / 1.5） | cell-010 |
| **MoA prediction** | k-NN NSC distance **AND** reference compound visual anchor | cell-010, cell-015 |
| **Cell typing in spatial proteomics** | knowledge-based threshold **AND** unsupervised cluster cross-check | cell-003, cell-009 |

## ❌ 禁用模式（Reviewer 必拦）

1. **Pearson alone** for coloc — strong outlier 主导；M1/M2 + Costes 必加（cell-005）
2. **Single normalization for HCS** — z-score 单跑假阳；B-score / SSMD 至少加一（cell-002）
3. **Single feature backend for profiling** — CellProfiler 手工特征 vs DL embedding 各有偏好；双 backend 才看出 biology vs artifact（cell-007）
4. **Single resolution Leiden** — cluster boundary 与 resolution 强相关；至少 sweep 3 个（cell-010）
5. **MoA call from cluster ID alone** — 无 reference compound anchor → cluster 名号无 biological meaning（cell-010, cell-015）
6. **Single cell-typing method**（spatial proteomics）— knowledge-based 受 marker QC 限；unsupervised cluster 受 rare cell 限；双方 cross-check 才 robust（cell-003, cell-009）

## ★ Consensus reporting 强制

每个 multi-method 输出必须包含：
- 每方法独立 score（Pearson r、Manders M1、Manders M2、Costes p；或 z、B-score、SSMD）
- **方法间一致性指标**（e.g. Costes p < 0.01 同时 Pearson > 0.5 = "high confidence coloc"）
- 不一致时 explicit flag："Pearson high but Manders low → spatial adjacency without true coloc; flag for inspection"

## 数学一致性 cheat-sheet

| Coloc 三方 | 一致 |
|---|---|
| Pearson > 0.5 AND M1 > 0.5 AND Costes p < 0.01 | high |
| Pearson > 0.5 AND M1 < 0.3 AND Costes p < 0.01 | partial（spatial adjacency, compartments touching） |
| Pearson < 0.3 AND M1 < 0.3 AND Costes p > 0.05 | random |
| Pearson > 0.5 AND Costes p > 0.05 | suspicious; high signal density may inflate Pearson; not real coloc |

## 边界（rule 不适用）

- 单 channel measurement（无 coloc 概念）
- 1 plate / no replicate dataset → 无 consensus 可言，degraded 模式
- Real-time live decision（reviewer 决策预算 < 1 min）— consensus 是事后报告，不阻塞 live triage
