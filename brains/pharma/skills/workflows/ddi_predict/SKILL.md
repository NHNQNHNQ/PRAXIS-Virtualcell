---
name: ddi_predict
description: |
  Static drug-drug interaction prediction following FDA "In Vitro DDI Studies"
  guidance (2020). Supports reversible inhibition, mechanism-based inactivation
  (MBI), and induction. Multi-CYP composite when substrate has fm > 0.1 in ≥ 2
  enzymes. Risk classification: weak (<2x) / moderate (2–5x) / strong (>5x).
inputs:
  substrate:
    name: str
    cyp_fm: dict[str, float]      # e.g., {"CYP3A4": 0.95, "CYP2C9": 0.05}; sum need not be 1
  perpetrators: list[
    name: str
    mechanism: "reversible|mbi|inducer"
    target_cyp: str
    Ki_uM: float                  # for reversible/MBI
    kinact_per_min: float | null  # only for MBI
    Ind_max: float | null         # max fold induction (for inducers)
    EC50_uM: float | null         # induction EC50
    plasma_unbound_max_uM: float  # [I]u,max
    fu_gut_inhibitor: float | null
    intestinal: bool              # apply gut-CYP3A correction
  ]
  cyp_kdeg_per_h: dict[str, float] | null   # default table loaded from cyp_params.json
outputs:
  per_substrate_cyp:
    cyp: str
    auc_ratio_total: float        # 1/((fm·Σ(1/Ri)) + (1−fm)) form
    auc_ratio_per_perpetrator: dict[str, float]
    risk: "none|weak|moderate|strong"
    mechanism_summary: list[str]  # e.g., ["clarithromycin: MBI on CYP3A4 (kinact/KI=…)"]
  composite_auc_ratio: float
  hard_warnings: list[str]        # e.g., "single-CYP only", "MBI without kdeg", "no transporter check"
env: praxis-pharma (numpy)
status: ready
stage: scoping|design|execution|reporting
domain: pk
---

# ddi_predict

Implements FDA static "Basic + Mechanistic Static" DDI models. Equations:

- **Reversible inhibition** (per CYP): `Ri = 1 + [I]u / Ki`
- **Mechanism-based inactivation** (per CYP): `Ri = (kdeg + (kinact·[I]u)/(KI + [I]u)) / kdeg` — equivalent to `1 + (kinact·[I]u) / (kdeg·(KI + [I]u))`.
- **Induction** (per CYP): `Ri = 1 / (1 + d·Ind_max·[I]u / (EC50 + [I]u))` where d = 1 (FDA default).
- **Combined per CYP** with multiple perpetrators: `R_combined = Π Ri` (product of individual ratios; multiplicative effect).
- **Per-CYP AUC ratio for substrate**: `AUCR_cyp = R_combined`.
- **Composite AUC ratio across CYPs** (substrate metabolized by multiple CYPs): `AUCR = 1 / (Σ_cyp(fm,cyp / R_cyp) + (1 − Σ fm,cyp))` — this is the FDA-endorsed multi-CYP form.
- **Gut CYP3A correction** (oral substrate, intestinal=true perpetrator): additional factor `1/(1 + ([Ig]u/Ki))` where [Ig]u ≈ dose / (250 mL × MW); not always available — emit warning.

## CLI
```bash
python -m skills.workflows.ddi_predict.run \
    --substrate-name simvastatin --substrate-cyp '{"CYP3A4":0.95}' \
    --perpetrator-name clarithromycin --mechanism mbi \
    --target-cyp CYP3A4 --Ki 10 --kinact 0.07 --Iu-max 1.5 \
    --out runs/<task>/ddi/result.json
```

## Sanity (G2)
- **Case**: simvastatin (CYP3A4 fm 0.95) + clarithromycin (MBI: KI=10 μM, kinact=0.07 min⁻¹=4.2 hr⁻¹), [I]u,max ~1.5 μM, kdeg(CYP3A4 liver) = 0.0193 hr⁻¹.
- **FDA observed**: ~10–12× AUC ratio (Backman 1998 mean 10×; FDA review ~11.9×; PBPK 12–15× depending on Iu); contraindicated.
- **Pass criterion**: `5 ≤ auc_ratio ≤ 15` AND `risk == "strong"` AND `single_cyp_only` warning fired.

## ★ Hard warnings (Reviewer feeds)
- `single_cyp_only`: substrate fm sums to one CYP — Reviewer rule HR-03.
- `mbi_without_kdeg`: kdeg missing for that tissue/CYP — falls back to liver default + warning.
- `no_transporter_check`: substrate is OATP1B1/3 / P-gp client (e.g., statins) — warn that transporter DDI may dominate.

## 输出契约

```json
{
  "skill_id": "ddi_predict",
  "n_compounds": 0,
  "admet_csv": "",
  "diagnostics": {
    "brain": "pharma",
    "archetype": "pharma"
  }
}
```
