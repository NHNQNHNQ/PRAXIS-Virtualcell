---
case_id: pharma-020-vancomycin-auc-targeted-tdm
task: auc_targeted_therapeutic_drug_monitoring
input_compound: vancomycin
target_drug: vancomycin
target_population: patient
drug_class: small_mol
target_indication: infection_MRSA
route_of_admin: IV
tools: [Bayesian forecasting (InsightRX, Tucuxi, ClinFTrials), AUC24-targeted dosing, popPK with Goti/Roberts priors, two-sample Bayesian estimator]
key_paper_doi: 10.1093/cid/ciaa303
status: validated
provenance:
  source_type: literature
  citation: "Rybak MJ et al. 2020 Clin Infect Dis 71:1361-1364 'Therapeutic Monitoring of Vancomycin for Serious Methicillin-resistant Staphylococcus aureus Infections: A Revised Consensus Guideline of the American Society of Health-System Pharmacists, the Infectious Diseases Society of America, the Pediatric Infectious Diseases Society, and the Society of Infectious Diseases Pharmacists'"
  extracted_at: 2026-05-01
  extraction_confidence: high
tags: [vancomycin, AUC24, TDM, MRSA, Bayesian_forecasting, IDSA_2020, paradigm_shift_from_trough_to_AUC, AKI_reduction]
---

# vancomycin AUC24-targeted TDM: 从 trough-only 到 Bayesian AUC 的范式转变

## Background
40+ 年来 vancomycin TDM 用 trough only：target trough 15-20 mg/L for serious MRSA。但累积证据显示：
- AUC24/MIC ≥ 400 是真实疗效驱动指标（不是 trough）
- Trough 15-20 mg/L 通常对应 AUC24 800-1000+ mg·h/L → **过度暴露 → AKI**
- AKI rate at trough-targeted dosing: 15-25%
- AUC-targeted dosing maintains AUC24 400-600 → AKI rate drops to 5-10%

**2020 IDSA + ASHP + PIDS + SIDP guideline (Rybak 2020)**: paradigm shift recommends:
- **AUC24 = 400-600 mg·h/L** as primary target (assuming MIC = 1)
- Bayesian forecasting (1-2 samples) > trough-only for AUC estimation
- Target trough 15-20 mg/L "abandoned" for serious MRSA (specifically NOT the recommendation)
- Population PK Bayesian estimator software (e.g., InsightRX, Tucuxi, ClinFTrials, RightDose) with patient-specific covariates (eGFR, weight, age) + 1-2 samples → posterior AUC24 estimate

**Clinical impact**：
- AKI rate ↓ ~50% in real-world adoption
- TTE clinical efficacy (clearance of bacteremia, mortality) maintained or improved
- Cost-effective despite Bayesian software cost (AKI hospitalization saving outweighs)

## What I actually did
1. **Patient covariates**: weight, age, eGFR (or CrCL)
2. **popPK prior** (Goti 2018 TDM 40:212 or Roberts 2011 AAC 55:2704):
   - CL = θ_CL × (CrCL/100)^0.8
   - V = θ_V × WT (0.7 L/kg typical)
3. **Two-sample Bayesian collection**:
   - Peak (1-2 h post end-of-infusion)
   - Trough (just before next dose)
   - OR: 4-12h post-infusion + trough
4. **Bayesian posterior**: software computes individual CL, V, AUC24 from prior + 2 samples
5. **AUC24 = Dose × Tau / (CL × interval_h × 24/interval_h)** = total dose / CL
6. **Dose recommendation**:
   - Target AUC24 = 400-600 mg·h/L (assuming MIC = 1)
   - Adjust dose so calculated AUC24 hits target
   - Example: 70 kg patient, eGFR 80 → predicted CL 4.5 L/h → for AUC 500: dose = 500 × 4.5 / 24 × 24h = 2250 mg/24h ≈ 1500 mg q12h or 1000 mg q8h
7. **Iterative refinement**: subsequent samples update posterior; weekly re-evaluation for prolonged therapy
8. **Continue / switch decision**: AUC24 < 400 → increase dose; AUC24 > 600 → decrease dose; persistently > 800 with creatinine rise → suspend, switch to daptomycin or linezolid

## ★ 排除的 dose / population / 方法
- **Trough-only targeted TDM at 15-20 mg/L** for serious MRSA: causes ~50% over-target AUC24 → AKI ↑ 2×; hard-rejected by 2020 IDSA guideline.
- **One-sample Bayesian for steady-state estimate**: insufficient information; posterior CI wide; 2 samples (peak + trough or two non-trough) preferred.
- **Trough alone in renal impairment**: CrCL changes daily in AKI patients; static covariate model fails (case-007 lesson). Daily TDM with re-estimation.
- **AUC computation by trapezoidal on sparse 2-sample data**: unreliable; Bayesian posterior estimator > trapezoidal for sparse sampling.
- **Continuous infusion vs intermittent**: CI gives steady plasma concentration; AUC is just Css × 24; same 400-600 target. Shifts from peak/trough to steady-state monitoring.
- **TDM in patients on CRRT**: CRRT alters CL substantially; standard popPK prior invalid; need CRRT-specific prior (Goti 2018 CRRT subset).

## ★ 失败模式
- **Real-world adoption lag**: ~50% of US hospitals still trough-targeting in 2022 surveys; equipment/software/training gap.
- **Bayesian software cost**: $50-200k institutional license; small hospitals can't afford; default back to trough.
- **AUC computation algorithm variability**: different Bayesian engines give 10-20% different AUC estimates from same data; clinician must understand what algorithm is being used.
- **Pediatric extrapolation**: adult vanco popPK doesn't extrapolate to pediatric; need pediatric-specific popPK prior (Le 2013 Pediatr Infect Dis J 32:e155 + maturation function rule_12).
- **AKI risk persists at AUC ≤ 600 in critically ill**: ICU patients have additive risk factors (nephrotoxic co-meds, sepsis-AKI); AUC band may need lower bound (300-500) for high-risk subgroups.
- **MIC variability**: AUC24/MIC ≥ 400 assumes MIC = 1 mg/L; lower-MIC isolates may achieve target at lower AUC, higher-MIC isolates need higher AUC. MIC not always available (BMD requires lab time).

## ★ 方法选择决策链
- **AUC24-targeted Bayesian** (IDSA 2020 mandate) > trough-only for serious MRSA infections.
- **Two-sample optimal**: peak + trough OR two non-trough samples within first 24-48 h of dosing.
- **Bayesian estimator software**: InsightRX, Tucuxi, ClinFTrials, RightDose all FDA-cleared / validated.
- **CRRT-specific prior** (Goti CRRT subset, or Roberts 2018 CRRT model).
- **Pediatric prior**: Le 2013, with maturation function (rule_12).
- **Continuous vs intermittent infusion**: CI mathematically simpler (AUC = Css × 24); preferred for very high-dose / sustained-target applications.
- **Switch to alternative anti-MRSA** (daptomycin, linezolid, ceftaroline) when AUC ≥ 800 with rising creatinine despite dose reduction — rule out vanco-induced AKI vs sepsis-AKI.

## ★ Validation
- **Rybak 2020 IDSA consensus**: synthesizes 50+ studies + meta-analyses; level A recommendation.
- **Multiple AKI-AUC linkage studies**: Lodise 2008 + Bosso 2011 + Aljutayli 2019 + Filippone 2017 — consistent finding of AUC > 600-700 → AKI ↑.
- **Real-world adoption studies post-2020**: Anderson 2022 OFID + Pai 2014 — Bayesian AUC adoption reduced AKI rate from ~20% to ~10% in matched cohorts.

## Lessons → seeds for rules
1. **AUC > trough** for narrow-window infections where exposure-response is integral over time.
2. **Bayesian forecasting > naive computation** for sparse-sample TDM (case-010 + case-020 generalization).
3. **Software-as-medical-device** for popPK Bayesian estimation; institutional adoption requires resource investment.
4. **Pediatric / CRRT / special-population priors** distinct from standard adult prior (rule_08 + rule_12 generalization).
5. **AUC target depends on pathogen MIC**; not single fixed number for all isolates.
6. **Paradigm shifts in TDM** are gradual: 40 years of trough-only → AUC adoption takes 5-10 years post-guideline.
