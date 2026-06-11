---
skill_id: sgrna_design_score
name: sgrna_design_score
host_env: PRAXIS-CRISPR
status: green
description: Score and rank SpCas9 sgRNA candidates with composite (Doench RS2 + CFD + GC + cloning + frameshift bias). Outputs top-5 cloning oligos for lentiCRISPR v2.
inputs:
  - target_seq: DNA region (early constitutive exon CDS) — string OR
  - gene + organism: HGNC symbol + genome build → fetches transcript via Ensembl
outputs:
  - top_k: list of {sgrna, pam, strand, composite, doench, cfd_off_target_inv, gc, cloning, frameshift_bias, cloning_oligo_F, cloning_oligo_R}
sanity_check: TP53/HeLa — top 5 composite ≥ 0.6, Doench ≥ 0.5
reference_case: crispr-001-spcas9-knockout-tp53
---

## Protocol

1. Resolve input: if `--target-seq` given, use directly; else fetch transcript from Ensembl.
2. Pick early constitutive exon (synthesis § crispr-001: avoid last exon NMD escape, avoid alternatively spliced exons).
3. Find SpCas9 NGG PAM target sites (`tools.seq_utils.find_spcas9_ngg_targets`).
4. Score each protospacer:
   - Doench RS2 simplified (`tools.sgrna_scoring.doench_score_protospacer`)
   - GC% in [40, 60] (penalty for outliers)
   - Cloning friendly (no BsmBI/BbsI sites)
   - Frameshift bias (DeepHF heuristic — preference for cuts between different bases)
5. Composite weighted score per `config/agent.yaml` `scoring_sgrna.weights`.
6. Rank top-5; emit lentiCRISPR v2 cloning oligos (BsmBI overhangs).
7. Polyploid-cell warning: if cell_context in {HeLa, U2OS, ...}, recommend dual-guide or single-cell clone.

## Don't (Reviewer-enforced)

- ❌ Single sgRNA recommendation when --cell HeLa (or any polyploid line) without explicit `--single-guide` flag.
- ❌ Composite < 0.4 in top-5 → Reviewer warning.
- ❌ Cloning_friendly = 0 in top-5 (BsmBI/BbsI in protospacer).

## 输出契约

```json
{
  "skill_id": "sgrna_design_score",
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
