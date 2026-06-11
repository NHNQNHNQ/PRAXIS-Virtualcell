---
name: tcr_seq_repertoire
description: (auto-generated stub from parity rewrite v2; please fill)
status: green
host_env: praxis-immuno
---
# tcr_seq_repertoire ⭐ MVP

TCR-seq (bulk or scTCR) → clonotypes + diversity + GLIPH2 cluster + OOF rate (rule 05).

## Inputs

```json
{
  "fastq_paths": ["tcr_R1.fq.gz", "tcr_R2.fq.gz"],
  "modality": "bulk" | "sc",
  "reference_organism": "human",
  "clustering": "GLIPH2" | "TCRdist3",
  "antigen_db": "VDJdb" | "McPAS" | "both"
}
```

## Outputs

```json
{
  "clones": [
    {"clone_id": "C0001", "V": "TRBV9", "J": "TRBJ2-7", "CDR3_aa": "CASSLDRDREAFF",
     "frequency": 0.018, "public_or_private": "private"}
  ],
  "diversity_metrics": {"Shannon": 5.2, "D50": 87, "Gini": 0.42, "Chao1": 1240},
  "gliph_clusters": [{"cluster_id": "G001", "members": ["C0001", "C0007"],
                      "shared_motif": "SLDR.RE", "db_hits": ["EBV-BMLF1"]}],
  "oof_rate": 0.18,
  "qc_pass": true
}
```

## Tools (real runner, Linux)

- MiXCR-4.6 (V/J/CDR3 segmenter + UMI)
- IgBLAST (cross-validate)
- Immcantation (Change-O / Alakazam diversity)
- scirpy (for scTCR from 10x)
- GLIPH2 / TCRdist3 (specificity clustering)

## --simulate behavior

Deterministic 100 mock clones with realistic V/J distribution + cluster mixture.

## Sanity QC

- OOF_rate < 30% (rule 05)
- Rarefaction step always run before cross-sample comparison
- D50 + Shannon reported for clonality
