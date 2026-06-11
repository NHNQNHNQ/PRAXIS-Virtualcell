---
rule_id: _default_bootstrap
rule_type: cold_start_defaults
applies_to:
  edit_type: ALL
  cell_context: ALL
evidence_cases: []
confidence: cold_start
---

# Cold-start defaults (loaded when n_cases < 5 in pool)

When the case library has fewer than 5 same-edit-type cases relevant to a query, fall back to these defaults — they encode the "safe" choice in each axis.

## Editor defaults
- KO: SpCas9 (NGG) — most validated; switch to enAsCas12a only for multiplex.
- A→G: ABE8e (latest, highest activity).
- C→T: CBE4max.
- Small insert/del: PE3 + epegRNA.
- Large insert (>20 bp): HDR with PAM-destroyed donor (or AAV donor if >1.5 kb).
- mRNA target: RfxCas13d (CasRx) — compact, high activity.

## Cell-context defaults
- Diploid cancer line (HeLa, U2OS) → recommend dual-guide; warn polyploid.
- Primary T / HSC → RNP electroporation; mRNA + LNP for in vivo.
- iPSC → HDR enhancer (NU7441/Scr7) mandatory.
- HAP1 (haploid) → preferred for SGE (analysis simpler).
- In vivo liver → LNP+mRNA preferred; AAV requires NAb screen.

## Off-target defaults
- In silico CFD always; if clinical, force GUIDE-seq + CHANGE-seq.
- Top-3 off-targets always amplicon-seq verified.
- DepMap CKE intersection BLOCKS the design.

## Output defaults
- Top 5 sgRNA candidates with composite score (Doench + CFD + GC + cloning + frameshift_bias).
- Confidence label: `cold_start` (degrade default `medium`).
- Always cite ≥1 case_id (even if from cross_pool).
- reproduce.sh emitted with exact CLI to re-run.

## Reviewer hard-stops (always active)
- Off-target high in essential gene
- HDR donor not PAM-destroyed
- BE/PE missing bystander prediction
- Single junction PCR validation for KI
- Single time point screen
- AAV clinical without NAb screen
- Triple KO without negative sort
- Cas13 used as DNA editor
