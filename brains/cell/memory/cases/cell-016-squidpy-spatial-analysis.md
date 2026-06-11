---
case_id: cell-016-squidpy-spatial-analysis
schema_version: 1
task: spatial_proteomics_cell_typing_neighborhood
input_data: per-cell coordinates + cell-type labels (from Mesmer/Cellpose) + spatial neighborhood graph
image_modality: CODEX
sample_dimension: 2d_tissue
cell_type: tonsil_tissue
assay_format: slide
channel_count: 38
dataset_accession: null
antibodies_rrid:
  - RRID:AB_2864355
  - RRID:AB_2895089
  - RRID:AB_2895091
software_versions:
  squidpy: ">=1.4"
  scanpy: ">=1.10"
  anndata: ">=0.10"
tools: [Squidpy, scimap, scanpy, anndata, scikit-image]
key_paper_doi: 10.1038/s41592-021-01358-2
provenance:
  source_type: literature
  doi: 10.1038/s41592-021-01358-2
  citation: "Palla G et al. Squidpy: a scalable framework for spatial omics analysis. Nat Methods. 2022;19(2):171-178."
  extracted_at: 2026-04-30
  extraction_confidence: high
  unverified_details: []
tags: [squidpy, spatial_omics, neighborhood_enrichment, ripley, anndata, scanpy_compatible, multi_modal]
status: validated
---

# Squidpy：spatial omics 标准 neighborhood + colocalization 分析框架

## Background
Squidpy（Palla 2022 Nat Methods）是 scanpy 生态中专门处理空间数据的库，覆盖 Visium / Slide-seq / MERFISH / CODEX / IMC 多模态。**核心**：把 cell coords + cell type 表达成 AnnData，然后跑 (1) neighborhood enrichment (Z-scored count-based)；(2) co-occurrence (distance-conditional probability)；(3) Ripley's L/F/G statistics；(4) interaction matrix。

## What I actually did
1. **Input**：从 Mesmer/Cellpose 上游拿 per-cell coords + types → 构建 `AnnData`（X = marker matrix, obs = cell_type labels, obsm['spatial'] = xy coords）
2. **Build neighbor graph**：`sq.gr.spatial_neighbors(adata, coord_type='generic', delaunay=True)`（或 KNN k=6）
3. **Neighborhood enrichment**：`sq.gr.nhood_enrichment` → permutation-based Z-score 矩阵（每对 cell type 邻居 enrichment）
4. **Co-occurrence**：`sq.gr.co_occurrence` → conditional P(type B | type A within distance d)
5. **Ripley's statistics**：`sq.gr.ripley(adata, mode='L')` — single-type clustering 趋势
6. **Interaction matrix**：直接邻居 contact 频率
7. **Visualize**：`sq.pl.nhood_enrichment` 热图 + `sq.pl.spatial_scatter` overlay
8. **Validation**: tonsil germinal center → CD20+ B 与 CD20+ Ki67+ B 邻居 enrichment Z-score 应显著正

## ★ 排除/不做的事
- **Direct on per-pixel image**：Squidpy 输入是 per-cell；上游 segmentation 必先跑
- **Neighbor graph without coord_type spec**：generic vs grid (Visium spot) 用不同参数
- **Ripley alone for all clustering**：L 函数受 edge effect 严重影响，必须 edge correction
- **Co-occurrence at single distance**：必须 sweep multiple distances 看 plateau
- **Interpret enrichment without permutation**：raw count 受 type frequency 影响；必须 permutation Z-score
- **Run Squidpy on unannotated clusters**：cell type 必须事先 annotate（rule 04 双方法）
- **跨 sample combine without batch correct**：不同 slide 的 cell 数差异 → enrichment 不可比

## ★ 失败模式
- **Edge effect**：tissue 边界 cell 邻居 incomplete → enrichment biased
- **Rare cell type underestimated**：cell count < 50 → permutation noise dominate
- **Tissue artifact (folds/tears)**：missing region 让 distance metric 偏
- **Cell type label noise**：knowledge-based threshold 错让全局邻居矩阵偏
- **Slide-to-slide variance**：normalize 不充分 → 跨样本 meta-analysis 失败
- **Distance unit confusion**：pixel vs μm；Squidpy 默认 pixel；必须 convert

## Lessons → seeds for rules
1. **AnnData as canonical handoff** between segmentation → spatial analysis
2. **Neighbor graph type explicit** (delaunay / knn-k / grid)
3. **Permutation Z-score** for enrichment (raw count misleading)
4. **Multi-distance co-occurrence** to find scale of organization
5. **Edge correction** for Ripley
6. **Cell type annotation upstream** — Squidpy assumes labels
7. **Per-slide normalize** before cross-sample meta-analysis
