---
name: mhc_class_i_predict
description: (auto-generated stub from parity rewrite v2; please fill)
status: green
host_env: praxis-immuno
---
# mhc_class_i_predict ⭐ MVP

Predict MHC Class I-restricted 8-11mer epitopes for a protein sequence + HLA-I allele(s) with multi-method consensus (rule 01).

## Inputs

```json
{
  "protein_sequence": "MFVF...",            // 1-letter aa
  "hla_alleles": ["HLA-A*02:01"],           // 4-digit IMGT (rule 02)
  "peptide_lengths": [8, 9, 10, 11],
  "predictors": ["NetMHCpan-4.1", "MHCflurry-2", "BigMHC"],   // ≥ 2 (rule 01)
  "top_k": 50,
  "self_proteome_blast": true                // rule 04
}
```

## Outputs

```json
{
  "skill_id": "mhc_class_i_predict",
  "n_epitopes": 0,
  "epitopes_csv": "",
  "diagnostics": {
    "brain": "immuno",
    "archetype": "mhc_epitope"
  }
}
```

## Tools (real runner, Linux)

- NetMHCpan-4.1 (binary, requires academic license)
- MHCflurry-2 (pip, CPU OK)
- BigMHC (PyTorch, GPU recommended)
- NetMHCstabpan-1.0 (binary)
- NetChop-3.1 (binary)

## --simulate behavior

Deterministic seed from `(sequence + alleles + lengths)` → emit 20 mock peptides with score distribution mimicking real EL_rank distribution. `passed_qc` tied to `consensus_strong_binders ≥ 2/3`.

## Sanity QC (Reviewer)

- `n_predictors_used ≥ 2` (rule 01)
- `hla_alleles[]` all 4-digit (rule 02)
- `peptide_lengths` all ≤ 11 (rule 03)

## Sanity test (deferred to Linux)

SARS-CoV-2 spike (P0DTC2) + HLA-A*02:01 → IEDB known-epitope recall ≥ 80% (per `tests/sanity/test_mhci_netmhcpan_recall.py`).
