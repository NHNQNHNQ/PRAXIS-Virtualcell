---
name: fih_dose_design
description: |
  First-in-human starting dose: NOAEL → HED (BSA scaling for small mol; BW for
  biologic) / safety factor → MRSD. For immune-modulating biologic, also
  compute MABEL from in vitro receptor occupancy. Output the LOWER of MRSD vs
  MABEL when both apply, plus an escalation scheme (3+3 default; BLRM optional).
inputs:
  noael_per_species: dict[str, float]    # mg/kg/d, key = species (rat/dog/monkey/...)
  drug_class: "small_mol|biologic|antibody"
  immune_modulator: bool                  # forces MABEL co-method
  body_weights_kg:                        # default {rat:0.25, dog:10, monkey:5, human:70}
    type: dict | null
  km_factors:                             # FDA HED conversion factors (Km = BW/BSA)
    type: dict | null
  safety_factor: float                    # default 10 for small_mol; 50-100 for novel mechanisms
  receptor_occupancy_curve:               # for MABEL; dict of dose_uM → fractional_RO
    type: dict | null
  target_max_RO: float                    # default 0.10 (10% RO ceiling per MABEL guideline)
outputs:
  most_sensitive_species: str
  most_sensitive_noael_mg_per_kg: float
  hed_mg_per_kg: float
  mrsd_mg: float
  mabel_mg: float | null
  recommended_starting_dose_mg: float     # min(MRSD, MABEL) when both
  escalation_scheme: list[float]          # dose levels for 3+3 default
  dlt_definition: str
  flags: list[str]
env: praxis-pharma (numpy)
status: ready
stage: design|execution|reporting
domain: pk
---

# fih_dose_design

Implements FDA "Guidance for Industry: Estimating the Maximum Safe Starting
Dose in Initial Clinical Trials for Therapeutics in Adult Healthy Volunteers"
(2005) + EMA "Guideline on strategies to identify and mitigate risks for
first-in-human and early clinical trials" (2017, post-TGN1412).

## Method

1. **Most-sensitive species** — argmin(NOAEL_mg/kg) across species.
2. **HED (small mol, BSA)** — `HED = NOAEL × (Km_animal / Km_human)` where Km = BW/BSA factor (rat 6, dog 1.86, monkey 3, human 37).
3. **HED (biologic, BW linear)** — `HED = NOAEL × (BW_animal / BW_human)` (FDA endorses BW scaling for protein therapeutics).
4. **MRSD** — `HED / safety_factor`. Default 10× for small mol with mature MoA; 50–100× for novel / immune mechanisms.
5. **MABEL** (immune modulator only) — interpolate receptor_occupancy_curve to find dose for `target_max_RO` (default 10%); convert in vitro [drug] → in vivo dose using fu × V.
6. **Recommended** — `min(MRSD, MABEL)` if both available; MRSD only otherwise.
7. **Escalation** — 3+3 default: `[D_start, 2× D_start, 3.3× D_start, 5× D_start, 7× D_start, 10× D_start]` capped at clinical max. BLRM if user opts in.
8. **DLT** — CTCAE grade 3+ non-hematologic / grade 4 hematologic; protocol-defined.

## CLI
```bash
python -m skills.workflows.fih_dose_design.run \
    --noael '{"rat":50,"dog":30,"monkey":40}' \
    --drug-class small_mol --safety-factor 10 \
    --out runs/<task>/fih/result.json
```

## Sanity (used in G6)
- **Inputs**: rat NOAEL 50 mg/kg/d, dog 30, monkey 40; small_mol; safety_factor 10.
- **Expected**:
  - most_sensitive_species == "dog"
  - HED ≈ 30 × (1.86/37) = 1.5 mg/kg = 105 mg/70-kg human
  - MRSD ≈ 10.5 mg
  - escalation scheme has 5+ dose levels.

## ★ Hard rules
- `noael_only_for_immune_modulator`: if `immune_modulator==true` and MABEL not provided → flag `mabel_required` (Reviewer HR-04 bounces).
- `single_species`: if only 1 species in `noael_per_species` → flag `single_species_noael`.

## 输出契约

```json
{
  "skill_id": "fih_dose_design",
  "n_compounds": 0,
  "admet_csv": "",
  "diagnostics": {
    "brain": "pharma",
    "archetype": "pharma"
  }
}
```
