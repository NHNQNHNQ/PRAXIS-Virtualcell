---
case_id: omics-006-spatial-slideseq-cerebellum
modality: spatial_transcriptomics
study: Stickels et al 2021, Slide-seqV2
public_accession: GSE158450
doi: 10.1038/s41587-020-0739-1
organism: Mus musculus
tissue: cerebellum
tools:
- Squidpy 1.4
- cell2location 0.1.4
- Tangram
- Scanpy
status: validated
validated: true
source: praxis_seed
study_design: reference_atlas
assay_subtype: slide_seq_v2
cell_type_focus:
- cerebellum_neuron
- Purkinje
- granule
method_choice:
- cell2location
- tangram
- squidpy
case_class: success
---

# Slide-seqV2 cerebellum：spatial deconvolution + 邻域分析

## Background
Slide-seqV2 提供 ~10μm 分辨率 spatial transcriptomics（每个 bead ~1-2 cells）。小鼠小脑层级清晰（molecular/Purkinje/granule layer），是 deconvolution 算法测试金标准——Purkinje 极少（~2%）但功能关键，能不能检出来是检验。

## What I actually did
1. 读 bead × gene matrix + bead spatial 坐标 `(x, y)`，作 AnnData with `obsm['spatial']`
2. **不直接当 single-cell 处理**——每个 bead 是 mixture，传统 cell type calling 失效
3. **Reference scRNA-seq 必备**：Saunders 2018 mouse brain atlas（DropViz）的小脑子集——cell type granularity 决定 deconvolution resolution
4. **cell2location**：贝叶斯 deconvolution，先训 reference 模型（cell type signature）→ map 到 spatial（NB 模型 + 空间先验）。GPU 训练，~30 min
5. **Tangram** 做对比：空间映射 / map cells to spots，不假设 mixture。两个方法 spot 上 cell type proportion 应大致一致；分歧 spot 标 review
6. **空间分析**：Squidpy `gr.spatial_neighbors` → `gr.nhood_enrichment`（邻接 enrichment）。期望 Purkinje 与 Bergmann glia 共定位（已知生物学）
7. **Spatially variable genes**：Moran's I 或 SpatialDE → 找出沿层级梯度变化的基因
8. Validation：marker（Calb1 Purkinje、Gabra6 granule）应空间限定到对应层

## ★ 排除/不做的事
- **Bead 当单细胞**走 Leiden + UMAP：底层 mixture 假设破坏，cluster 解读虚假
- **不用 reference 单跑 NMF/factor analysis**：得 spatial pattern 但无法对到生物学
- **HVG 选择忽略空间**：用 Moran's I 选 spatially variable genes 比 mean-variance HVG 更适合 spatial
- **跨 puck/section concat 不校正**：每个 puck 是独立 batch，z 方向（连续切片）也要建模
- **小细胞类型 deconvolution 信任度高**：< 1% 的 cell type 检出极不可靠，需要 robustness check

## ★ 失败模式
- **Reference / spatial 物种 strain 不匹配**：B6 atlas 部署到 BALB/c spatial 数据，部分 marker 失效
- **Bead pollution**：实验上 bead 偏离原位置（physical drift），形成假"跨层"信号
- **Layer boundary blur**：deconvolution 在层界面 spot 给的 proportion 不是真 mixture，是算法不确定性——需要 confidence interval 输出
- **Negative binomial overdispersion**：cell2location 的 NB 模型对 high-expression 基因（rRNA contamination）拟合差
- **Purkinje sparse 检出 0%**：reference signature 弱 → deconvolution 不出来，看似无 Purkinje。要看 reference matrix 中该 cell type 表达量

## ★ QC sanity check (known answer)
- Anchor (Slide-seqV2 cerebellum GSE158450)：
  - **Calb1** 空间限定到 Purkinje cell layer（在小脑层级 = 中间薄层）
  - **Gabra6** 限定到 granule cell layer（最厚层）
  - cell2location + Tangram 共识：> 75% spot 上 top cell type 一致
  - Squidpy nhood_enrichment：Purkinje 与 Bergmann glia 共定位（已知生物学）
- Pass criterion：Calb1 spatial ≥ 80% in Purkinje layer + 共识率 > 75%
- Fail criterion：Calb1 全 puck 散布 → reference scRNA 缺失或不匹配；共识率 < 60% → 单方法不可信

## Lessons → seeds for rules
1. **Spatial deconvolution 必须有 paired scRNA reference**，且 cell type granularity 决定空间分辨率
2. **跑 ≥ 2 deconvolution 方法**（cell2location + Tangram 或 + RCTD），分歧 spot 标 review
3. **空间分析三件套**：邻域 enrichment + spatial autocorrelation（Moran's I）+ ligand-receptor（CellChat/COMMOT）
4. **HVG 改用 spatially variable gene selection**（SpatialDE/SpaGCN）
5. **Puck/section batch 必须建模**——平面 + z 方向都是 batch
