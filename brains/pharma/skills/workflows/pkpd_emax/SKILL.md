---
name: pkpd_emax
description: |
  Joint or sequential PK-PD modeling — Emax model (Effect = Emax × C / (EC50 + C))
  for receptor occupancy or biomarker; tumor-PD integrative model for oncology
  (long-term tumor size dynamics). Per case-009 (pembrolizumab flat-dose
  rationale) + rule_06 + FDA E-R requirement for oncology BLA.

  v0.1 STATUS: stub. Real implementation is straightforward:
  scipy.optimize.curve_fit on Emax with bootstrap CI; tumor PD ODE with
  scipy.integrate.solve_ivp.
inputs:
  pk_data:   "subject,time_h,conc CSV path"
  pd_data:   "subject,time_h,effect CSV path"
  endpoint:  "receptor_occupancy|tumor_size|biomarker"
  joint_or_sequential: "joint|sequential"
  emax_constraint:  "free|fixed_at_observed_max"
outputs:
  emax_estimates:
    emax: {value: float, ci_95: [float, float]}
    ec50: {value: float, ci_95: [float, float]}
    hill_slope: {value: float, ci_95: [float, float]} | null
  exposure_response:
    dose_levels_mg: list[float]
    predicted_effect: list[float]
    saturation_dose_mg: float    # dose ≥ this gives < 5% incremental effect
  flat_dose_recommendation:
    is_saturated_at_clinical_dose: bool
    recommended_flat_dose_mg: float | null
  flags: list[str]   # "single_endpoint", "no_safety_e_r", "tumor_outcome_emax_only"
env: praxis-pharma
status: stub
stage: design|execution|reporting
domain: pkpd
host_env: praxis-pharma
---

# pkpd_emax (v0.1 stub)

Real v0.2 implementation (~150 LOC):

1. **PK fit** — 1-cmt or 2-cmt depending on data richness; capture Cmin, Css.
2. **Emax fit** — `scipy.optimize.curve_fit(emax_fn, conc, effect, p0=[Emax_guess, EC50_guess])`;
   bootstrap CI: 1000 resamples on (subject, residual) pairs.
3. **Tumor PD model** (oncology) — Stein-Bonate two-compartment tumor:
   `dTumor/dt = k_growth · Tumor − k_kill · drug_effect · Tumor`;
   ODE integrate, fit kₖ to longitudinal tumor size data.
4. **Saturation dose** — find dose where `dEffect/dDose < 0.05 × Effect_max`.
5. **Flat-dose recommendation** — if clinical dose ≥ saturation, recommend flat
   (case-009 pembrolizumab 200 mg q3w → ~99% RO → flat dose justified).
6. **Safety E-R** — must run separately on AE rate vs exposure (FDA E-R
   requirement); flag `no_safety_e_r` if missing.

Soft Reviewer warning if endpoint is `tumor_size` and only Emax fit (no
integrative tumor model) — case-009 lesson.

## 输出契约

```json
{
  "skill_id": "pkpd_emax",
  "n_compounds": 0,
  "admet_csv": "",
  "diagnostics": {
    "brain": "pharma",
    "archetype": "pharma"
  }
}
```
