---
skill_id: multiplex_array_design
description: Cas12a (As / Lb / enAsCas12a) crRNA-array design for multi-gene KO. Find TTTV PAMs in early constitutive exons; assemble 5'-DR-spacer-DR-... array with self-cleaving direct repeats; recommend RNP electroporation; triple-negative sort reminder; cross-locus translocation amplicon-seq plan.
inputs:
  - genes: list of {name, target_seq} (or just gene names with target_seq fetched)
  - cas12a_variant: AsCas12a (default) | LbCas12a | enAsCas12a (recommended for clinical)
  - clinical: bool (forces RNP delivery, blocks lentivirus)
outputs:
  - per_gene: {best_crRNA, pam, target_position, off_target_score}
  - crrna_array: full 5'-DR-spacer1-DR-spacer2-...-3' for Pol III U6/H1 expression
  - cloning_oligos: F/R for vector cloning
  - delivery_recommendation: RNP_electroporation (vs lentivirus blocked for clinical)
  - sort_panel: flow-cytometry markers for triple-negative selection (CAR-T case)
  - translocation_pcr_plan: amplicon-seq across locus pairs to detect inter-locus rearrangement
sanity_check: TRAC + B2M + CD52 (CAR-T case 005) — array length ≥ 3 spacers, all TTTV PAMs, RNP recommended for clinical, triple-negative sort flagged
reference_case: crispr-005-cas12a-multiplex
---

## Direct repeats (DR scaffold)

- AsCas12a (Acidaminococcus): `TAATTTCTACTAAGTGTAGAT`
- LbCas12a (Lachnospiraceae): `TAATTTCTACTGTTGTAGAT`
- enAsCas12a: same DR as AsCas12a

## Don't (Reviewer-enforced)

- ❌ Lentivirus delivery for clinical CAR-T (continuous Cas12a → off-target accumulation).
- ❌ Triple KO without triple-negative sort (residual TCR+ cells = GVHD risk).
- ❌ B2M KO without HLA-E knock-in plan (NK cell killing).
- ❌ Loose PAM (TTTN with default Cas12a; only enAsCas12a allows TYCV/TATV).

## 输出契约

```json
{
  "skill_id": "multiplex_array_design",
  "n_guides": 0,
  "guides_csv": "",
  "best_guide": {
    "seq": "",
    "cfd_score": 0.0,
    "mit_score": 0.0
  },
  "diagnostics": {
    "brain": "crispr",
    "archetype": "crispr"
  }
}
```
