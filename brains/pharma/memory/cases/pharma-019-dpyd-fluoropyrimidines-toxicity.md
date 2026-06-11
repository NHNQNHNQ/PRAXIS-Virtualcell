---
case_id: pharma-019-dpyd-fluoropyrimidines-toxicity
task: pharmacogenomic_toxicity_prevention
input_compound: 5-fluorouracil + capecitabine (5-FU prodrug)
target_drug: capecitabine, 5-fluorouracil (5-FU), tegafur (all DPD-cleared fluoropyrimidines)
target_population: patient
drug_class: small_mol
target_indication: oncology_colorectal_breast_GI
route_of_admin: PO_capecitabine_or_IV_5FU
tools: [DPYD genotype panel, dihydropyrimidine dehydrogenase (DPD) phenotype assay, pre-emptive dose reduction, CPIC guideline]
key_paper_doi: 10.1002/cpt.911
status: validated
provenance:
  source_type: literature
  citation: "Amstutz U et al. 2018 Clin Pharmacol Ther 103:210-216 'Clinical Pharmacogenetics Implementation Consortium (CPIC) Guideline for Dihydropyrimidine Dehydrogenase Genotype and Fluoropyrimidine Dosing: 2017 Update'"
  extracted_at: 2026-05-01
  extraction_confidence: high
tags: [DPYD, 5-fluorouracil, capecitabine, tegafur, fluoropyrimidine, dihydropyrimidine_dehydrogenase, oncology, toxicity_prevention, severe_toxicity, EMA_2020_mandate]
---

# DPYD fluoropyrimidine: 4 个 SNP 预防 fatal toxicity

## Background
5-FU + capecitabine + tegafur 是 colorectal / breast / GI 肿瘤 first-line 化疗 backbone (anti-metabolite, thymidylate synthase inhibition). 80% catabolism via 肝脏 DPD enzyme → DPD deficiency → 5-FU accumulation → severe / fatal toxicity (mucositis, diarrhea, neutropenia, hand-foot syndrome).

**DPYD gene** 编码 DPD enzyme. Loss-of-function variants:
- **DPYD\*2A (rs3918290, c.1905+1G>A)** — splicing defect; LoF; ~1% Caucasian carriage
- **DPYD\*13 (rs55886062, c.1679T>G)** — LoF
- **rs67376798 (c.2846A>T)** — partial function
- **rs75017182 (HapB3, c.1129-5923C>G)** — partial function

**Phenotype categorization** (CPIC 2017 activity score AS):
- AS = 2.0 (normal): no dose reduction
- AS = 1.0-1.5 (intermediate): reduce dose 25-50%
- AS = 0-0.5 (poor): avoid fluoropyrimidine OR start at 50% with rapid escalation only after toxicity demonstrably absent

**Clinical impact**: untreated DPYD-null patients have **fatal toxicity rate ~40-60%** at standard dose. Pre-emptive genotyping reduces severe toxicity (grade ≥3) from 73% to 28% (DPYD\*2A carriers in Henricks 2018 Lancet Oncol cohort).

**EMA April 2020**: mandated pre-treatment DPYD testing (4-variant panel) for all fluoropyrimidine prescriptions in EU. NHS England mandate followed November 2020.

## What I actually did
1. **DPYD genotype panel** (4 SNPs minimum: \*2A, \*13, c.2846A>T, c.1129-5923 HapB3)
2. **Activity score calculation** per CPIC 2017:
   - \*1/\*1 (homozygous functional): AS = 2.0
   - \*1/\*2A or \*1/\*13: AS = 1.0 (intermediate)
   - \*1/c.2846A>T or \*1/HapB3: AS = 1.5 (intermediate)
   - \*2A/\*2A or compound heterozygous LoF: AS = 0 (null; AVOID fluoropyrimidine)
3. **Dose recommendation**:
   - AS 2.0: full dose (capecitabine 1250 mg/m² q12h × 14d / 21d cycle)
   - AS 1.5: 75% dose (940 mg/m² q12h)
   - AS 1.0: 50% dose (625 mg/m² q12h) with TDM if available
   - AS 0-0.5: avoid OR <25% dose with intensive monitoring
4. **TDM 5-FU**: where available, target Css 20-30 mg·h/L AUC for 5-FU IV infusion (TDM-guided dose-adjustment in real-world cohorts shows further benefit)
5. **Pre-emptive screen + dose adjustment** (Henricks 2018 protocol): all colorectal patients screened pre-treatment; \*2A carriers receive 50% dose; severe toxicity rate dropped from 73% (historical) to 28%.

## ★ 排除的 dose / population / 方法
- **Standard fluoropyrimidine dose for any DPYD LoF carrier**: 5-FU AUC ↑ 2-5× → fatal toxicity risk. Dose reduction MANDATORY.
- **DPYD\*2A homozygous + standard dose**: ~50% fatal toxicity rate. Switch to non-fluoropyrimidine regimen (oxaliplatin + leucovorin alone, or irinotecan-based).
- **3-allele panel only without HapB3**: misses 30-50% of intermediate-metabolizer phenotypes especially in non-European populations.
- **DPD phenotype assay (uracil breath test) alone without DPYD genotype**: phenotype only catches ~70% of LoF; combined genotype + phenotype panel best.
- **Genotype testing AFTER first cycle toxicity emergence**: too late — if toxicity is grade ≥4, often fatal. Pre-emptive testing required.
- **Non-cancer use of fluoropyrimidine prodrugs (5-FU topical)**: localized topical 5-FU has minimal systemic exposure; DPYD testing not routinely required.

## ★ 失败模式
- **Pre-2020 standard care didn't test DPYD**: ~10% of fluoropyrimidine fatalities attributable to undetected DPD deficiency.
- **EMA mandate compliance variability**: even after 2020 mandate, some EU countries/centers slow to implement; persistent missed cases.
- **HapB3 (c.1129-5923) is intronic** and was missed by older sequencing panels; only added in 2017 CPIC update.
- **Compound heterozygosity rare but devastating**: \*2A/\*13 compound heterozygous = AS 0 = essentially DPD-null; rare (< 0.01% frequency) but ~50% mortality at standard dose.
- **Acquired DPD inhibition**: brivudine (anti-herpes drug, EU only) covalently inactivates DPD → effective DPD-null state for 4 weeks → severe 5-FU toxicity. Drug-drug-DPYD-gene interaction (rule_10 generalization).
- **In-trial vs real-world performance gap**: dose-reduction in trials with intensive monitoring vs real-world without — community oncology may underdose AS = 1.0 patients to avoid toxicity at the cost of efficacy.

## ★ 方法选择决策链
- **Pre-emptive genotyping before first cycle**: standard of care since EMA 2020.
- **4-allele panel minimum** (\*2A, \*13, c.2846A>T, HapB3); 5-allele if budget allows (add c.1679T>G).
- **DPD phenotype assay (uracil breath, plasma U/UH2 ratio)** as adjunct in equivocal cases or for novel/rare variants not in panel.
- **AS-based discrete dose reduction** (CPIC) for clinical decisions; algorithm-based continuous dose adjustment for research.
- **Switch to non-fluoropyrimidine regimen** for AS ≤ 0.5 patients (alternative: oxaliplatin + leucovorin in colorectal; CMF in breast).
- **TDM 5-FU AUC** for IV continuous infusion regimens (not capecitabine PO; oral PK too variable for TDM).

## ★ Validation
- **Henricks 2018 Lancet Oncol 19:1459 (n=1103 prospective)**: DPYD\*2A pre-emptive 50% dose reduction reduced severe toxicity from 73% → 28% in carriers, with maintained efficacy.
- **Deenen 2016 J Clin Oncol 34:227 (n=2038 prospective)**: similar 4-variant pre-screen + dose adjustment showed grade ≥3 toxicity drop in DPYD-positive subgroup.
- **EMA 2020 mandate** + cost-effectiveness analyses (Henricks 2019): genotype-guided is dominant strategy (lower toxicity + lower hospitalization cost + non-inferior efficacy).
- **CPIC 2017 update** synthesizes 50+ studies; level A evidence.

## Lessons → seeds for rules
1. **Pre-emptive PG genotyping** for any drug with high genotype-driven toxicity risk (rule_09 generalization).
2. **Multi-allele panel**: include intronic and partial-function alleles, not just classic LoF.
3. **Ethnic calibration**: panel breadth may differ by ancestry; include HapB3 and c.2846A>T.
4. **Pre-emptive dose reduction > reactive dose reduction post-toxicity**: when toxicity is fatal, no second chance.
5. **Drug-gene-drug interactions**: brivudine + 5-FU = effective DPD-null (rule_10 extension).
6. **Switch class when phenotype is null** (rule_09 anchor): AS=0 → use non-fluoropyrimidine alternative.
