---
name: tdm_bayesian
description: |
  Bayesian forecasting for therapeutic drug monitoring (TDM). Given population
  PK priors (CL_pop, V_pop, ω²_CL, ω²_V) + 1–2 measured concentrations +
  patient covariates (CYP3A5 genotype, weight, eGFR), MAP estimate of individual
  ETAs and predict next dose to hit target trough. Tacrolimus is the canonical
  use case (case-010). Compare to trough-only proportional scaling baseline to
  quantify individualization gain.
inputs:
  drug: "tacrolimus|vancomycin|digoxin|... (drives prior selection)"
  patient_covariates:
    body_weight_kg: float
    age_y: float | null
    egfr_mL_min_1_73m2: float | null
    cyp3a5_genotype: "*1/*1|*1/*3|*3/*3" | null
    concomitant_strong_cyp3a_inhibitor: bool | null
    hepatic_dysfunction: "none|mild|moderate|severe" | null
  observations: list[
    time_after_last_dose_h: float
    conc: float          # ng/mL
    is_trough: bool
  ]
  current_dose:
    dose_mg: float
    interval_h: float
  target:
    trough_target_ng_per_mL: float
outputs:
  individual_eta:
    eta_cl: float
    eta_v: float
  individual_pk:
    cl: float                    # L/h
    v: float                     # L
    half_life_h: float
  predicted_next_dose:
    dose_mg: float
    predicted_trough_ng_per_mL: float
    predicted_trough_ci_95: [float, float]
  baseline_proportional_dose_mg: float    # trough-only scaling for comparison
  individualized_adjustment_pct: float    # |new − baseline| / baseline
  flags: list[str]                        # "single_concentration_only", "missing_genotype_for_tacro"
env: praxis-pharma (numpy + scipy)
status: ready
stage: scoping|design|execution|reporting
domain: pk
---

# tdm_bayesian

Bayesian / Empirical-Bayes individualization. Implementation:

1. **Prior selection** — `priors_table` keyed by drug:
   - **tacrolimus** (Andrews 2019 CPT 105:986; Storset 2014 BJCP 78:509):
     - CL_pop = 21.0 L/h (CYP3A5 *3/*3 non-expresser baseline, BW 70 kg)
     - V_pop = 200 L
     - ω²_CL = 0.25 (CV ~50%); ω²_V = 0.20
     - Covariates: WT^0.75 on CL, WT linear on V, CYP3A5 *1 carrier × 1.6 on CL,
       strong CYP3A inhibitor × 0.4 on CL, severe hepatic × 0.6 on CL
     - σ_prop² = 0.04 (proportional residual error CV ~20%)
   - **vancomycin** (Goti 2018 Ther Drug Monit 40:212): CL=4.5×(CrCL/100)^0.8,
     V=0.7×WT, ω²_CL=0.15, ω²_V=0.10
2. **Apply covariates** to prior CL_pop, V_pop → individual prior means.
3. **MAP objective** — minimize over (η_CL, η_V):
   ```
   −2·LL = Σ_i ((C_obs_i − C_pred_i(η)) / (σ_prop·C_pred_i))² + (η_CL/ω_CL)² + (η_V/ω_V)²
   ```
   where `CL_ind = CL_prior · exp(η_CL)`, `V_ind = V_prior · exp(η_V)`.
4. **PK model** — 1-cmt IV bolus + 1st-order elimination, multiple dosing
   superposition; for tacrolimus use trough-at-steady-state closed form:
   `C_trough = (D / (CL · τ)) · (1 / (1 − exp(−ke·τ))) · exp(−ke·τ)`
   with ke = CL/V, τ = interval.
5. **Predict next dose** — solve for D such that predicted trough = target.
6. **Baseline (proportional scaling)** — `D_baseline = D_current · (target / observed_trough)`.
7. **Individualization gain** — `|D_new − D_baseline| / D_baseline`.

## CLI
```bash
python -m skills.workflows.tdm_bayesian.run \
    --drug tacrolimus \
    --patient tests/fixtures/tdm_tacro_patient.json \
    --target-trough 8.0 \
    --out runs/<task>/tdm/result.json
```

## Sanity (G4)
- **Patient**: simulated CYP3A5 *1/*1 expresser (Asian / African ancestry common
  in case-010), 70 kg, no concomitant inhibitor, currently 4 mg q12h, observed
  trough 4.5 ng/mL.
- **Metric**: `individualized_adjustment_pct` = `|D_with_genotype − D_without_genotype| / D_without_genotype`
  for the genotype-aware starting dose targeting 8 ng/mL trough.
- **Pass criterion**: `0.30 ≤ pct ≤ 2.5`. Andrews 2019 reports CL × 1.5 for *1
  carriers, but with a 1-cmt steady-state trough formula the dose ratio amplifies
  to ~1.5–2.5× because the trough accumulation factor changes too. The
  qualitative claim — knowing genotype matters materially (≥30% change) — is the
  invariant and is preserved.
- **Genotype-missing test**: tacrolimus call without `cyp3a5_genotype` must raise
  `missing_genotype_for_tacro` flag (case-010 hard rule).

## ★ Hard warnings
- `single_concentration_only` (n_obs == 1) — Bayesian still works but flag.
- `missing_genotype_for_tacro` (CYP3A5 not provided) — case-010 hard rule.

## 输出契约

```json
{
  "skill_id": "tdm_bayesian",
  "n_compounds": 0,
  "admet_csv": "",
  "diagnostics": {
    "brain": "pharma",
    "archetype": "pharma"
  }
}
```
