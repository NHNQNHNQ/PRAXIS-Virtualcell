---
rule_id: 16-variant-calling-priors
rule_type: case_distilled
applies_to:
  modality: [variant_calling]
  study_design: [cohort, cohort_reference, case_control, trio]
  tissue_class: ALL
  task: [variant_calling, joint_genotyping, filtering]
evidence_cases:
  - case_id: omics-019-vanderauwera-2013-gatk-best-practices
    page_hint: "Best Practices pipeline + VQSR vs hard filter cutoff"
confidence: high
status: active
created: 2026-04-29
---

# Variant calling priors (GATK Best Practices grade)

## Statement
1. **Joint genotyping is required for cohorts** — single-sample calling then
   VCF merge is anti-pattern (loses cross-sample power).
2. **BQSR mandatory** unless data is known systematic-error-free (PacBio HiFi).
3. **VQSR ≥ 30 exomes / ≥ 10 WGS**; smaller cohort → hard filter.
4. **Mutect2 + PoN + germline resource** for somatic calling — no PoN = no go.
5. **Reference + dbSNP version locked** in provenance (BQSR resource version
   matters).
6. **GIAB / NA12878 truth set** must benchmark pipeline (sensitivity +
   precision F1 reportable).
7. **Read group tags** are the silent killer — wrong RG → wrong BQSR + wrong
   dedup.

## Decision tree
```
Variant calling task?
├─ Germline single sample → GATK HaplotypeCaller GVCF
├─ Germline cohort ≥ 10 → joint genotyping + VQSR
├─ Germline small cohort < 10 → joint genotyping + hard filter
├─ Somatic tumor-normal → Mutect2 + PoN + germline resource + FilterMutectCalls
├─ Somatic tumor-only → Mutect2 --tumor-only + strict PoN + caveat: high FP risk
├─ Trio (parent-child) → joint + de novo (PossibleDeNovo)
└─ Long read (PacBio HiFi / ONT) → DeepVariant or ClairS

Aligner?
├─ Short read Illumina → BWA-MEM
├─ Linked read 10x → Lariat / EMA
└─ Long read → minimap2

Caller alternatives?
├─ DeepVariant → SNP precision typically ≥ GATK; INDEL similar
├─ Strelka2 → fast, validated for both germline + somatic
└─ FreeBayes → mature; INDEL slightly inferior
```

## Hard filter thresholds (Best Practices defaults)
**SNP**: QD < 2.0, FS > 60.0, SOR > 3.0, MQ < 40.0, MQRankSum < -12.5, ReadPosRankSum < -8.0
**INDEL**: QD < 2.0, FS > 200.0, SOR > 10.0, ReadPosRankSum < -20.0

## Cold-start fallback
- Reference build unknown → ask user; do not silently use latest.
- dbSNP version unknown → use GATK Resource Bundle's bundled version,
  document.
- Truth set unavailable → flag confidence: medium; results not externally
  benchmarked.

## Sanity anchors
- **HG001 NA12878 (GIAB)**: SNP F1 ≥ 99%, INDEL F1 ≥ 92% (within high-conf).
- **Ti/Tv (WES)**: 3.0–3.3.
- **Het/Hom**: ~1.6.
- **Mean coverage**: WES ≥ 80×, WGS ≥ 30×.

## Linked anti-rule sections (rule 11)
Variant-calling-specific: skip BQSR, single-sample then merge VCF,
hard filter on large cohort, Mutect2 without PoN, joint genotyping cross
WGS+WES without recalibration, hard-coded reference build.
