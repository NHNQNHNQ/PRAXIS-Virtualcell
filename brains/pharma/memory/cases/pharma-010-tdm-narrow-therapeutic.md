---
case_id: pharma-010-tdm-narrow-therapeutic
task: therapeutic_drug_monitoring
target_drug: tacrolimus (immunosuppressant, narrow therapeutic window)
target_population: organ transplant patient
tools: [Bayesian forecasting (Tucuxi/InsightRX), NONMEM/Pumas posterior, hospital LIS integration]
key_paper_doi: 10.1002/cpt.113
status: validated
_doi_provenance: Birdwell KA et al. 2015 Clin Pharmacol Ther 98:19–24 "Clinical Pharmacogenetics Implementation Consortium (CPIC) Guidelines for CYP3A5 Genotype and Tacrolimus Dosing" — the canonical CPIC guideline establishing CYP3A5 *1 carrier dose adjustment for tacrolimus that this case describes.
---

# TDM (Therapeutic Drug Monitoring)：tacrolimus 个体化剂量

## Background
Tacrolimus (FK506) 是 organ transplant 主流免疫抑制 — 太低 → rejection；太高 → nephrotoxicity, neurotoxicity, diabetes。Therapeutic window: trough 5-15 ng/mL (transplant type-specific)。**TDM = measure trough → adjust dose to maintain therapeutic range**。Bayesian forecasting tool 比 trough-only adjustment 更准。

## What I actually did
1. **Patient inputs**：age, weight, ethnicity, organ type, CYP3A5 genotype (\*1 vs \*3), concomitant drugs (CYP3A inhibitor/inducer)
2. **PopPK model** for tacrolimus (literature-derived priors)
3. **Sample**：trough (C0) + ideally 1-2 additional timepoints for individual estimate
4. **Bayesian posterior**：priors + observed → individual CL + V → individualized dose recommendation
5. **CYP3A5 expressers (\*1/*1 or \*1/*3)**: 30-50% lower trough at same dose; need higher dose
6. **DDI**：CYP3A4 inhibitor (azoles) → reduce dose 50-75%
7. **Output**：recommended next dose + predicted trough + 95% CI
8. **Iterate**：after each TDM sample, update model and refine

## ★ 排除/不做的事
- **Trough-only proportional adjustment**：忽略 individual PK，inaccurate
- **Single sample Bayesian without prior**：need PopPK prior
- **CYP3A5 genotype 不考虑**：% Asian / African 表达 CYP3A5 高比例需 higher dose
- **Concomitant drug list 不更新**：DDI 持续影响
- **Time of sample 不准**：trough should be exactly pre-dose; off-time invalidate
- **Disease state 不考虑**：hepatic dysfunction reduce CL；need adjust
- **Switch IV/PO 不重新 estimate**：absorption changes

## ★ 失败模式
- **Sample timing error**：not true trough → over/under estimate
- **Drug-drug interaction onset**：starting / stopping CYP3A inhibitor causes trough swing
- **Genotype未测**：assume wild-type but actual express → 30-50% off
- **Hepatic / renal dysfunction**：CL changes, model needs adjust
- **Compliance issues**：patient miss dose → trough misleading
- **Active metabolite contribution**：tacrolimus metabolite not measured but immunosuppressive
- **Lab assay variability**：immunoassay vs LC-MS 差 ~15%

## Lessons → seeds for rules
1. **Bayesian forecasting > trough-only**
2. **CYP3A5 genotype** mandatory for tacrolimus
3. **Concomitant medication review** at every TDM
4. **Sample timing strict** (true trough)
5. **Disease state covariate** in model
6. **Active metabolite consideration**
7. **Lab assay method documented**
