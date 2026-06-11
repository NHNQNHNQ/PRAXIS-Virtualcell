---
case_id: pharma-011-pediatric-tacrolimus-poppk
task: poppk
input_compound: tacrolimus
drug_class: small_mol
target_population: pediatric
target_indication: transplant
route_of_admin: PO
tools:
- NONMEM
- R popPK suite
- allometric scaling
- maturation function
key_paper_doi: 10.1111/bcp.12013
status: draft
provenance:
  source_type: literature
  extracted_at: '2026-04-30'
  extraction_confidence: low
  extraction_method: rule_based_heuristic
  unverified_details:
  - heuristic-extracted ★ sections require human review before promote
tags:
- tacrolimus
- pediatric
- popPK
- CYP3A5
- kidney_transplant
- maturation
---

# Population pharmacokinetics and dosing optimization of tacrolimus in pediatric kidney transplant patients

## Background
Tacrolimus is a key immunosuppressant in pediatric kidney transplantation but exhibits high pharmacokinetic variability driven by CYP3A5 polymorphism and developmental pharmacology. Standard adult popPK models do not extrapolate accurately to children — clearance scales sub-linearly with body weight and additionally varies with maturation of CYP3A4 and intestinal P-glycoprotein expression.

## What I actually did
TODO — extract methods / inputs / outputs from source paper.

## ★ 排除的 dose / population / 方法
- Patients should not be dosed using fixed mg/kg without genotype
because the inter-genotype variability dominates body-weight scaling.
- We avoided extrapolation to neonates
younger than 1 month (insufficient data) and excluded patients on concurrent
CYP3A inhibitors during the parameter estimation phase to reduce
confounding.

## ★ 失败模式
- The model failed to capture between-occasion variability in patients
experiencing rejection episodes (where CL changes acutely due to inflammation).
- Rejection-state PK is a known limitation; future work should explore
time-varying covariate models.
- We did not validate
prospectively in a separate cohort.
- , asymptotic
exponential) might fit equally well — we did not test alternatives.

## ★ 方法选择决策链
- We chose NONMEM FOCE-I over SAEM because of historical institutional
familiarity; results would likely be equivalent.
- We selected sigmoidal Hill
maturation over linear age-on-CL because the literature (Anderson 2008)
strongly supports the sigmoidal form for CYP3A4 ontogeny.
- The maturation function form (Hill TM50)
is the standard published method but other forms (e.
- We compared model predictions with observed individual concentrations using
Bayesian individual posterior estimates; observed-vs-predicted R² = 0.
- 312 concentration measurements were analyzed with NONMEM
(FOCE-I).

## ★ Validation
- We did not validate
prospectively in a separate cohort.
- The final model showed VPC pass with 87% of binned timepoint observed
medians within the simulated 90% prediction interval.
- We compared model predictions with observed individual concentrations using
Bayesian individual posterior estimates; observed-vs-predicted R² = 0.
- Without the maturation function, adult-derived models
under-predicted CL in toddlers by ~30% and over-predicted in neonates.
- 1 for diagnostic plots, VPC with 1000 simulations.

## Lessons → seeds for rules
TODO — distill 2-5 high-confidence rule candidates from this case.
