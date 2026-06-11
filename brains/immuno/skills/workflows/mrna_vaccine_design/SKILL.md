# mrna_vaccine_design ⭐ MVP

Joint codon-optimize + secondary-structure-aware mRNA design with m1Ψ + Cap1 + UTR.

## Inputs

```json
{
  "antigen_protein_sequence": "MFVF...",
  "host": "human",
  "joint_optimizer": "LinearDesign",
  "utr_set": "BNT162b2" | "custom",
  "m1psi_substitution": true,         // rule 06 (warn-level)
  "cap": "Cap1",
  "polya_length": 120,
  "target_strain_consensus": ["BA.5", "XBB"]
}
```

## Outputs

```json
{
  "mrna_sequence": "AUGUUCGUC...",
  "codon_optimized_orf": "AUGUUC...",
  "utr_5p": "GAGAAUAA...", "utr_3p": "AAGCUC...",
  "polya": "AAAA...",
  "cai_human": 0.88,
  "gc_pct": 56.0,
  "mfe_kcal_per_mol": -425.0,
  "has_m1psi_flag": true,
  "cpg_count": 12,
  "restriction_sites": [],
  "cryptic_splice_count": 1,
  "qc_pass": true
}
```

## Tools (real runner, Linux)

- LinearDesign (joint CAI + MFE optimizer; CPU OK)
- ViennaRNA RNAfold (secondary structure)
- ARNIE (mRNA toolkit)

## --simulate behavior

Deterministic mock optimization with CAI ≥ 0.85 enforced.

## Sanity QC

- CAI ≥ 0.85
- MFE within plausible range for length
- m1psi flag true
- CpG count ≤ baseline (immune-stimulatory minimization)
