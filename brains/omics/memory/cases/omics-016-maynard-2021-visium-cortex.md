---
case_id: omics-016-maynard-2021-visium-cortex
schema_version: 1
modality: spatial_transcriptomics
study: "Maynard et al 2021, Transcriptome-scale spatial gene expression in the human dorsolateral prefrontal cortex"
public_accession: "GSE171011 / spatialLIBD R Bioconductor package"
doi: 10.1038/s41593-020-00787-0
organism: Homo sapiens
tissue: dorsolateral prefrontal cortex
study_design: cohort_reference
assay_subtype: visium_v1
cell_type_focus: [cortical_neuron, layer_specific, glia]
tools: [SpaceRanger 1.0, scran 1.18, BayesSpace 1.0, spatialLIBD, scanpy + squidpy, harmony_for_spatial]
method_choice: [bayesspace_layer_clustering, sct_normalize_section_level, spatial_clustering_with_neighbors, deconvolution_paired_scrna]
status: validated
validated: true
source: praxis_seed
case_class: success
provenance:
  source_type: literature
  doi: 10.1038/s41593-020-00787-0
  extracted_at: 2026-04-29
tags: [visium, spatial, cortex, layer_clustering, FFPE_alternative]
---

# Maynard 2021：Visium 人脑前额叶皮层 6 层（Visium 范式 vs Slide-seqV2）

## Background
12 张 Visium 切片，3 个 donor × 4 sections each，覆盖人 dorsolateral prefrontal cortex (DLPFC)。Visium spot ~55 μm（~1-10 cells per spot，远高于 Slide-seqV2 的 ~10 μm/1-2 cells per spot），需要的 deconvolution 技术不同 — Visium spot 是真 mixture，但比 Slide-seq 更高深度。**case 006 (Slide-seqV2 cerebellum) 之外的 Visium 主流路线代表**。论文直接挑战 6 层皮层结构是否能从 transcriptomic 重建出来。

## What I actually did
1. **SpaceRanger** 处理 raw images + reads → 每个 section 的 spot × gene matrix + 空间坐标 + H&E image
2. **Per-section QC**：spot count、`detected_genes_per_spot`、`pct_mito` per section（不同 section quality 不一）
3. **Section-level batch effect**：每个 section 是独立 batch；Harmony with `batch=section` (cross-donor) 但保留 layer biology
4. **Normalization**：SCT (Seurat) 或 scran size factor — 不用简单 log-normalize（spot 大小差异）
5. **HVG**：per-section HVG → 取并集；spatially variable gene 用 SpatialDE
6. **Layer clustering**：**BayesSpace** with `q=7`（6 cortical layers + WM）；空间感知 clustering 比纯 Leiden 更准确（~75% accuracy vs manual annotation）
7. **Layer marker validation**：
   - SNAP25 全 neuron
   - CUX2 / CUX1: L2-3
   - RORB: L4
   - PCP4 / FEZF2: L5
   - NTNG2 / KRT17: L6
   - MBP: WM (myelin)
8. **Cell deconvolution** (optional)：cell2location with paired scRNA reference (Allen Brain Atlas DLPFC) → 每个 spot 的 cell type composition
9. **Spatial autocorrelation**：Moran's I 找 spatially variable genes 不在 HVG 中
10. **Cross-section integration**：BayesSpace per-section + post-hoc layer label transfer

## ★ 排除/不做的事
- **跨 section 直接 concat 不校正**：每个 section 是独立 batch；不校正 → cluster 按 section 分 (not by layer)
- **用普通 Leiden 不用 BayesSpace**：丢失空间约束 → cluster 边界不沿 layer 走
- **Visium spot 当 single cell 处理**：每 spot ~5-10 cells，是 mixture
- **Layer marker 直接当 cell type marker**：SNAP25 是 layer marker 不是 cell type marker（neuron 都有）
- **Per-section 独立 BayesSpace 然后 cluster ID 直接 concat**：BayesSpace cluster ID 跨 section 不可比
- **HVG 不区分 spatial vs technical**：mitochondrial gene 也变化大但不是 spatial signal

## ★ 失败模式
- **Tissue position artifact**：tissue 在 capture area 上偏移 → 部分 spot 在边缘信号低
- **Out-of-tissue spots**：必须先用 H&E + tissue detection 过滤掉
- **Layer 数量调错**：q=4 时 L2-L4 合并；q=10 时同 layer 被切两半 — 必须用 BayesSpace `qPlot` 选 q
- **Donor effect 主导 layer signal**：3 donor 间 batch 大于 layer 差异 → integration 必做
- **FFPE-Visium 与 Fresh-Frozen Visium 不可比**：化学方法不同，bias 不同；论文用 FF
- **Cell deconvolution 分辨率限制**：rare cell type < 5% 的 spot 信号不可信
- **Spatial autocorrelation 假阳**：tissue 边缘 + 空气 boundary 制造伪 spatial pattern → 必须 mask 边缘 spot

## ★ 方法选择决策链
```
Visium 分析？
├─ Per-section QC + tissue mask（remove out-of-tissue spots）
├─ Cross-section integration → Harmony / scVI（with batch=section + donor）
├─ Layer / region clustering → BayesSpace（空间感知，比 Leiden 好）
│   ├─ 选 q（cluster 数）用 qPlot elbow
│   └─ 用 ari vs manual 验证
├─ Cell type composition (optional) → cell2location + 配对 scRNA reference
├─ Spatial gene discovery → SpatialDE / Moran's I（在 HVG 之外）
└─ Cross-section comparison → label transfer (anchor-based)，不直接 concat
```

## ★ QC sanity check (known answer)
- Anchor (Maynard 2021 DLPFC)：
  - **CUX2** 表达限定到上层 (L2-3)，向下层迅速衰减
  - **RORB** 限定到 L4（中层）
  - **PCP4 / FEZF2** 限定到 L5
  - **MBP** 限定到 WM（白质）
  - BayesSpace q=7 cluster 与 manual layer annotation **ARI ≥ 0.7**
- Pass criterion：layer marker 空间分布符合预期 + ARI ≥ 0.7
- Fail criterion：layer marker 全切片散布 → batch correction 过度或 BayesSpace 没用空间信息

## Lessons → seeds for rules
1. **Visium ≠ Slide-seq**：spot 大、mixture 多；分析路径不同（rule 07 spatial_deconvolution 的子分支）
2. **空间感知 clustering 必备**（BayesSpace / SpaGCN）：纯 Leiden 不够
3. **Per-section batch 必须建模**：跨 section 不直接 concat
4. **Layer marker ≠ cell type marker**：neurons 跨 layer 共享 cell type，但表达 layer-specific gene
5. **Tissue mask 优先**：out-of-tissue spots 必须先剔除
6. **Cell deconvolution 选 paired scRNA reference 关键**：cell type granularity = spatial resolution upper bound
