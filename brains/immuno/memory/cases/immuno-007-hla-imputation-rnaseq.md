---
case_id: immuno-007-hla-imputation-rnaseq
schema_version: 1
task: hla_typing_from_rnaseq
immuno_task: hla_typing_from_rnaseq
antigen_class: n/a
hla_class: population_coverage
hla_alleles: []
peptide_length_bin: n/a
disease_indication: n/a
target_data: TCGA tumor RNA-seq sample
target_protein_uniprot: []
tools: [OptiType, arcasHLA, HLA-LA, seq2HLA, xHLA, Polysolver]
key_paper_doi: 10.1186/s13073-018-0560-3
status: validated
source: praxis_seed
---

# HLA imputation from RNA-seq：4-digit class I/II typing

## Background
临床/研究常 RNA-seq 已有但 HLA typing 未做。RNA-seq derived HLA typing accuracy 已达 4-digit ≥ 95% for class I (主流 alleles)，DR/DQ 稍弱（90% 左右）。是 neoantigen pipeline 必需 input。

## What I actually did
1. **Input**：bulk RNA-seq fastq (paired) ≥ 30M reads
2. **OptiType (class I)**：fastq → HLA-A/B/C 4-digit calls + confidence
3. **arcasHLA (class I + II)**：另一 caller, multi-class 一站式
4. **HLA-LA (graph alignment)**：第三方法, 准确度高但慢
5. **Consensus**：3 callers ≥ 2 agree = 信；分歧时人工 review
6. **Confidence indicators**：
   - Coverage at HLA region ≥ 50x preferred
   - Multiple supporting reads per allele call
   - Heterozygous (homozygous 也可能但少)
7. **For class II**：DR/DP/DQ alleles，DRB1 最准；DRB3/4/5 (paralogous beta chain) 难
8. **Validation**：与 Sanger / SBT typing 比对（subset 验证 pipeline）
9. **Output**：HLA-A*02:01,*03:01 + HLA-B*07:02,*15:01 + HLA-C*07:02,*06:02 + HLA-DRB1*15:01,*04:01 等完整 4-digit haplotype

## ★ 排除/不做的事
- **Single caller**：3 caller consensus 是 reliable 标准
- **2-digit only (e.g., HLA-A02)**：4-digit 是 neoantigen pipeline minimum
- **Coverage 不查**：< 30x at HLA RNA-seq 给低 confidence
- **DR/DP/DQ 直接 trust**：class II 准度低，DR 关注，DP/DQ 谨慎
- **Tumor RNA-seq 用 caller assume normal**：tumor HLA LOH（loss of heterozygosity）影响 RNA-seq HLA call → match normal RNA-seq 才准
- **不报 confidence**：用户决策需知 reliability

## ★ 失败模式
- **HLA LOH in tumor**：tumor sample 丢一 allele → only one called，但 patient 实际 het
- **Rare allele not in reference DB**：caller 默认 IMGT/HLA 数据库，未列入的 allele 错配
- **Pseudogene confusion**：HLA-H, HLA-J 等 pseudogene 偶被误 call
- **Cross-mapping**：HLA 基因序列高度同源，read 跨 align
- **Low expression RNA**：HLA-DRB3 等表达低 → coverage 弱
- **Population bias**：欧美人群 reference rich，非洲人群少见 allele 准度低

## Lessons → seeds for rules
1. **3 caller consensus**：OptiType + arcasHLA + HLA-LA
2. **4-digit minimum**
3. **Coverage ≥ 30x** at HLA region 必查
4. **Tumor 用 matched normal**避 LOH
5. **Confidence label per allele**
6. **Class II（DR/DP/DQ）** 单独标 confidence
7. **Population coverage check** for rare allele
