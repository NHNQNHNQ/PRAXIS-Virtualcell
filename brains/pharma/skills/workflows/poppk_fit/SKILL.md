---
name: poppk_fit
description: |
  Population PK fit (NLME with FOCE-style two-stage approximation). Fits a
  1-cmt IV-bolus model with covariates: CL = θ_CL × (CrCL/100)^θ_crcl,
  V = θ_V × (WT/70). Estimates θ + ω² (between-subject) + σ² (residual) by
  alternating individual MAP + population MLE. Visual Predictive Check (VPC):
  posterior simulate 1000 trajectories per design point, return 5/50/95
  percentiles vs observed.
inputs:
  data_csv: "subject,time_h,conc,dose_mg,interval_h,wt_kg,crcl_mL_min"
  drug: str
  model: "1cmt_iv_bolus"     # extensible later to oral / 2cmt
  covariates: list[str]      # default ["wt", "crcl"]
  vpc_n_simulations: int     # default 500
outputs:
  population_estimates:
    theta_cl: float
    theta_v: float
    theta_crcl_exp: float
    omega2_cl: float
    omega2_v: float
    sigma2_prop: float
  individual_estimates: list[
    subject: int
    eta_cl: float
    eta_v: float
    cl: float
    v: float
  ]
  vpc:
    bin_edges_h: list[float]
    observed_p5: list[float]
    observed_p50: list[float]
    observed_p95: list[float]
    simulated_p5: list[float]
    simulated_p50: list[float]
    simulated_p95: list[float]
    timepoints_within_90pct_pi_pct: float    # G5 acceptance — fraction of observed bins within 5–95%ile
  goodness_of_fit:
    n_subjects: int
    n_obs: int
    final_objective_function_value: float
    obs_vs_pred_r2: float
  flags: list[str]
env: praxis-pharma (numpy + scipy)
status: ready
stage: design|execution|reporting
domain: pk
---

# poppk_fit

NONMEM-style NLME fit. We don't use real NONMEM (commercial); pymc would also
work but adds a heavy dependency. Implementation is a two-stage iterative MAP:

1. **Initial estimates** — geometric mean (median CL, median V from naive pooled
   approximation): for each subject solve `D = CL × AUC` and `V × ke = CL`.
2. **Outer loop** (population step): given current η_i estimates, fit population
   θ via least-squares minimization on the typical predictions (per-subject,
   weighted by 1/σ²).
3. **Inner loop** (individual step): for each subject, MAP estimate η_i given
   current population θ + ω².
4. **Convergence**: alternate until θ change < 0.5% or 30 outer iterations.
5. **VPC** — for each subject's design points, sample 1000 (η_CL, η_V) ~
   N(0, ω²), compute predicted concentration, and return 5/50/95 percentiles
   per binned timepoint vs observed bin percentiles. The G5 acceptance is
   `≥80% of observed bin medians fall within the simulated 5–95% interval`.

## CLI
```bash
python -m skills.workflows.poppk_fit.run \
    --data tests/fixtures/poppk_vanco_synthetic.csv \
    --drug vancomycin --vpc-sims 500 \
    --out runs/<task>/poppk/result.json
```

## Sanity (G5)
- **Drug**: vancomycin in clinical patients (case-007 reference: Goti 2018 TDM 40:212;
  Roberts 2011 AAC 55:2704). True parameters used to generate fixture:
  - θ_CL = 4.5 L/h × (CrCL/100)^0.8
  - θ_V = 0.7 × WT (L)
  - ω²_CL = 0.15, ω²_V = 0.10, σ²_prop = 0.04
  - 30 simulated patients × 4 sparse samples each (peak/mid/trough × 2 dose intervals)
- **Pass criterion**: `vpc.timepoints_within_90pct_pi_pct ≥ 0.80`
- **Hard rule**: if user input has < 10 subjects → flag `insufficient_subjects` (case-007 lesson).

## 输出契约

```json
{
  "skill_id": "poppk_fit",
  "n_compounds": 0,
  "admet_csv": "",
  "diagnostics": {
    "brain": "pharma",
    "archetype": "pharma"
  }
}
```
