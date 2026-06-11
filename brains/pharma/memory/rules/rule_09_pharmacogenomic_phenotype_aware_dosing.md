---
rule_id: rule_09_pharmacogenomic_phenotype_aware_dosing
rule_type: case_distilled
applies_to: [tdm, poppk, pkpd, ddi]
evidence_cases:
  - pharma-010-tdm-narrow-therapeutic
  - pharma-011-pediatric-tacrolimus-poppk
  - pharma-012-cyp2d6-codeine
  - pharma-013-cyp2c19-clopidogrel
confidence: high
authoring_date: 2026-04-30
source_synthesis_section: cross-case PG axis (CYP3A5 + CYP2D6 + CYP2C19)
---

# 药物基因组学表型驱动剂量个体化 (跨 CYP3A5 / CYP2D6 / CYP2C19)

Generalization of rule_03 (CYP3A5 tacrolimus) → 任何由 polymorphic CYP 代谢的药物。

## When to apply

Drug metabolized primarily by CYP3A5, CYP2D6, CYP2C19, CYP2C9, TPMT, DPYD,
UGT1A1, or other clinically actionable polymorphic enzyme + CPIC level A/B
guideline exists.

## Mandatory operations

1. **Assign phenotype** from genotype using CPIC activity score:
   - PM (poor) — AS = 0
   - IM (intermediate) — AS 0.25-1.0
   - EM ("normal") — AS 1.25-2.25
   - UM (ultra-rapid) — AS ≥ 2.25
2. **Apply phenotype-specific dosing**: not just dose adjustment but potentially
   **drug switch** when bioactivation pathway is genotype-blocked (case-012
   codeine PM/UM → switch class; case-013 clopidogrel PM → switch to
   prasugrel/ticagrelor).
3. **Concomitant medication review** for **drug-gene-drug interactions**
   (rule_10): strong CYP inhibitors phenoconvert EM → PM-equivalent.
4. **Consider ethnicity-calibrated allele frequencies**: CYP3A5 \*1 frequency
   varies 5-50× across populations; one-size-fits-all dosing fails subgroups.

## Reviewer hard-flag triggers

- TDM call without genotype for tacrolimus → `missing_genotype_for_tacro` (HR-related)
- Codeine call without CYP2D6 phenotype → `missing_phenotype_for_codeine`
- Codeine in pediatric < 12 → `contraindicated_pediatric_under_12` (FDA 2017)
- Codeine UM phenotype → `contraindicated_ultrarapid_metabolizer` (FDA 2017)
- Clopidogrel PM phenotype reaching < 50% platelet inhibition → recommend switch

## Confidence

Each underlying CPIC guideline (CYP3A5 Birdwell 2015, CYP2D6 Crews 2014, CYP2C19
Scott 2013) has level A evidence with multiple confirmatory clinical studies.
