---
case_id: omics-028-krusche-2019-giab-variant-benchmark-failure
schema_version: 1
modality: variant_calling
study: "Krusche et al 2019, Best practices for benchmarking germline small-variant calls in human genomes"
public_accession: "GIAB HG001-HG007 truth sets; gnomAD; 1000 Genomes"
doi: 10.1038/s41587-019-0054-x
organism: Homo sapiens
tissue: "germline DNA (NA12878 / Ashkenazi trio / Chinese trio)"
study_design: meta_analysis_failure
assay_subtype: variant_calling_benchmark
cell_type_focus: [bulk_dna_germline]
tools: [GATK 4.x, DeepVariant, Strelka2, FreeBayes, hap.py / vcfeval, RTG Tools, GA4GH benchmark]
method_choice: [variant_caller_benchmark, truth_set_stratification, regional_difficulty_stratification, indel_complexity]
status: validated
validated: true
source: praxis_seed
case_class: failure_landscape
provenance:
  source_type: literature_failure_review
  doi: 10.1038/s41587-019-0054-x
  extracted_at: 2026-05-01
tags: [failure_case, variant_calling, GIAB, benchmark, regional_difficulty, anti_pattern, NEG]
---

# Krusche 2019 GIAB benchmark：variant calling 评估的系统性失败模式

## Background
GA4GH Benchmarking Team 与 Genome in a Bottle (GIAB) 联合发布的 variant calling benchmark "best practice" 论文。**关键发现**：variant caller 的"99% precision"是个误导数字 — **只有在 high-confidence region 内**才如此；real-world genome 的 ~10-15% 区域是"difficult"（segmental duplication / low-mappability / 长重复 / 大 INDEL），多数 caller 在此区域 precision drop 到 50-70%。这是 case 019 (GATK Best Practices success) 的 counter-balance：best practice 也有适用边界。

## What this paper actually did
1. 用 GIAB truth set (HG001-HG007) 系统化 variant calling benchmark
2. **Region stratification** 关键：把 genome 切成
   - Easy / high-confidence: ~85% genome
   - Tandem repeat regions
   - Homopolymer ≥ 5bp
   - Segmental duplications (segdup)
   - Low-mappability (multi-mapping)
   - Centromeric / acrocentric / telomeric
   - Long INDEL (≥ 50bp; structural variant 边界)
3. **Variant type stratification**: SNP / small INDEL / large INDEL / MNP / complex
4. **Caller comparison**: GATK / DeepVariant / Strelka2 / FreeBayes
5. **关键发现**：
   - **High-conf region**: SNP F1 99-99.5%; INDEL F1 95-97% (caller-dependent)
   - **Tandem repeat**: SNP F1 80-90%; INDEL F1 50-70% (drop 显著)
   - **Segdup**: SNP F1 70-85%; INDEL F1 40-60%
   - **Long INDEL**: F1 < 50% across all callers
   - **Homopolymer ≥ 5bp**: INDEL F1 < 70% (sequencing chemistry-specific)
   - **DeepVariant > GATK** in difficult regions (~3-5% F1 advantage)
   - **GATK + DeepVariant agreement** is the gold standard for ambiguous calls
   - **Truth set version matters**: GIAB v3.3 vs v4.2 truth changed in difficult regions

## ★ 排除/不做的事 (反面教材)
- **报告 single global F1**: 99% F1 in genome ≠ 99% F1 in your specific gene of interest
- **不做 region stratification 报告**: 临床决策需要 region-specific recall/precision
- **跳过 hap.py / vcfeval 标准化对比**: vcftools diff / bedtools 对 phased haplotype 处理错
- **拿 v3.3 truth set 对比 modern caller**: caller 改进可能在 difficult region，旧 truth set 不能捕捉
- **Pharmacogenomics gene 用普通 caller**: CYP2D6 / HLA / KIR 等基因在 segdup 内，需要 specialized caller (Stargazer / HLA-LA)
- **Long INDEL (≥ 50bp) 用 small-variant caller**: 走 SV caller (Manta / GRIDSS) 才行
- **Homopolymer 不做 chemistry-specific filter**: ONT 的 homopolymer error 与 Illumina 不同
- **Trio 数据不做 mendelian inheritance check**: 后验 truth set 中 ~1% violations 是新 mutation 或 caller error
- **跨 GIAB sample 性能直接外推**: NA12878 (CEU)、HG002 (Ashkenazi)、HG005 (Chinese) 的 difficult region 不同

## ★ 失败模式 (论文记录的)
- **HLA / KIR gene region**: GATK call 准确率 ~60%，因 segdup + 高多态性；clinical pharmacogenomics 必须用 specialized caller
- **Tandem repeat insertion**: STR/VNTR 长度变化 caller 几乎都失败；专门的 STR caller (HipSTR / GangSTR) 是必需
- **Centromere / telomere**: read 不能 unambiguously align，几乎无 variant call
- **Mitochondrial heteroplasmy**: 不能用 diploid caller (HC 假设 diploid)；专门的 mtDNA caller (mitoSAlt / MToolBox)
- **Chimeric reads**: BWA-MEM split read flags 处理错 → 假 INDEL
- **Tumor purity bias** (somatic context): purity < 30% → Mutect2 sensitivity < 30%（与 case 019 hard 阈值对应）
- **Truth set bleeding**: GIAB truth set 在更新版本中扩展，旧 benchmark 数据不能直接对比新 caller paper

## ★ 方法选择决策链
```
Variant calling benchmark / 临床报告?
├─ Always stratify by region:
│   ├─ High-conf (auto report)
│   ├─ Tandem repeat (separate report; caveat user)
│   ├─ Segdup (consider specialized caller)
│   ├─ Centromere/telomere (do NOT report; not callable)
│   └─ Homopolymer (chemistry-specific filter)
├─ Pharmacogenomics genes?
│   ├─ HLA → HLA-LA / OptiType
│   ├─ CYP2D6 → Stargazer
│   ├─ KIR → KIR*IMP / specialized
│   └─ Standard caller for "easy" pharmacogenomics gene
├─ Variant types
│   ├─ SNP → GATK / DeepVariant / Strelka
│   ├─ Small INDEL ≤ 20bp → same; expect lower F1
│   ├─ Long INDEL ≥ 50bp → SV caller (Manta / GRIDSS)
│   └─ STR/VNTR → HipSTR / ExpansionHunter
└─ Always cross-validate:
    ├─ ≥ 2 caller agreement
    ├─ hap.py against current GIAB truth (lock version!)
    └─ For trio data, mendelian violation check
```

## ★ QC sanity check (known answer)
- Anchor (Krusche 2019 GIAB benchmark)：
  - **HG001 NA12878 high-conf SNP F1**: ≥ 99% (GATK / DeepVariant)
  - **High-conf INDEL F1**: ≥ 95%
  - **Tandem repeat INDEL F1**: 50-70% (drop is real, not pipeline bug)
  - **Segdup region F1**: 60-80%
  - **Trio mendelian violation rate**: < 1% (else caller error suspected)
  - **GATK + DeepVariant overlap precision**: ≥ 99.5% (gold standard)
  - **Truth set version locked**: GIAB v4.2.1 as of 2024
- Pass criterion: high-conf metrics in expected range + region stratification reported
- Fail criterion: single global F1 reported without stratification → unfit for clinical decision

## Lessons → seeds for rules
1. **Variant calling 必须 region stratify 报告**（rule 16 强化）— 全局 F1 误导
2. **Pharmacogenomics gene 用 specialized caller**: HLA / CYP2D6 / KIR 普通 caller 准确率 ~60%
3. **Long INDEL ≥ 50bp 走 SV caller**：small-variant caller 注定失败
4. **STR/VNTR 走 specialized caller** (HipSTR / ExpansionHunter)
5. **GIAB truth set version lock**: v3.3 vs v4.2 不可比；记 provenance
6. **GATK + DeepVariant 双 caller 交集** 是 ambiguous call 的金标准
7. **Trio mendelian violation < 1%** 是 caller QC 必查
