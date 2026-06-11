---
rule_id: 04-tissue-vs-single-cell
schema_version: 1
scope: case_distilled
applies_to:
  cell_task:
    - cell_segmentation_fluorescence
    - spatial_proteomics_cell_typing_neighborhood
    - imaging_mass_cytometry_multiplex
    - histology_nuclear_segmentation_classification
  image_modality: ALL
  sample_dimension:
    - 2d_tissue
    - 2d_single_cell
evidence_cases:
  - cell-003-codex-spatial-proteomics
  - cell-009-imc-multiplex
  - cell-011-mesmer-tissue-segmentation
  - cell-014-hovernet-histology
confidence: high
rule_type: domain_routing
---

# Tissue context vs single-cell — 工具/参数/QC 分流

来自 4 篇真实文献：CODEX tonsil（cell-003）、IMC（cell-009）、Mesmer/TissueNet（cell-011）、HoVer-Net H&E（cell-014）。

## 核心区分

**Tissue context** ≠ **single-cell（cell line dish/well）**。同样的 segmentation/profile 算法在两种 setting 表现差距 10-30%。

| 维度 | single-cell（dish/well） | tissue（slide/section） |
|---|---|---|
| 细胞分布 | well-separated, ~1 layer | tightly-packed, multi-layer, 多 cell type 混合 |
| 染色穿透 | 均匀 | depth gradient, fold artifact, tear |
| Background | 低（DMSO well） | autofluorescence (RBC, lipofuscin, collagen) |
| Cell shape 异质性 | 中（cell line） | 极高（B/T/macrophage/stroma/tumor） |
| Reference annotation | 化合物已知 | 组织结构已知（germinal center / stroma / tumor stroma） |

## 决策表（按 image_modality × sample_dimension）

| modality | dimension | **tool 路径** | 必备 QC | 凭据 |
|---|---|---|---|---|
| fluorescence | 2d_single_cell | **Cellpose 3** (cyto2/cyto3) | border cell filter, illumination correction | cell-001 |
| fluorescence | 2d_tissue (multiplex IF/CODEX) | **Mesmer (TissueNet)** | nucleus + membrane channel 双 input；image_mpp explicit；marker QC per cycle | cell-003, cell-011 |
| brightfield | 2d_tissue (H&E) | **HoVer-Net** | stain normalization (Macenko/Vahadane)；tile + stitch；pen mark filter | cell-014 |
| IMC | 2d_tissue | **Steinbock pipeline + Mesmer** | hot pixel removal MANDATORY；arcsinh；isobaric overlap check | cell-009 |
| CODEX | 2d_tissue | **Mesmer + scimap** | spectral bleedthrough correction；marker validation per cycle；arcsinh | cell-003 |

## ❌ 禁用模式（Reviewer 必拦）

1. **Cellpose for tissue context** — Cellpose 训练 single-cell；tissue 性能掉 ~10%（cell-003, cell-011）
2. **Mesmer for organoid 3D** — Mesmer 是 2D；3D 用 Cellpose 3D（cell-008, cell-011）
3. **Mesmer single-channel input** — 强制 nucleus + membrane 双 channel；缺一报错（cell-011）
4. **CellProfiler default for H&E** — CellProfiler 是 fluorescence-oriented；H&E 用 HoVer-Net（cell-014）
5. **One-class classifier for histology** — HoVer-Net 5-class（neoplastic/stromal/immune/dead/non-neoplastic-epithelial）远比 binary 实用（cell-014）
6. **No spatial sanity check** for spatial proteomics — 必须 known structure recover（germinal center 应富 CD20+B + Ki67）（cell-003）
7. **Single cycle marker validation skipped**（CODEX/IMC）— 每 cycle 抗体性能不一；marker QC 必跑（cell-003, cell-009）

## ★ Tissue 分析必经流程

```
tissue image (multiplex/H&E)
  → stain norm (H&E only) / cycle alignment (CODEX) / hot pixel filter (IMC)
    → arcsinh transform (multiplex) / RGB color deconvolution (H&E)
      → tissue-aware segmentation (Mesmer / HoVer-Net)
        → nucleus + whole_cell mask 双层
          → per-cell marker quantification
            → cell typing (knowledge-based + unsupervised cluster, rule 03)
              → spatial neighborhood / tissue domain detection
                → known-biology validation (germinal center / tumor margin / immune zone)
```

## ★ Validation gates

| Modality | Validation |
|---|---|
| CODEX tonsil | germinal center cluster contains CD20+ B + Ki67 |
| IMC | hot pixel ratio post-filter ≤ 0.001 |
| Mesmer | F1 ≥ 0.85 (TissueNet baseline) |
| HoVer-Net | classification accuracy ≥ 0.65 (PanNuke baseline) |

## 边界（rule 不适用）

- Single-cell suspension imaging (cytometry, not microscopy) → 不在 PRAXIS-Cell scope
- 3D tissue z-stack → rule 01 (3D tools) 优先；本 rule 仅覆盖 2D tissue
- iPSC organoid colony — 用 Cellpose / 3D-organoid-segment（rule 01），不用 tissue tools
