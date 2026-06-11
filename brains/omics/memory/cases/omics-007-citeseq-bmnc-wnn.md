---
case_id: omics-007-citeseq-bmnc-wnn
modality: CITE_seq
study: Stuart et al 2019, Comprehensive Integration of Single-Cell Data
public_accession: GSE128639
doi: 10.1016/j.cell.2019.05.031
organism: Homo sapiens
tissue: bone marrow mononuclear cells (BMNC)
tools:
- Seurat v5
- totalVI 0.7
- Scanpy + muon
status: validated
validated: true
source: praxis_seed
study_design: cohort_reference
assay_subtype: cite_seq_25abs
cell_type_focus:
- bone_marrow_immune
- HSPC
method_choice:
- seurat_wnn
- totalvi
- muon
case_class: success
---

# CITE-seq BMNC：RNA + ADT 多模态整合（WNN 标准案例）

## Background
Seurat v3/v4 论文示例数据集，~30k BMNC 同时测 RNA（17k genes）+ 25 surface antigens（ADT）。多模态整合的金标准基线——RNA 看转录状态，ADT 看蛋白表型，两者对 immune cell 注释互补。

## What I actually did
1. **两个 modality 独立 normalize**：RNA 用 log-normalize；**ADT 用 CLR**（centered log-ratio）——因每个 cell 总 ADT 数差异大但 protein composition 才有意义
2. **不要把 ADT count 直接加进 RNA 矩阵跑 PCA**——counts scale 完全不同（RNA 单基因 0-100，ADT 100-10000）会被淹没
3. **Seurat WNN（Weighted Nearest Neighbors）**：对每个 cell 学习 RNA vs ADT 的局部权重——T cell 区域 ADT CD4/CD8 权重高（well-resolved），HSPC 区域 RNA 权重高（marker 不强）
4. **替代方案 totalVI**（贝叶斯 latent，更适合 batch/donor 多的场景）：要 GPU、训练慢但 explicit modeling protein background
5. WNN UMAP → Leiden 0.6 → 注释。**关键**：annotate 时同时看 RNA marker + ADT level，不一致的 cluster（如 RNA 像 Treg 但 CD25 蛋白低）需要 review
6. **HSPC subset 重做高分辨率聚类**——干/祖细胞分化连续，需要 trajectory（Palantir/Monocle3）而非离散 cluster

## ★ 排除/不做的事
- **ADT 用 log-normalize 而非 CLR**：忽略 compositional 性质，CD4 量"高"可能只是因为 cell 总抗体多
- **WNN 只跑 RNA 当作 single-modality**：浪费昂贵的 ADT 数据
- **Isotype control 不去掉**：IgG isotype 应作 background 减除（每个 cell - mean isotype）
- **Doublet detector 只跑 RNA**：CITE-seq doublet 在 ADT 维度更可见（CD3+CD19 共阳）；要双模态联合检测
- **过度依赖 ADT 注释**：只 25 个 antigen，rare cell type panel 不覆盖（如 pDC、basophil）

## ★ 失败模式
- **Antibody capture noise**：ADT bead 残留导致 "all cells positive" 的虚假 signal——要看 ADT density plot 的 bimodality
- **Hashing 串扰**：multiplex CITE-seq 时 hash tag 跨 cell 污染，需 demuxlet/HTODemux 严控
- **Protein vs mRNA 时差**：CD69 等快速 inducible marker 蛋白可能比 mRNA 滞后/超前——RNA-protein discordance 是真生物学不是 noise
- **小群 cell type 在 ADT 上 < 100 个 antigen counts**：信号太低，被算法当 noise 吃掉

## ★ QC sanity check (known answer)
- Anchor (Stuart 2019 BMNC GSE128639)：
  - **CD4 蛋白** ADT 在 CD4 T cluster 高表达；mRNA `CD4` 同向（concordance > 0.7）
  - **CD8 蛋白** 同上
  - CD19+ B cell 在 ADT 上明确分离（25 antibody panel 是足够的）
  - Isotype control 减除后 ADT density bimodality 清晰
  - WNN UMAP 上 HSPC 子群（trajectory）连续，而非离散 cluster
- Pass criterion：RNA-ADT concordance > 0.7 AND isotype subtracted
- Fail criterion：concordance < 0.5 → CLR 没做 (rule 09) 或 isotype 没减；ADT 在所有 cell 阳性 → bead 残留

## Lessons → seeds for rules
1. **ADT normalize 用 CLR 不用 log**，且要 isotype subtract
2. **WNN/totalVI/MOFA+ 多模态专用方法**，不允许直接 cbind 不同 modality
3. **Doublet 检测必须双模态**——RNA-only doublet detection miss CITE-seq 特有 doublet 类型
4. **注释 = RNA marker × ADT marker 双源**，不一致 cluster 标 review
5. **Isotype control 在 panel 中是必备 QC 通道**，设计实验时不能省
