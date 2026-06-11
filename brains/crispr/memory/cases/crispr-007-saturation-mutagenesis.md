---
case_id: crispr-007-saturation-mutagenesis
schema_version: 1
edit_type: saturation_genome_editing_sge
target_gene: BRCA1
target_organism: hg38
cell_context: HAP1
editing_system: SpCas9
delivery_method: plasmid_transfection
tools:
- SGE pipeline (Findlay 2018)
- MaveDB
- Enrich2
- MAGeCK for screen
key_paper_doi: 10.1038/s41586-018-0461-z
status: validated
provenance:
  source_type: literature
  doi: 10.1038/s41586-018-0461-z
  citation: Findlay GM et al. (2018) Nature 562:217-222 — BRCA1 SGE
  extracted_at: '2026-04-29'
  source: praxis_seed
tags:
- saturation_genome_editing_sge
- HAP1
- SpCas9
- BRCA1
- MaveDB
- VUS
---

# BRCA1 saturation genome editing：每个氨基酸所有变体功能扫描

## Background
Findlay 2018 (Nature) 用 SGE 把 BRCA1 13 exon 中每个 SNV 变体生成 + 测功能影响（drop out 还是 enrich）。**输出：variant function score 表**——直接 inform clinical variant interpretation（VUS → benign/pathogenic）。比 pure in silico predictor 准 ~10× 在 critical exon 上。

## What I actually did
1. **Target region 选择**：critical exon（如 RING domain exon 2-10、BRCT exon 16-23）；HAP1 是 haploid 简化分析
2. **Library 设计**：每 codon 19 substitution + 1 stop = 20 variant × ~50 codon × exon = ~1000 variant 库
3. **HDR donor design**：
   - Each variant 一条 ssODN（70-100 nt） with mutation + silent recoding 防 re-cutting
   - sgRNA cut site < 30 nt from target codon
4. **Library generation**：oligonucleotide pool synthesis（Twist / IDT）→ amplification → SLAM-seq prep
5. **Cas9 + library 共转 HAP1** → 14 day cellular fitness selection → amplicon-seq variant frequency
6. **Score = log2(end / start)**：每 variant fitness effect
7. **Validation**：
   - Stop codon 应全 deplete（loss of function bench）
   - Synonymous 应 neutral
   - Known pathogenic variant 应 deplete
   - Known benign 应 neutral
8. **MaveDB 上传**：保留 variant × score 数据 community use

## ★ 排除/不做的事
- **Diploid cell line 跑 SGE**：复杂分析（hetero/homo），HAP1 / haploid 必须
- **HDR efficiency 不 boost**：默认 HDR < 5%；需用 HDR enhancer（NHEJ inhibitor / RAD51 stim）
- **Library 不含 silent control**：silent mutation 是 neutral baseline，不放无 calibration
- **Single replicate**：variant noise 巨大，需 ≥ 3 replicate
- **Selection 时间不足**：14 day 多 cell cycle 才能放大 fitness 差
- **不上传 MaveDB**：community variant 解读资源浪费，临床用 acceptance 受限

## ★ 失败模式
- **HDR efficiency cell type 依赖**：HAP1 ~5%；T cell ~1-2%；HSC < 1%
- **Allele dropout in haploid**：复制时 random allele loss，noise
- **Edit drift**：随时间累积 indel 而非 desired SNV，需 amplicon-seq 区分 pure SNV vs indel byproduct
- **Synonymous re-coding 导致 protein effect**：silent mutation 偶尔影响 splicing / mRNA stability
- **Selection pressure inadequate**：fitness selection 弱，effect size 缩
- **Off-target 引入 confounding**：cas9 cut + HDR 在 off-target locus，noise

## Lessons → seeds for rules
1. **Haploid cell line（HAP1）** for SGE 简化分析
2. **每 codon all 20 variant** library design + silent control
3. **Replicate ≥ 3** + selection ≥ 14 day
4. **Stop codon / synonymous QC anchor**：必含
5. **MaveDB 上传** for clinical variant interpretation
6. **HDR enhancer** boost edit efficiency
7. **Pure SNV vs indel byproduct** 区分（amplicon-seq + variant calling）
