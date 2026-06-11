---
case_id: omics-001-scrna-pbmc10k-canonical
modality: scRNA_seq
study: 10x Genomics PBMC 10k v3 demo
public_accession: 10x_demo (analogue GSE149938)
organism: Homo sapiens
tissue: PBMC
tools:
- Scanpy 1.10
- scrublet 0.2.3
- CellTypist 1.6
status: validated
validated: true
source: praxis_seed
study_design: reference
assay_subtype: 10x_chromium_v3
cell_type_focus:
- PBMC_immune
- T_cell
- B_cell
- NK
- monocyte
- DC
method_choice:
- scanpy
- scrublet
- celltypist
case_class: success
---

# PBMC10k：scRNA-seq pipeline 的 reference 走法

## Background
10x Genomics PBMC 10k v3 是全行业 scRNA-seq 教学/基线数据集。健康供体外周血单核细胞，~11k 细胞经 CellRanger，cell type 已被反复验证（T/B/NK/mono/DC 子型清晰）。

## What I actually did
1. `sc.read_10x_mtx(...)` 读 raw matrix（不要直接读 filtered_feature_bc_matrix，先看 raw 的 knee plot 决定是否补做 ambient RNA 校正）
2. **QC**：计算 `pct_counts_mt`（`MT-` 前缀基因）、`n_genes_by_counts`、`total_counts`。阈值 `n_genes ≥ 200` + `pct_mt ≤ 15%`（**不是常说的 5%**——PBMC 单核细胞代谢活跃，5% 会切掉 30% 真实 mono）
3. **Doublet 检测在归一化之前**：`scrublet.Scrublet(counts, expected_doublet_rate=0.075)`。10x 装载量越大 doublet 越多，10k 细胞约 7-8%
4. `sc.pp.normalize_total(target_sum=1e4)` + `sc.pp.log1p()`
5. **HVG 选 2000，flavor='seurat_v3'**（需 raw counts 输入）。500 太少，会丢 pDC/cDC 子型
6. **PCA**：`n_comps=50`，但实际后续 neighbors 用 `n_pcs=30`（看 `pca_variance_ratio` 拐点；不要默认 50）
7. **Neighbors → UMAP → Leiden**：先 `resolution=0.5`，迭代 0.3–1.0；resolution=1.5 直接出会过聚导致 mono 被切 8 个 cluster 难解释
8. **注释双源**：CellTypist `Immune_All_Low.pkl` 自动 + 手工 marker（CD3E+CD8A→CD8 T；MS4A1→B；NKG7+无 CD3E→NK；CD14→classical mono；FCGR3A→non-classical mono；FCER1A→cDC2）

## ★ 排除/不做的事
- **不做 doublet 检测**：T/mono doublet 会形成"伪激活" cluster，下游误读为生物学
- **HVG=500**：rare cell types（pDC、HSPC 等占 < 0.5%）找不出来
- **leiden 0.1 一刀切**：无法分辨 CD4/CD8 子型
- **mito% 切 5%**：单核 + 激活 T 被无差别清理

## ★ 失败模式（行业反复出现）
- **Ambient RNA 漏掉**：BCR/TCR 基因在所有细胞 nonzero（cell-free RNA 污染），不上 SoupX/CellBender 的话 DE 全是 noise
- **Marker 重叠**：CD8A 在部分 NK 弱表达；MS4A1 在 plasmablast 已下调——单 marker 注释必出错
- **Batch confound**：本案例只有 1 个 sample 没有 batch，但跨实验合并时 90% 失败案例没设计 batch covariate
- **Cluster=cell type 误等**：1 cluster 可能是 1 cell type 的 2 个 state（resting vs activated）

## ★ QC sanity check (known answer)
- Anchor (PBMC10k 10x v3 demo)：
  - Mono fraction (CD14+ + FCGR3A+) 在 25-35%
  - CD3+ T cell (CD4 + CD8) 在 50-70%
  - pDC (FCER1A+, IL3RA+) 必须 > 0（HVG=2000 + leiden 0.5 才能找出来）
  - B cell (MS4A1+) ~5-10%
- Pass criterion：mono ∈ [0.25, 0.35] AND pDC count > 0 AND CD3 ∈ [0.50, 0.70]
- Fail criterion：mono < 0.20 → mito% 切太严（5% 而非 15%）；pDC = 0 → HVG 太少 (<1000)

## Lessons → seeds for rules
1. **QC 阈值组织依赖**：mito% 5%（hepatocyte/neuron）≠ 15%（PBMC mono）≠ 25%（cardio）。规则需带 organ→threshold 表
2. **Doublet 必须在归一化之前删**，否则 HVG 被污染
3. **注释 = 自动 + 至少 2 marker 手工交叉**，单一来源不接受
4. **`n_pcs` 看 elbow，不用默认值**——下游 UMAP 拓扑差异巨大
