---
case_id: microbiome-005-ancombc-da
task: differential_abundance_analysis
input_data: ASV table + sample metadata (case vs control)
tools: [ANCOM-BC2, MaAsLin2, LinDA, ALDEx2, songbird, ZicoSeq]
key_paper_doi: 10.1038/s41467-020-17041-7
status: validated
microbiome_task: da_analysis
sequencing_type: 16S
sample_type: human_gut
reference_db: null
dataset_accession: null
biomass_estimate: high
---

# Differential abundance：microbiome 数据特殊统计学

## Background
Microbiome 数据 = compositional + zero-inflated + sparse + over-dispersed。Standard t-test / DESeq2 假设破坏 → false positive。**专用方法**：ANCOM-BC2 / MaAsLin2 / LinDA 处理 compositionality + sparsity + complex covariates。

## What I actually did
1. **Input**：ASV count table + metadata (case/control + age/sex/diet)
2. **Pre-process**：
   - 过滤 prevalence < 10% sample 或 < 5 reads
   - Don't rarefy (信息丢)；instead model handles count
3. **ANCOM-BC2**：
   - Bias correction: per-sample sampling fraction estimate
   - Linear model with covariates
   - Multiple testing correction (Holm)
   - Sensitivity analysis: pseudo-count, taxon prevalence
4. **MaAsLin2 平行**：generalized linear mixed model with random effects
5. **LinDA**：fast, well-controlled FDR
6. **Effect size + p-value 双报**：log fold change + adj p
7. **Cross-method consistency**：significant in ≥ 2 methods = high confidence
8. **Pathway-level DA**：similar tools on functional pathway

## ★ 排除/不做的事
- **t-test / Wilcoxon on raw count**：compositionality violation, false positive 高
- **DESeq2 directly**：partly works but assumptions violated
- **Rarefaction before DA**：信息损失，统计 power 低
- **Single method**：cross-method consistency 重要
- **No covariate adjustment**：age/sex/diet/batch confound
- **Effect size ignored**：statistically significant but tiny effect

## ★ 失败模式
- **High inter-individual variability**：microbiome cross-person 比 cross-condition variability 大 → power 弱
- **Confounding with diet / antibiotic / lifestyle**：observational study 难解读
- **Compositional bias**：one taxon increase → other decrease apparent (not real)
- **Zero inflation**：high zero rate in sparse data
- **Multiple testing penalty**：1000s of taxa → strict correction
- **Batch effect**：DNA extraction batch / sequencing run 主要 effect

## Lessons → seeds for rules
1. **Compositional-aware methods (ANCOM-BC2, LinDA)** > t-test / DESeq2
2. **Multi-method cross-validation**
3. **Covariate adjustment**: age, sex, BMI, antibiotic 必须
4. **Effect size + p-value** dual report
5. **Don't rarefy**：use count-aware models
6. **Batch effect** check + adjust
7. **Pathway-level DA** parallel to taxon
