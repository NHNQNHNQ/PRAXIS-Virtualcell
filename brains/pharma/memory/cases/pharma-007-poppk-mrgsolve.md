---
case_id: pharma-007-poppk-mrgsolve
task: population_pk_modeling
target_drug: vancomycin (TDM-required, narrow window)
inputs: [sparse clinical samples from many patients]
tools: [NONMEM (gold standard, commercial), nlmixr2 (open source), Pumas.jl, mrgsolve, Monolix]
key_paper_doi: 10.1146/annurev.pharmtox.46.120604.141115
status: validated
---

# Population PK：vancomycin in clinical patients (sparse data)

## Background
Population PK (popPK) 模型 = nonlinear mixed-effects (NLME) model：固定效应（typical PK params）+ 个体随机效应（patient variability）+ 残差误差。**应用**：sparse sampling clinical data + covariate identification（age, weight, kidney function 影响 PK）+ TDM (therapeutic drug monitoring)。Vancomycin 是 TDM 经典 case。

## What I actually did
1. **Data**：~200 patients × 2-3 PK samples each + covariate (age, weight, eGFR, scr)
2. **Base model selection**：1- vs 2-compartment with first-order elimination
3. **Parameter estimation**：FOCE (NONMEM) or SAEM (Monolix/Pumas)
4. **Covariate analysis**：scan eGFR, weight, age 等是否显著解释 between-patient variability
   - eGFR strongly affects CL (vancomycin renally cleared)
   - Weight affects Vd
5. **Final model**：CL = θ_CL × (eGFR/100)^0.75；V = θ_V × (BW/70)
6. **Goodness-of-fit**：observed vs predicted scatter, residual plots, VPC (Visual Predictive Check)
7. **Bayesian individual estimates (Empirical Bayes)**：每 patient 后验 estimate
8. **Dose recommendation**：given target trough 15-20 mg/L → individualized dose

## ★ 排除/不做的事
- **Rich sampling popPK overkill**：rich data 用 NCA + traditional 简单
- **Skip covariate analysis**：unexplained variability 高让 individualization 不可
- **Statistical significance only for covariate**：clinical relevance 同等重要 (effect size > 20% change)
- **VPC 不做**：no validation plot 无 model trust
- **Single dataset estimate**：cross-validation / split-sample necessary
- **Covariate without biological rationale**：spurious correlation

## ★ 失败模式
- **Convergence failure**：NLME hard to converge with poor initial estimates
- **Covariate collinearity**：weight + BMI + body surface area 强相关，独立性不可分
- **Special population gap**：obese / pediatric / elderly 不在原 dataset → individualization 错
- **Time-varying covariate**：eGFR 在 ICU patient 急变；single value 模型失败
- **Saturable kinetics**：high concentration nonlinearity
- **Bioassay interference**：concentration measurement 不准
- **Adherence in outpatient**：dosing time noise 影响 PK

## Lessons → seeds for rules
1. **NLME with FOCE/SAEM** > naive pooled
2. **Covariate analysis biological + statistical**
3. **VPC 必步**
4. **Cross-validation / split-sample**
5. **Time-varying covariate** for ICU / dynamic
6. **Empirical Bayes individual** for TDM
7. **Special population external validation**
