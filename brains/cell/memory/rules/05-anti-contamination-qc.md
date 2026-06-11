---
rule_id: 05-anti-contamination-qc
schema_version: 1
scope: case_distilled
applies_to:
  cell_task: ALL
  image_modality: ALL
  sample_dimension: ALL
evidence_cases:
  - cell-001-cellpose-segmentation
  - cell-002-hcs-hit-calling
  - cell-003-codex-spatial-proteomics
  - cell-009-imc-multiplex
confidence: high
rule_type: artifact_filtering
---

# Anti-contamination QC（每 design 必填 ★ excluded_artifacts）

来自 4 篇真实文献：border cell filter（cell-001）、cytotoxic + edge effect filter（cell-002）、autofluorescence + bleedthrough（cell-003）、hot pixel + isobaric overlap（cell-009）。

## 核心原则

**Image artifact 不去除会污染下游所有分析。** Reviewer 在 Design 阶段强制 `excluded_artifacts[]` 非空。本 rule 列出按 modality × format 的强制 artifact 清单。

## 必填 excluded_artifacts 矩阵（按 modality / format）

| Modality / format | 必含 excluded_artifacts | 过滤方法 | 凭据 |
|---|---|---|---|
| **任何 segmentation** | `border_cell` | post-segment touching-image-border filter | cell-001 |
| 任何 segmentation | `low_confidence_segment` | Cellpose flow_threshold / cellprob_threshold | cell-001 |
| **HCS plate (96/384/1536)** | `edge_well` | rim well (row A/H, col 1/12) flag | cell-002 |
| HCS plate | `cytotoxic_compound_well` | cell count drop > 50% → cluster separately | cell-002 |
| HCS plate | `autofluorescence_well` | parallel control well per compound (no cell, compound only) | cell-002 |
| **Live cell movie** | `motion_blur_frame` | per-frame variance check | cell-004 |
| Live cell movie | `out_of_focus_region` | focus-drift z-correction | cell-004 |
| **Coloc imaging** | `spectral_bleedthrough` | linear unmixing or single-label control | cell-005 |
| **3D organoid** | `out_of_focus_region` | depth-based illumination correction | cell-008 |
| 3D organoid | `low_confidence_segment` (necrotic core) | center vs periphery flag | cell-008 |
| **CODEX** | `autofluorescence_well` | cycle 0 baseline subtract | cell-003 |
| CODEX | `spectral_bleedthrough` | adjacent-cycle marker carry-over check | cell-003 |
| **IMC** | `hot_pixel` (PROMPT-mandated MUST) | Steinbock hot-pixel filter (median + 6 MAD) | cell-009 |
| IMC | `isobaric_overlap_channel` | metal isobaric matrix in panel design | cell-009 |
| **H&E histology** | `low_confidence_segment` | pen mark / tissue fold / RBC region flag | cell-014 |

## ❌ 禁用模式（Reviewer 必拦）

1. **Empty `excluded_artifacts[]`** — schema 强制 minItems=1；空就 hard-block
2. **IMC design 无 hot_pixel artifact** — PROMPT-mandated；Reviewer 启发式 + imc-pipeline skill rc=3 双层硬拦（cell-009）
3. **HCS design 无 edge_well + cytotoxic_compound_well** — 边缘 evaporation 是常见假阳源（cell-002）
4. **CODEX design 无 spectral_bleedthrough** — adjacent cycle marker 残留是常见 false coloc 源（cell-003）
5. **Coloc design 无 spectral_bleedthrough** — channel cross-talk 直接造假 Pearson > 0（cell-005）
6. **3D design 无 out_of_focus_region**（z-stack 末端）— deeper plane 信号弱，假 ΔF（cell-008）
7. **Segmentation design 无 border_cell** — partial cell area / intensity 严重偏（cell-001）

## ★ excluded_artifact entry schema 模板

每条 entry 必须含 4 个字段：
```yaml
- type: hot_pixel        # enum: 12 值（见 schemas/design_plan.schema.json）
  reason: "IMC laser ablation 检测器 spike，1e5 单位异常值会 saturate downstream arcsinh"
  citation_case_id: cell-009-imc-multiplex
  filter_method: "Steinbock hot-pixel filter; threshold = median + 6 MAD"
```

`citation_case_id` 必须指向真实 case（rule 不替代 case 引用）。

## ★ Reviewer 启发式快查表（自动 reject 的 design）

| 触发条件 | required_repair |
|---|---|
| `image_modality=IMC` 且 design 无 `hot_pixel` artifact 或 hot-pixel-filter step | "IMC pipeline missing hot-pixel removal step" |
| `cell_task=hcs_hit_*` 且 design 无 `edge_well` artifact | "HCS plate missing edge-well filter" |
| `cell_task=marker_colocalization_*` 且 design 无 `spectral_bleedthrough` artifact | "coloc requires spectral_bleedthrough exclusion" |
| `image_modality=CODEX` 且 design 无 `spectral_bleedthrough` AND `autofluorescence_well` | "CODEX requires bleedthrough + autofluorescence controls" |
| `sample_dimension=time_lapse` 且 design 无 `motion_blur_frame` | "live cell missing motion-blur QC" |
| `sample_dimension=3d_organoid` 且 design 无 `out_of_focus_region` | "3D z-stack missing depth QC" |
| 任何 segmentation pipeline 无 `border_cell` | "segmentation missing border-cell filter" |

## 边界（rule 不适用）

- 纯 in-silico simulation（无 image artifact 概念）— excluded_artifacts 可为占位 entry
- 已 pre-processed 数据（vendor 给的 OME-TIFF + 质控报告）— 仍需 entry 但 filter_method 写 "verified upstream by vendor QC report"
