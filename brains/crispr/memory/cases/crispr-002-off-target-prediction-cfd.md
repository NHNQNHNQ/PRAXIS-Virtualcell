---
case_id: crispr-002-off-target-prediction-cfd
schema_version: 1
edit_type: off_target_landscape
target_gene: any
target_organism: hg38
cell_context: any
editing_system: SpCas9
delivery_method: any
tools:
- CFD score
- MIT score
- CasOFFinder
- CHANGE-seq
- GUIDE-seq
- CIRCLE-seq
- CRISTA
key_paper_doi: 10.1038/nbt.3437
status: validated
provenance:
  source_type: literature
  doi: 10.1038/nbt.3437
  citation: Doench JG et al. (2016) Nat Biotechnol 34:184-191 — CFD off-target score
  extracted_at: '2026-04-29'
  source: praxis_seed
tags:
- off_target_landscape
- CFD
- CHANGE-seq
- GUIDE-seq
- clinical_grade
editing_system_list:
- SpCas9
- SpCas9-HF1
- eSpCas9
---

# Off-target 预测：in silico ranking 与实验验证的 gap

## Background
sgRNA off-target 预测是 CRISPR 临床应用的 gating 问题。in silico 工具（CFD/MIT score）便宜但 false positive 高；实验方法（GUIDE-seq/CHANGE-seq/CIRCLE-seq）准确但贵。**真实 off-target landscape 通常被 in silico over-call**——95% in silico hit 实验验证不切割。

## What I actually did
1. **In silico baseline**：CRISPOR 输出 mismatch ≤ 4 的 NGG/NAG 全基因组 hit table
2. **CFD score 计算**：每 mismatch 位置有不同 weight（PAM-proximal seed > distal）；累积 CFD：1 - prod(1 - per_mismatch_CFD)
3. **CasOFFinder 全基因组扫描**：bulge tolerance 1 + mismatch 4，比 CRISPOR 更穷尽
4. **Genomic context filter**：
   - In CDS / UTR / regulatory region → 高 risk
   - In intron / intergenic → low risk
   - In essential gene → 阻塞
5. **实验验证（关键 case）**：临床 sgRNA 必须 wet lab 验证：
   - **GUIDE-seq**：dsODN integration 报 actual cut site
   - **CHANGE-seq**：循环 in vitro，sensitivity 最高
   - **CIRCLE-seq**：环化基因组 in vitro
6. **Comparison**：典型治疗用 sgRNA in silico CFD top 100 → CHANGE-seq 验证 cut 的可能 5-15
7. **Risk stratification**：top 3 in silico hit 必 amplicon-seq；top 4-20 视情况

## ★ 排除/不做的事
- **只信 CFD score 临床用**：assay-validated 必须，否则 IND 申请 FDA 不接受
- **不区分 NGG vs NAG PAM**：NAG cleavage 效率 ~10% NGG 但仍可见
- **Bulge-tolerant 不查**：DNA bulge / RNA bulge mismatch 不被 vanilla CFD 抓
- **不看 chromatin accessibility**：closed chromatin 的 off-target 实际不切；ATAC-seq integration 提升 specificity
- **种族/个体 SNP 影响**：reference genome 的 off-target 可能不在 patient 实际基因组——personalized off-target 评估
- **Cell type 一致性**：HEK293 in silico off-target panel ≠ T cell ≠ HSC

## ★ 失败模式
- **Indel via off-target translocation**：双 cut（target + off-target）可形成大 deletion / translocation
- **Chromosome rearrangement**：长距离 off-target 同时 cut 引发 chromothripsis（罕见但严重）
- **VHL-like off-target**：临床 sgRNA 可能 cut tumor suppressor → oncogenic 风险
- **Mosaic editing**：bulk 看起来 specificity 好，single cell 显示有 outlier cells 高 off-target
- **PAM-distal mismatch underweighted**：CFD weight 在 distal 区低估了 cleavage
- **ssODN 整合 bias**：HDR donor 整合到 off-target 错位

## Lessons → seeds for rules
1. **临床 sgRNA 必须 wet lab off-target 验证**（GUIDE-seq + CHANGE-seq 双方）
2. **Risk stratification**：genomic context（CDS/essential）× CFD × cell type
3. **Top 20 in silico hit amplicon-seq verify**——不验证 deep seq 不能宣称 specificity
4. **Translocation 评估**：双 cut event 显式查
5. **Personalized off-target**：临床用 patient WGS 重 align off-target 表
6. **Chromatin context**：ATAC-seq + RNA-seq integration 升 specificity prediction
