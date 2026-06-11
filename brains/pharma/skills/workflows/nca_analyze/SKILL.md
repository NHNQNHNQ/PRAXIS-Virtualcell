---
name: nca_analyze
description: |
  Noncompartmental analysis (NCA) for plasma concentration-time data.
  Linear-up / log-down trapezoidal AUC, terminal log-linear lambda_z (R² > 0.9),
  Cmax/Tmax, t1/2, CL/F, Vss/F. Bioequivalence helper (90% CI of geometric mean ratio).
inputs:
  conc_table: "CSV path or list[{subject:int, time_h:float, conc:float}]"
  dose_mg: float
  route: "PO|IV|IM|SC"
  llq: float                # lower limit of quantification (BLOQ → 0 below first peak, NA after Tmax)
  lambda_z_n_points: int    # default 3 (auto-pick last n with R²>0.9)
outputs:
  per_subject:
    subject: int
    cmax: float
    tmax_h: float
    auc_last: float           # linear-up/log-down trapezoid
    auc_inf: float            # auc_last + Clast/lambda_z
    auc_extrap_pct: float     # > 20% → flagged unreliable
    half_life_h: float
    lambda_z: float
    lambda_z_r2: float
    lambda_z_n_points: int
    cl_per_f: float           # mg / (mg/L * h) → L/h, only if dose given
    vss_per_f: float | null
    flags: list[str]          # e.g., "auc_extrap_high", "lambda_z_r2_low", "predose_nonzero"
  summary:
    n: int
    geomean_auc: float
    geomean_cmax: float
    cv_pct_auc: float
env: praxis-pharma (numpy + scipy)
status: ready
stage: scoping|design|execution|reporting
domain: pk
---

# nca_analyze

Pure-Python NCA implementation. Reference algorithms in PKNCA (R) and Bailer 1988 / Yeh & Kwan 1978.

## Method

1. **Sort + dedupe** per subject by time.
2. **Pre-dose check**: if conc[t=0] > LLQ × 5 → flag `predose_nonzero` (washout incomplete).
3. **AUC_last** (linear-up / log-down):
   - For each (t_i, t_{i+1}) where C_{i+1} ≥ C_i (rising / plateau): `(C_i + C_{i+1})/2 * (t_{i+1} - t_i)`
   - Else (falling, both > 0): `(C_i - C_{i+1}) / ln(C_i / C_{i+1}) * (t_{i+1} - t_i)`
4. **λz fit**: starting from `lambda_z_n_points` last samples, linear regression of ln(C) vs t. Iteratively drop earliest of the window if R² < 0.9 until R² ≥ 0.9 or fewer than 3 points remain (then flag `lambda_z_r2_low`).
5. **AUC_inf** = AUC_last + C_last / λz; **% extrapolated** = 1 − AUC_last/AUC_inf; flag if > 0.20.
6. **t1/2** = ln(2) / λz.
7. **CL/F** = Dose / AUC_inf; **Vss/F** (statistical-moment, IV only): MRT × CL where MRT = AUMC_inf / AUC_inf.
8. **Bioequivalence helper** (when ≥2 formulations): per-subject log(AUC_T) − log(AUC_R), bootstrap or t-distribution 90% CI on geometric mean ratio.

## CLI
```bash
python -m skills.workflows.nca_analyze.run \
    --conc tests/fixtures/nca_airway.csv \
    --dose-mg 50 --route PO --llq 0.05 \
    --out runs/<task>/nca/result.json
```

## Sanity (G1)
- **Dataset**: case-006 airway nasal-spray PK reference; published AUC_inf = 1247 ng·h/mL (literature mean).
- **Pass criterion**: `|AUC_calc − AUC_pub| / AUC_pub < 0.05`.

## ★ Mandatory output fields
- `flags` must be present (empty list ok).
- `auc_extrap_pct` always reported.
- Per-subject table even if N=1 (no auto-pooling means).

## 输出契约

```json
{
  "skill_id": "nca_analyze",
  "n_compounds": 0,
  "admet_csv": "",
  "diagnostics": {
    "brain": "pharma",
    "archetype": "pharma"
  }
}
```
