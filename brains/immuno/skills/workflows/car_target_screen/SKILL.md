# car_target_screen

CAR-T target candidate screening with multi-source expression panel + safety risk score.

## Inputs

```json
{
  "candidate_genes": ["CD33", "CD123", "CLL-1"],
  "indication": "cancer_aml",
  "sources": ["DepMap", "GTEx", "HPA", "TabulaSapiens"],
  "essential_tissue_panel": ["liver", "heart", "lung", "brain"],
  "affinity_tuning_required": true
}
```

## Outputs

```json
{
  "targets": [
    {
      "gene": "CD33",
      "tumor_expression_pct": 0.92,
      "normal_essential_max_TPM": 0.4,
      "surface_localization_confidence": 0.91,
      "differential_expression_ratio": 18.5,
      "escape_risk_score": 0.32,
      "on_target_off_tumor_risk": "low",
      "recommended_affinity_kd_nm": 35
    }
  ]
}
```

## Tools (real runner, Linux/cloud)

- DepMap API (cell-line dependency)
- GTEx API (normal tissue expression)
- HPA API (Human Protein Atlas — surface confidence)
- TabulaSapiens (cellxgene scRNA-seq atlas)
- Compartments DB (subcellular localization)

## --simulate behavior

Mock expression panel for CD19/CD33/CD123/CLL-1.

## Sanity QC

- diff_expr_ratio ≥ 10 (tumor:normal)
- surface_localization_confidence ≥ 0.7
- multi-source: ≥ 3 of 4 sources agree (rule 07 warn-level)
