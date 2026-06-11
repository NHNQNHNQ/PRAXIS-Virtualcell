---
name: allometric_scale
description: |
  Cross-species allometric scaling of clearance and volume of distribution.
  Power-law fit log(CL) vs log(BW) across ≥ 3 species; reports 95% CI on the
  exponent. Optional corrections: MLP (Maximum Lifespan Potential, for highly
  protein-bound / hepatic-extraction-low drugs), brain-weight (CNS-active),
  fu-correction (unbound CL). Flags single-species or n<3 with hard error.
inputs:
  species_data: list[
    species: str
    body_weight_kg: float
    clearance_mL_per_min: float
    fu: float | null            # plasma free fraction (only needed for fu_corrected)
    brain_weight_kg: float | null  # only for brain-weight correction
  ]
  correction: "none|MLP|brain_weight|fu_corrected"
  target_species: str           # default "human"
  target_body_weight_kg: float  # default 70
  target_brain_weight_kg: float | null
outputs:
  exponent: float
  exponent_ci_95: [float, float]
  intercept_log: float
  r2: float
  predicted_clearance_mL_per_min: float
  predicted_clearance_ci_95: [float, float]
  correction_factor: float       # 1.0 if correction=none
  flags: list[str]               # "single_species_no_ci" → HR-01; "exponent_out_of_band"; "poor_fit"
env: praxis-pharma (numpy + scipy)
status: ready
stage: scoping|design|execution|reporting
domain: pk
host_env: praxis-pharma
---

# allometric_scale

Allometric power-law: `CL = a × BW^b`. Empirical b ≈ 0.75 for hepatic-cleared
drugs, ≈ 1.0 for renally-cleared, ≈ 0.6–0.8 with protein-binding mismatches.

## Method

1. **Filter** — drop species with missing CL or BW.
2. **Hard-fail** if `len(species) < 3` → `flags=["single_species_no_ci"]`, returns
   exponent=null (caught by Reviewer rule HR-01).
3. **Fit** — `log10(CL)` vs `log10(BW)` via `scipy.stats.linregress`. Report slope
   (= exponent), intercept, R², and 95% CI on slope from standard error
   (`slope ± t(0.975, df=n-2) × stderr`).
4. **Predict** for target species: `log10(CL_target) = intercept + slope × log10(BW_target)`.
5. **Apply correction** (multiplicative on predicted CL):
   - **MLP (Maximum Lifespan Potential)** — uses Sacher 1959 formula:
     `MLP = 185.4 × BW^0.636 × BrW^0.225` (years). Correction factor =
     `mean(MLP_animals) / MLP_target` (drugs with hepatic CL benefit; reduces
     overprediction in long-lived species). Requires brain weights.
   - **brain_weight** — `BrW^b_brain` substitution; b_brain ≈ 0.97 for CNS drugs.
   - **fu_corrected** — fit on unbound CL = CL/fu instead of CL_total, then
     re-multiply by fu_target.
6. **Predict CI** — propagate slope CI through the BW exponent:
   `CL_lo = 10^(intercept + slope_lo × log10(BW))`, similarly `CL_hi`.

## CLI
```bash
python -m skills.workflows.allometric_scale.run \
    --csv tests/fixtures/allometric_warfarin_species.csv \
    --correction MLP \
    --target-bw 70 --target-brain 1.4 \
    --out runs/<task>/allometric/result.json
```

## Sanity (G3)
- **Positive**: caffeine 5 species (mouse/rat/rabbit/monkey/dog), Lelo 1986 BJCP 22:177; published human CL ≈ 110 mL/min; expected exponent ≈ 0.82, fit R² > 0.95.
  - `0.5 ≤ pred_CL_caffeine / 110 ≤ 2.0` (within 2-fold)
  - `exponent_ci_95` reported (non-null)
  - exponent in `[0.6, 0.95]`
- **Negative (honesty test)**: warfarin 4 species (Mahmood 1998 J Pharm Sci 87:1428); published human CL ~3.3 mL/min; simple BW^0.75 overpredicts ~3-5× (high protein binding, fu≈0.005). Skill must EITHER overpredict (fold>2) OR raise `exponent_out_of_band`; honesty is the requirement, not magical correctness.
- **HR-01**: single-species input → `single_species_no_ci` flag, exponent=null, prediction=null.

## ★ Hard warnings (Reviewer feeds)
- `single_species_no_ci` (n<3) — Reviewer rule HR-01: "Single species allometric without CI".
- `exponent_out_of_band` (exponent < 0.55 or > 0.95) — likely renal or active transport; allometric inappropriate.
- `poor_fit` (R² < 0.85) — suggest IVIVE or PBPK instead.

## 输出契约

```json
{
  "skill_id": "allometric_scale",
  "n_compounds": 0,
  "admet_csv": "",
  "diagnostics": {
    "brain": "pharma",
    "archetype": "pharma"
  }
}
```
