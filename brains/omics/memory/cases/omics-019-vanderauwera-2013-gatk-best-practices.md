---
case_id: omics-019-vanderauwera-2013-gatk-best-practices
schema_version: 1
modality: variant_calling
study: "Van der Auwera et al 2013, From FastQ data to high-confidence variant calls: the GATK best practices pipeline"
public_accession: "1000 Genomes Project + GATK Resource Bundle"
doi: 10.1002/0471250953.bi1110s43
organism: Homo sapiens
tissue: "germline DNA (PBMC / saliva); somatic tumor DNA (tumor + matched normal)"
study_design: cohort_reference
assay_subtype: short_read_dna_seq_germline_and_somatic
cell_type_focus: [bulk_dna]
tools: [GATK 4.4, BWA-MEM 0.7.17, Picard 3.0, samtools 1.17, vcftools 0.1.16, bcftools 1.17, DeepVariant 1.5, Strelka2 2.9]
method_choice: [bwa_mem_alignment, base_quality_score_recalibration, haplotype_caller_gvcf, joint_genotyping, vqsr_or_hard_filter, mutect2_for_somatic]
status: validated
validated: true
source: praxis_seed
case_class: success
provenance:
  source_type: literature
  doi: 10.1002/0471250953.bi1110s43
  extracted_at: 2026-04-29
tags: [variant_calling, gatk, best_practices, germline, somatic, dna_seq]
---

# Van der Auwera 2013：GATK Best Practices（变异检测的工业标准）

## Background
Broad Institute 发布的 GATK Best Practices pipeline 是过去十年临床 + 群体基因组学的事实标准。覆盖 alignment → BQSR → variant calling → joint genotyping → variant filtering → annotation。**case-based learning 角度**：变异检测有大量"看似简单实则坑深"的决策（joint vs single-sample, hard filter vs VQSR, GATK vs DeepVariant）。这是 PRAXIS-Omics 第一个 DNA-seq variant calling case。

## What I actually did
1. **Alignment**：BWA-MEM `-M` flag (mark short split as secondary)；输出 sorted BAM；read group (RG) tag 必须正确（sample / library / lane）
2. **Mark duplicates**：Picard `MarkDuplicates`（不是 samtools markdup —— Picard 处理 RG 更稳）
3. **BQSR (Base Quality Score Recalibration)**：GATK `BaseRecalibrator` + `ApplyBQSR`，需要 known variants VCF (dbSNP)；纠正 sequencer-specific systematic error
4. **Variant calling per sample**：GATK4 `HaplotypeCaller` 在 GVCF 模式 → 输出 per-sample GVCF
5. **Joint genotyping**：`CombineGVCFs` + `GenotypeGVCFs` 跨 cohort；这一步是 best practice 关键 — 比 single-sample calling power 高
6. **Filtering**：
   - **VQSR (Variant Quality Score Recalibration)**：cohort 大（≥ 30 exomes / ≥ 10 WGS）时优先；GMM 学习真假变异分布
   - **Hard filtering**：cohort 小或 single-sample 时；预设阈值（QD < 2, FS > 60 SNP / 200 INDEL, MQ < 40, etc.）
7. **Annotation**：VEP / SnpEff / ANNOVAR；ClinVar / gnomAD allele frequency；CADD score
8. **Somatic variants (matched tumor-normal)**：Mutect2（替代 HaplotypeCaller），需要 PoN (Panel of Normals) + germline resource (gnomAD VCF)
9. **Validation**：
   - Ti/Tv ratio：WGS ~2.0-2.1, WES ~3.0-3.3（偏离 → 低质量 cohort）
   - Het/Hom ratio：~1.6 (population avg)
   - Sample concordance with known truth (GIAB samples HG001-HG007)

## ★ 排除/不做的事
- **跳过 BQSR 直接 call variant**：少数 sequencer batch 系统误差进 calling，VAF 估计偏
- **Single-sample calling 然后 cohort 合并 VCF**：power 大幅下降；joint genotyping 才能 share information across samples
- **Hard filter 在大 cohort 上代替 VQSR**：VQSR 学到的边界更软，不丢真变异
- **Germline pipeline 跑 somatic data**：HaplotypeCaller 假设 diploid + Hardy-Weinberg；肿瘤 subclone / aneuploidy 不符
- **Mutect2 不用 PoN**：技术 artifact （sequencer-specific error）会被 call 成 variant
- **Joint genotyping 跨技术 batch 不校正**：WGS + WES + targeted panel 直接 join → 大量 false call 在覆盖度边界
- **Variant filter 只看 PASS**：rare disease 中 PASS 但 borderline (QD 接近 threshold) 仍可能假；要看 GenotypeQuality (GQ)
- **不用 GIAB 或类似 truth set 验证 pipeline**：sensitivity / precision 不可量化

## ★ 失败模式
- **Read group 混乱**：lane 信息错填 → BQSR + duplicate marking 错；最常见的 pipeline failure
- **Reference build 不一致**：hg19 vs hg38 vs GRCh38 (with vs without alt contigs) → coordinate 错位
- **dbSNP version mismatch**：BQSR 用 dbSNP v138 训练但 calling 用 v151 → 校准偏
- **HC 在 INDEL 边界 over-call**：repetitive region INDEL 多假阳；VQSR INDEL track 通常不如 SNP track 干净
- **Mutect2 contamination**：tumor purity < 30% → somatic call 极少；需要 ContEst / VerifyBamID 估 contamination
- **GVCF merge memory blow**：cohort > 10k exomes，CombineGVCFs RAM 不够；需 GenomicsDBImport
- **CRAM 与 BAM 不一致**：CRAM 依赖 reference，reference 错→ 解码错
- **Y-chr / mitochondrial special handling**：gender + mt-DNA heteroplasmy 需要单独 calling

## ★ 方法选择决策链
```
Variant calling 任务?
├─ Germline single sample → GATK HaplotypeCaller (GVCF mode)
├─ Germline cohort (≥ 10 samples) → GATK HC GVCF + joint genotyping → VQSR
├─ Germline small cohort (< 10) → joint genotyping + hard filter
├─ Somatic tumor-normal → Mutect2 + PoN + germline resource + filtering (FilterMutectCalls)
├─ Somatic tumor-only → Mutect2 with --tumor-only + 严格 PoN (高假阳风险)
└─ Trio (parent-child) → joint genotyping + de novo variant detection (PossibleDeNovo)

Aligner choice?
├─ Short read (Illumina) → BWA-MEM (fastest + accurate)
├─ Linked read (10x) → Lariat / EMA
└─ Long read (PacBio HiFi / ONT) → minimap2 + DeepVariant (PacBio mode)

Caller alternatives (validated)？
├─ DeepVariant → 通常 SNP precision 比 GATK HC 略高；INDEL 类似
├─ Strelka2 → germline + somatic 都好；快
└─ FreeBayes → 老但稳；INDEL 不如 GATK
```

## ★ QC sanity check (known answer)
- Anchor (Genome in a Bottle HG001 NA12878 NIST gold standard)：
  - **SNP precision**：≥ 99% (PASS variants vs GIAB high-confidence)
  - **SNP recall**：≥ 99% (GIAB high-confidence within callable regions)
  - **INDEL precision**：≥ 95%
  - **INDEL recall**：≥ 90%
  - **Ti/Tv ratio (WES)**：3.0-3.3
  - **Het/Hom ratio**：~1.6 across genome
  - **Mean coverage WES** ≥ 80×；WGS ≥ 30×
- Pass criterion：SNP F1 ≥ 99%，INDEL F1 ≥ 92%，Ti/Tv 在范围
- Fail criterion：F1 < 95% → pipeline 配置问题（reference / dbSNP / BQSR）；Ti/Tv < 2.5 → 低质量 cohort

## Lessons → seeds for rules
1. **Joint genotyping 不可省**：单样本 calling 然后合并 VCF 是 anti-pattern
2. **BQSR 是必经步骤**（除非已知数据无 systematic error，比如 PacBio HiFi）
3. **VQSR vs hard filter 的 cutoff = 30 exomes / 10 WGS**
4. **Mutect2 不带 PoN 不可用**于 somatic calling
5. **Reference build + dbSNP version 必须 lock 在 provenance**
6. **GIAB / NA12878 truth set 验证 pipeline**（每次 pipeline 改动后跑一次）
7. **Read group tag 是 GATK pipeline 隐形地雷**：自动化 RG 添加是好实践
