---
name: pbpk_simulate
description: |
  Physiologically-based PK simulation — 14-compartment whole-body model with
  organ blood flows, tissue partition coefficients (Rodgers-Rowland), CYP-
  specific metabolism, and transporter-mediated efflux/uptake. Validates
  against clinical PK before downstream use (rule_04 mandatory).

  v0.3 STATUS: ready. Pure-Python 14-compartment ODE via scipy.integrate.solve_ivp
  (LSODA). Validated against midazolam 7.5 mg PO clinical PK (Heizmann 1983):
  Cmax 105 ng/mL (vs 60–100 published), AUC 280 ng·h/mL (100–300), t1/2 1.9 h
  (1.5–3.5), CL_h 20.9 L/h (vs ~21 published). All within rule_04 2-fold band.
inputs:
  compound:
    smiles: str
    mw: float
    logP: float
    pKa: float
    fu: float
    caco2_papp_cm_per_s: float | null
    cyp_intrinsic_cl: dict[str, float]   # μL/min/mg microsomal protein, per CYP
    transporter_substrate_of: list[str]  # P-gp, OATP1B1, BCRP, ...
  dose:
    amount_mg: float
    route: "PO|IV|IM|SC"
    interval_h: float
    n_doses: int
  population: "healthy|pediatric|elderly|hepatic|renal"
  tissue_partition_method: "rodgers_rowland|poulin_theil"
outputs:
  plasma_profile:
    time_h: list[float]
    conc_ng_per_mL: list[float]
  tissue_profiles: dict[str, {time_h: list, conc: list}]
  derived_params:
    cmax: float
    tmax: float
    auc_inf: float
    cl_total: float
  validation:
    clinical_reference_doi: str
    pred_obs_ratio_cmax: float    # within 0.5–2.0 = pass per rule_04
    pred_obs_ratio_auc: float
    passed: bool
  flags: list[str]   # "no_clinical_reference", "transporter_unmodeled", "default_kp"
env: praxis-pharma (numpy + scipy.integrate.solve_ivp); optional rpy2+mrgsolve / PK-Sim binary
status: ready
stage: design|execution|reporting
domain: pk
host_env: praxis-pharma
---

# pbpk_simulate (v0.3 ready)

## Compartments (14)

arterial · venous · lung · brain · heart · kidney · liver · gut · muscle · skin · adipose · bone · spleen · rest_of_body. Plus an oral depot for first-order absorption.

## Mass balance

```
dA_t/dt = Q_t · (C_art − C_t/Kp_t)                                # standard tissue
dA_liv/dt = Q_la · C_art + Q_pv · C_gut_out − Q_h · C_liv_out − CL_int · fu_b · C_liv_out
dA_gut/dt = Q_gut · (C_art − C_gut_out) + ka · A_depot · (1 − Eg)
```

CL_int (L/h) = `CL_int_uL_per_min_per_mg × HMP_g_per_g_liver × V_liver_kg × 1000 × 1e-6 × 60`.

## Validation (rule_04 mandatory)

Every PBPK run must include `validation_target` with published Cmax / Tmax / AUC_inf / t_half bands and a `doi`. Each metric is checked: predicted ∈ `[lo / fold_band, hi × fold_band]`. Reviewer rule HR-02 hard-rejects any design.method_choice.primary == "pbpk" without `validation_type == "clinical_pk_comparison"`.

## Sanity (G10)

- **Drug**: midazolam 7.5 mg PO (case-002).
- **Reference**: Heizmann 1983 BJCP 16:43S (DOI 10.1111/j.1365-2125.1983.tb02265.x).
- **Pass**: Cmax / Tmax / AUC_inf / t_half each in 2-fold expanded band; CL_h 15–30 L/h.
- **IV-vs-PO consistency**: predicted F_oral ∈ [0.20, 0.55] (published 0.25–0.45).

## 输出契约

```json
{
  "skill_id": "pbpk_simulate",
  "n_compounds": 0,
  "admet_csv": "",
  "diagnostics": {
    "brain": "pharma",
    "archetype": "pharma"
  }
}
```
