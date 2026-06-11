---
case_id: omics-002-scrna-kang-ifnb-integration
modality: scRNA_seq
study: Kang et al 2018, Multiplexed droplet single-cell RNA-seq
public_accession: GSE96583
doi: 10.1038/nbt.4042
organism: Homo sapiens
tissue: PBMC (control vs IFN-β-stimulated)
tools:
- Scanpy 1.10
- scvi-tools 1.1
- harmonypy 0.0.10
status: validated
validated: true
source: praxis_seed
study_design: case_control_paired
assay_subtype: 10x_chromium_v2
cell_type_focus:
- PBMC_immune
method_choice:
- harmony
- scvi
- bbknn
- MAST_pseudobulk
case_class: success
---

# Kang IFN-β：condition 整合的标准教案

## Background
Kang 2018 用 demuxlet 分配 8 个供体的 PBMC，做 ctrl 与 IFN-β 刺激配对实验。是测试"如何在保留 IFN-β 反应（real biological signal）同时去掉 batch/donor 效应"的金标准基线。

## What I actually did
1. 读 control + stim 两个 sample，注释 `obs['condition'] = ctrl|stim`、`obs['donor']`
2. **不能 naive concat 直接聚类**——会按 condition 分群（IFN response 太强）
3. **三种整合策略对比**：
   - **Harmony**（`harmonypy.run_harmony(pca, batch='donor', vars_use=['donor'])`）：快、保留 condition 差异，但对极端 batch 偏差校正不彻底
   - **scVI**（`scvi.model.SCVI(adata, batch_key='donor')`），训练 400 epochs，latent dim=10：拓扑最干净，但要 GPU + 训练时间长
   - **BBKNN**：最快但 cluster 边界软，适合探索不适合 final
4. **关键决策：batch_key 设 donor 还是 condition？设 donor**——condition 是想保留的生物学差异，把它放 batch_key 会被洗掉
5. 整合后 Leiden 0.5 → 注释（同 case-001 marker 集）→ **per-cell-type DE：MAST 模型 + condition 作 fixed effect + donor 作 random effect**
6. IFN response signature（ISG15/IFI6/IFIT1/MX1）在所有 cell types 升高，CD14 mono 最强（与原文一致）

## ★ 排除/不做的事
- **batch_key 设 condition**：把生物学差异当 batch，IFN signature 全部消失
- **`sc.pp.combat()` 先 batch correct 再算 HVG**：HVG 选择会偏向 batch 而非生物学
- **Wilcoxon test 单细胞 DE**：忽略伪重复（pseudoreplication），p value 过乐观；要做 pseudobulk → DESeq2 或 MAST 含 random effect
- **scVI 不设 `batch_key`**：等于不整合

## ★ 失败模式
- **Pseudoreplication**：每个细胞当独立 sample 是单细胞 DE 最大坑——8 个 donor 不是 ~8000 个独立观察
- **整合过度**：IFN-β 反应的真实生物学差异被 Harmony/scVI 洗成几乎无差。判断标准：ISG15 在 stim vs ctrl 的 log2FC 应 ≥ 2.5；< 1 表示过度校正
- **Donor effect heterogeneity**：8 个供体响应强度不一致，部分会被当 outlier 移除——其实是真生物学

## ★ QC sanity check (known answer)
- Anchor (Kang IFN-β GSE96583)：
  - **ISG15** stim/ctrl pseudobulk LFC ≥ 2.5 在 CD14 monocytes (强 IFN response)
  - IFI6, IFIT1, MX1 同向上调
  - Cell type 数量 (T/B/NK/mono/DC) **不被 condition 撕裂**：每个 cluster 含 ctrl + stim 两侧细胞
  - kBET batch (donor) mixing ≥ 0.5
- Pass criterion：ISG15 LFC ≥ 2.5 AND every cell type cluster has both ctrl + stim cells
- Fail criterion：ISG15 LFC < 1.0 → integration over-correction（batch_key 错设 condition?）

## Lessons → seeds for rules
1. **batch_key 选择 = 想消的变量**；想保留的生物学**不要**进 batch_key
2. **整合方法多比一比**：Harmony 快做基线、scVI 做 final、BBKNN 探索；single method 是 red flag
3. **DE 必须做 pseudobulk 或带 random effect**，不能 naive Wilcoxon
4. **整合质量量化**：kBET（batch mixing）+ ISG signature 保留度（生物学保留），两个指标都看
