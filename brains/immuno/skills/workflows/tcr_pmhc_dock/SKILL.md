---
name: tcr_pmhc_dock
description: (auto-generated stub from parity rewrite v2; please fill)
status: green
host_env: af2
---
# tcr_pmhc_dock

TCR-pMHC complex modeling with TCRdock specialized docker (rule 05). Generic PP-dockers (HADDOCK / ClusPro) explicitly rejected.

## Inputs

```json
{
  "tcr_alpha_seq": "...",
  "tcr_beta_seq": "...",
  "peptide": "LLFGYPVYV",
  "hla_allele": "HLA-A*02:01",
  "n_seeds": 5,
  "predictor": "TCRdock" | "AF-Multimer-custom",
  "reference_pdb": "2BNQ"
}
```

## Outputs

```json
{
  "complex_pdb_path": "runs/.../complex.pdb",
  "interface_rmsd_to_ref": 1.85,
  "cdr3_loop_clusters": [{"cluster": 1, "rmsd_within": 0.8, "members": 3}],
  "iptm": 0.74,
  "ptm": 0.69,
  "plddt_mean": 78.0,
  "pae_interface": 6.8,
  "mhc_restriction_class": "HLA_I",
  "specificity_score": 0.82,
  "qc_pass": true
}
```

## Tools (real runner, Linux)

- TCRdock (specialized — phbradley)
- TCRen (alternative)
- ESM-IF (sequence-based binder filter)
- AlphaFold-Multimer with custom MSA
- Rosetta SnugDock

## --simulate behavior

Deterministic mock: interface RMSD < 3 Å vs reference; iPTM ≥ 0.6 over 5 seeds.

## Sanity QC (Reviewer blocks)

- predictor must be TCRdock (not generic HADDOCK/ClusPro/PatchDock) — rule 05
- hla_allele Class I → peptide length ∈ 8-11 (rule 03)
- n_seeds ≥ 5 (multi-seed mandatory)
