---
case_id: omics-013-young-2020-ambient-rna-neglect-failure
schema_version: 1
modality: scRNA_seq
study: "Young & Behjati 2020, SoupX removes ambient RNA contamination from droplet-based single-cell RNA sequencing data"
public_accession: "(method paper + 4 reanalyzed datasets including Lawlor 2017 islet)"
doi: 10.1093/gigascience/giaa151
organism: Homo sapiens
tissue: "multi-tissue (pancreas islet, kidney, lung, PBMC) — method validation"
study_design: method_failure_demonstration
assay_subtype: 10x_chromium_v2_v3
cell_type_focus: [pancreas_islet, kidney_epithelial, lung_alveolar, PBMC_immune]
tools: [SoupX 1.4, CellBender 0.2, DecontX 1.0, scAR]
method_choice: [soupx, cellbender, decontx, scar]
status: validated
validated: true
source: praxis_seed
case_class: failure_pattern
provenance:
  source_type: literature_failure_demonstration
  doi: 10.1093/gigascience/giaa151
  extracted_at: 2026-04-29
tags: [failure_case, ambient_rna, soup, droplet_based, anti_pattern]
---

# Young 2020 SoupX：droplet scRNA 中 ambient RNA 污染的常被忽视错误

## Background
Droplet-based scRNA（10x Chromium / DropSeq）每个 droplet 都从环境 RNA 池中"喝一口" —— 即所谓 "soup" 或 "ambient RNA"。Young & Behjati 系统量化了这一现象：典型 10x 实验**有 2-50% 的 reads 来自 ambient RNA 而非细胞内表达**，且这一污染**严重影响下游 cell type 注释、DE、和 pathway 分析**。社区在 2017-2020 间大量论文未做 ambient correction，回头看相当部分结论受影响。

## What this paper documented
1. **量化 soup 比例**：Lawlor 2017 islet 数据中 acinar cell 高表达基因（PRSS1, REG1A）出现在所有非 acinar cell 的细胞中，平均贡献 ~10% 的 counts
2. **典型组织模式**：
   - **Pancreas islet**：acinar 消化酶（CTRB1, CTRB2, PRSS1）泄漏到 beta/alpha cell；导致 beta cell DE 报告 acinar marker
   - **PBMC + 红细胞污染**：HBB / HBA 出现在 T/mono cell 中（如果分离不彻底）
   - **Lung**：surfactant gene SFTPC 出现在 immune cell
   - **Kidney**：tubule 高表达 gene 出现在 immune infiltrate
3. **修正方法**：
   - **SoupX**：用 empty droplet 估 soup → contaminate fraction → 矩阵减除
   - **CellBender**：deep learning，更彻底但需 GPU + 训练
   - **DecontX**：贝叶斯，在 cell type 间分配 contamination
   - **scAR**：focused on noise modeling
4. **Anti-rule confirmed**：solid tissue scRNA 不做 ambient correction → cell type 注释错 / DE 全是 noise / TCR/BCR 类基因虚假"普遍表达"

## ★ 排除/不做的事 (反面教材)
- **Solid tissue scRNA 跳过 ambient correction**：尤其 pancreas / lung / liver / kidney
- **TCR/BCR 基因当 cell-type marker 不查 ambient**：这些基因极易被 ambient 污染
- **直接用 raw matrix 进 HVG**：HVG 选择被 ambient 模式偏 → 下游 PCA / cluster 全错
- **cell-free RNA 高的样本（如肿瘤坏死区）**：ambient 比例可达 30-50%，必须 correct
- **以 empty droplet 数 < 1000 跑 SoupX**：empty 太少估计不稳，结果不可信

## ★ 失败模式 (论文记录的)
- **Lawlor 2017 islet 重新分析**：原文 beta cell 的 top DE 基因含 acinar genes (PRSS1, CTRB1) —— SoupX correction 后这些消失，真 beta cell program 浮现
- **PBMC scRNA + cancer 样本**：肿瘤 lysis 释放大量 cell-free RNA → ambient 高 → 把 cancer markers 报到 immune cell 上
- **Doublet detection 干扰**：高 ambient 让 scrublet 把单 cell 误判为 doublet（contamination 模式像 double profile）
- **Cross-sample 比较污染**：sample 1 有大量坏死 → ambient 高；sample 2 健康 → ambient 低；不 correct 的话差异主要是 ambient 而非 biology
- **Saunders 2018 brain**：SoupX 后 microglia 真 DE 浮现，原因 brain 区域 ambient = 神经元 mRNA

## ★ 方法选择决策链
```
组织类型？
├─ Solid tissue (pancreas / liver / lung / kidney / brain) → SoupX MANDATORY
├─ Tumor / 含坏死区 → SoupX OR CellBender (后者更彻底)
├─ PBMC / 健康血液 → ambient 通常 < 5%, SoupX 可选但推荐
└─ FACS-sorted Smart-seq2 → ambient 几乎 0, 不需要

方法选择：
├─ SoupX：默认 (轻量、CPU)
├─ CellBender：高 ambient (>20%) 或 publication-grade
├─ DecontX：当能预先标注 cell type 时
└─ scAR：noise modeling 重点场景
```

## ★ QC sanity check (known answer)
- Anchor: TCR/BCR genes (TRBC1, IGHM 等) **不该** 在非 T/B cell 中显著表达
  - 检查：non-T-cell cluster 的 mean TRBC1 / max TRBC1 比 → > 0.3 = ambient 污染严重
- Pass criterion: SoupX correction 后该比 < 0.05
- Fail criterion: > 0.2 → 重做 ambient correction 或质疑分离质量

## Lessons → seeds for rules
1. **Solid tissue scRNA 默认跑 SoupX**（新 anti-rule for rule 11）
2. **Lineage marker 串扰 = ambient 信号**：T cell receptor 在非 T cell、surfactant 在 immune、酶原在 beta 都是 red flag
3. **跨 sample 比较前必须做 ambient correction**：否则差异主要来自坏死 / lysis 程度
4. **CellBender > SoupX > DecontX > scAR 决策树** 应嵌入 scrna_qc_pipeline skill
5. **Empty droplet 计数是 ambient correction 的关键资源**：CellRanger 默认丢弃 < 100 UMI 的 barcode，但其实它们对 SoupX 至关重要 —— rerun with `--include-introns --raw-feature-bc-matrix` 保留
