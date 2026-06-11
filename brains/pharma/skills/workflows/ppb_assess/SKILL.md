---
name: ppb_assess
description: |
  Plasma protein binding fu — equilibrium dialysis (gold standard) +
  ultrafiltration (cross-check) + concentration-dependence (3–5 levels) +
  species comparison + disease-state plasma (hypoalbuminemia / uremia).
  Reports albumin vs AAG binding hint for acidic vs basic drug.

  v0.1 STATUS: stub. Real implementation requires either a wet-lab data
  ingest (case-008 references published equilibrium dialysis values) or an
  in-silico predictor (PKCSM / ADMET-AI / PaDEL features).
inputs:
  compound_name: str
  smiles: str | null
  is_acidic: bool   # albumin vs AAG hint
  in_vitro_data: list[
    method: "equilibrium_dialysis|ultrafiltration|in_silico"
    species: str
    concentration_uM: float
    fu: float
    plasma_state: "normal|hypoalbuminemic|uremic"
  ] | null
outputs:
  fu_human:                {value: float, ci_95: [float, float], method: str}
  fu_concentration_table:  list[{conc_uM: float, fu: float}]   # linearity check
  species_comparison:      dict[str, float]
  disease_state_shifts:    dict[str, float]
  binding_protein_hint:    "albumin|alpha1_acid_glycoprotein|both"
  ddi_displacement_risk:   "low|moderate|high"
  flags: list[str]   # "single_method_only", "single_concentration", "in_silico_only"
env: praxis-pharma
status: stub
stage: design|execution|reporting
domain: pk
host_env: praxis-pharma
---

# ppb_assess (v0.1 stub)

Real v0.2 implementation:

1. **Equilibrium dialysis** (gold) — Spectra/Por dialysis membrane; 6h, 37°C,
   matched plasma vs PBS buffer; LC-MS quantification.
2. **Ultrafiltration** — Centrifree 30 kDa, 4°C, 30 min, 2000g; correct for
   non-specific binding to membrane (subtract control).
3. **Concentration sweep** — 0.1, 1, 10, 100 μM (cover therapeutic range);
   non-linear binding flag if Δfu > 2-fold across range.
4. **Species comparison** — human / rat / dog / monkey; cross-species fu
   must be measured separately, NEVER scaled by allometry (case-008).
5. **Hypoalbuminemia plasma** — spike-in test or sample from cirrhotic patient.
6. **In-silico predictor** triage only (ADMET-AI / PKCSM ~70-80% accuracy);
   flag `in_silico_only` if no in vitro data.

Soft Reviewer warning: single-method or single-concentration → downgrade
confidence_label one step.

## 输出契约

```json
{
  "skill_id": "ppb_assess",
  "n_compounds": 0,
  "admet_csv": "",
  "diagnostics": {
    "brain": "pharma",
    "archetype": "pharma"
  }
}
```
