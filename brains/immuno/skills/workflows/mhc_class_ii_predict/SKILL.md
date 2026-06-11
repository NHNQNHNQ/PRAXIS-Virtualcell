# mhc_class_ii_predict

MHC Class II 13-25mer epitope prediction with register prediction (rule 03).

## Inputs

```json
{
  "protein_sequence": "MFVF...",
  "hla_alleles": ["HLA-DRB1*15:01", "HLA-DPB1*04:01", "HLA-DQB1*06:02"],
  "peptide_length_grid": [13, 15, 18, 21],
  "predictors": ["NetMHCIIpan-4.3", "MARIA", "MixMHC2pred"],   // ≥ 2 (rule 01)
  "promiscuity_threshold": 3
}
```

## Outputs

```json
{
  "epitopes": [
    {
      "peptide": "AVDLSHFLKEKGGL",
      "length": 14,
      "hla_alleles_strong_binding": ["HLA-DRB1*15:01"],
      "core_9mer_consensus": "DLSHFLKEK",
      "register_predicted": 4,
      "flanking_aa": {"N": "AV", "C": "EKGGL"},
      "promiscuity_count": 1,
      "rank": 1
    }
  ]
}
```

## Tools (real runner, Linux)

- NetMHCIIpan-4.3 (binary)
- MARIA (PyTorch)
- MixMHC2pred (open-source)
- MHCflurry-II (alternative)
- IEDB Tepitope (legacy fallback)

## --simulate behavior

Deterministic mock with register variation across the 4 length bins.

## Sanity QC

- ≥ 2 predictor consensus on register (rule 01)
- All input HLA alleles 4-digit format (rule 02)
- All peptide_length_grid ≥ 13 (rule 03)
