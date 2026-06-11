---
rule_id: 08-admet-hard-stop-list
rule_type: case_distilled
applies_to: {target_class: ALL, modality: ALL, project_phase: ALL}
confidence: high
evidence_cases: [drug-004-admet-multi-parameter]
schema_version: 2
---

# Rule 08: ADMET hard-stop list — auto-reject

## Statement
Any candidate compound predicted to fail any of these endpoints is automatically rejected. User override is allowed only with explicit `--allow-hard-stop` CLI flag (logged to provenance).

| Endpoint                  | Hard-stop threshold                  | Reason                                       |
|---------------------------|--------------------------------------|----------------------------------------------|
| **hERG IC50**             | < 1 μM                               | QT prolongation, Torsades de Pointes risk    |
| **Ames mutagenicity**     | positive                             | Carcinogenicity risk                         |
| **CYP3A4 inhibition**     | strong inhibitor (IC50 < 1 μM)       | Drug-drug interaction risk                   |
| **DILI risk**             | high (model probability > 0.7)       | Drug-induced liver injury                    |

ADMET predictions must come from **at least 2 independent predictors** (ADMET-AI + SwissADME REST + pkCSM REST) and the hard-stop counts as triggered only if **≥2-of-3 predictors agree** the threshold is crossed.

## Why
Single-predictor decisions get ~30% wrong on individual endpoints. Two-of-three voting reduces false-rejects while maintaining false-accept protection on the four endpoints with the highest historical clinical-failure rate. Terfenadine (drug-004) was famously withdrawn for hERG; Vioxx and similar for CYP3A4 / DILI.

## How to apply
- Skill `admet_multi` returns vote consensus + per-endpoint flag.
- Reviewer at execution stage rejects any candidate with `scoring_5d.admet_score.hard_stops_failed` non-empty.
- `confidence_label` automatically downgraded to `low` if any soft-flag triggers (logP > 5, MW > 600, TPSA > 140 unless oral bioavailability not required).
