# allergen_predict

Allergenicity prediction with WHO criteria + DL classifier consensus (rule 01 + rule 04).

## Inputs

```json
{
  "protein_sequence": "MFVF...",
  "who_criteria_window_aa": 80,
  "who_identity_threshold": 0.35,
  "predictors": ["AllergenOnline", "AllerCatPro", "AlgPred-2.0", "AllerTOP"],
  "conformational_epitope_check": true
}
```

## Outputs

```json
{
  "skill_id": "allergen_predict",
  "n_epitopes": 0,
  "epitopes_csv": "",
  "diagnostics": {
    "brain": "immuno",
    "archetype": "mhc_epitope"
  }
}
```

## Tools (real runner, Linux)

- AllergenOnline (FARRP DB)
- AllerCatPro
- AlgPred-2.0
- AllerTOP
- SDAP (alternative)

## --simulate behavior

Deterministic 4-tool mock + consensus voting.

## Sanity QC

- ≥ 3 tool consensus required for `recommended_action="reject"` (rule 01)
- WHO criteria + DL classifier combined (rule 04)
- conformational epitope check enabled
