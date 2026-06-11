---
skill_id: off_target_predict
description: Off-target prediction for SpCas9 sgRNA — CFD score (Doench 2016) + Cas-OFFinder enumeration + genomic context filter (CDS/UTR/intron/intergenic/essential gene) + risk tier (high/med/low) + clinical wetlab validation flag.
inputs:
  - sgrna: 20-nt protospacer
  - organism: hg38 / mm10 / ...
  - candidate_off_targets: optional list of 20-mer + PAM (else uses Cas-OFFinder if installed, else seeded baseline)
  - clinical: bool (forces clinical wetlab recommendations)
outputs:
  - per_off_target: list of {target_seq, pam, mismatches, cfd, retained_activity, genomic_context, risk_tier}
  - cfd_cumulative: 1 - prod(1 - cfd_i)
  - clinical_wetlab_flag: GUIDE-seq + CHANGE-seq required if clinical
sanity_check: VEGFA known promiscuous sgRNA (Tsai 2015) — top-5 in silico hits include validated sites; cumulative CFD < 1 (max 0.5)
reference_case: crispr-002-off-target-prediction-cfd
---

## Protocol

1. Score perfect-match (cfd = 1.0).
2. For each candidate off-target:
   - Compute CFD via `tools.sgrna_scoring.cfd_score`
   - Apply genomic-context tier (CDS=high, UTR=med, intron/intergenic=low, essential=BLOCK)
3. Cumulative CFD = 1 - prod(1 - cfd_i)
4. Risk stratify:
   - HIGH: CFD ≥ 0.5 AND in CDS / essential
   - MED: CFD ≥ 0.2 OR in CDS / regulatory
   - LOW: CFD < 0.2 in intron/intergenic
5. Clinical flag: if --clinical, force GUIDE-seq + CHANGE-seq + CIRCLE-seq recommendation (case crispr-002 lesson).

## Don't

- ❌ Trust in silico CFD alone for clinical sgRNAs — always wetlab validate (GUIDE-seq).
- ❌ Ignore essential genes (DepMap CKE) hits even at low CFD.
- ❌ Forget personalized off-target check for therapeutic sgRNAs.

## 输出契约

```json
{
  "skill_id": "off_target_predict",
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
