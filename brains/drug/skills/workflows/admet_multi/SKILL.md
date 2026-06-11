---
name: admet_multi
description: |
  Multi-method ADMET prediction with 2-of-3 vote consensus across ADMET-AI + SwissADME REST + pkCSM REST.
  Implements rule 08 hard-stop list (hERG IC50 < 1 μM, Ames+, strong CYP3A4, high DILI → auto-reject).
inputs:
  smiles_list: list[str]
outputs:
  per_compound:
    smiles: str
    endpoints:
      hERG_IC50_uM:    {value: float, predictors_agreed: int, hard_stop_failed: bool}
      Ames:            {pos: bool, predictors_agreed: int, hard_stop_failed: bool}
      CYP3A4_inhib:    {strong: bool, predictors_agreed: int, hard_stop_failed: bool}
      DILI_risk:       {high: bool, predictors_agreed: int, hard_stop_failed: bool}
      logP, logS, MW, TPSA, HBA, HBD, F_oral_pct: float
    hard_stops_failed: list[str]
    soft_flags: list[str]
    admet_composite_score: float (0..1)
env: praxis-drug-admet (admet-ai + GPU optional, CPU OK)
status: ready
stage: design|execution|reporting
domain: admet
host_env: praxis-drug-admet
---

# admet_multi

For each input SMILES, query 3 independent ADMET predictors:

1. **ADMET-AI** (Therapeutics Data Commons) — local Python package, GPU-accelerated if available
2. **SwissADME REST** — `http://www.swissadme.ch/index.php` (best-effort, may not have REST API at all times; in v0 we shell out to swissadme-cli if installed, else fallback to local heuristics)
3. **pkCSM** REST — `http://biosig.unimelb.edu.au/pkcsm/`

For each hard endpoint (hERG / Ames / CYP3A4 / DILI), apply **2-of-3 voting**:
- If ≥ 2 predictors agree the threshold is crossed → `hard_stop_failed: true`
- Else → `hard_stop_failed: false`

Soft endpoints (logP, MW, TPSA, etc.) are reported as numbers; soft flags include logP > 5, MW > 600, TPSA > 140 (when oral bioavailability is required).

`admet_composite_score` ∈ [0, 1]:
- 1.0 if all hard stops passed and no soft flags
- 0.0 if any hard stop failed
- in-between for soft-flag-only cases (linear with soft flag count up to 5)

## CLI
```bash
python -m skills.workflows.admet_multi.run --smiles "CCO" --json
python -m skills.workflows.admet_multi.run --smiles-file lib.smi --out runs/<task>/admet/
```

## 输出契约

```json
{
  "skill_id": "admet_multi",
  "n_compounds": 0,
  "best_score": 0.0,
  "compound_csv": "",
  "diagnostics": {
    "brain": "drug",
    "archetype": "drug"
  }
}
```
