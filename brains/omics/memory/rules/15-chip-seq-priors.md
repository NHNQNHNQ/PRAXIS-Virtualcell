---
rule_id: 15-chip-seq-priors
rule_type: case_distilled
applies_to:
  modality: [chip_seq]
  study_design: ALL
  tissue_class: ALL
  task: [QC, peak_calling, replicate_consistency, motif_enrichment]
evidence_cases:
  - case_id: omics-018-landt-2012-chip-seq-encode-guidelines
    page_hint: "Library QC + IDR + peak caller decision tree"
confidence: high
status: active
created: 2026-04-29
---

# ChIP-seq priors (ENCODE-grade)

## Statement
1. **Input control is mandatory** — ChIP without input is uninterpretable.
2. **Library complexity QC** (NSC ≥ 1.05 / 1.1, RSC ≥ 0.8, PBC ≥ 0.5) — fail
   any → consider remaking library, not just deduping.
3. **Peak caller depends on target type**:
   - TF / point-source → MACS2 narrow + IDR
   - Active histone (H3K4me3 / H3K27ac) → MACS2 narrow
   - Repressive histone (H3K27me3 / H3K9me3) → MACS2 broad
   - CUT&RUN / CUT&Tag → SEACR (sparse signal)
4. **Replicate consistency = IDR @ 0.05** (not "intersect peak sets").
5. **Blacklist filter mandatory** (ENCODE-provided + per-tissue empty input).
6. **FRiP**: narrow ≥ 1%, broad ≥ 5%; lower → low-quality IP.
7. **Antibody specificity validated at experimental stage** — analysis cannot
   rescue a non-specific antibody.

## Decision tree
```
ChIP-seq target?
├─ TF (CTCF, GATA1, YY1, etc.) → MACS2 narrow + IDR
├─ H3K4me3 / H3K27ac (active marks) → MACS2 narrow
├─ H3K27me3 / H3K9me3 (repressive) → MACS2 broad --broad-cutoff 0.1
├─ H3K36me3 / mixed → MACS2 broad with --nomodel --extsize
├─ CUT&RUN low input → SEACR stringent
└─ ATAC-seq → MACS2 narrow with --nomodel --shift -75 --extsize 150 (or use ArchR for scATAC, see rule 08)

Replicate consistency?
├─ ≥ 2 biological replicates → IDR
├─ Pseudo-replicate (split sequencing) → IDR (lower confidence)
└─ Single replicate → CAVEAT explicit; rule 05 multi-method consensus violated
```

## Cold-start fallback
- If antibody validation status unknown → flag confidence: medium with caveat.
- If FRiP < threshold → flag confidence: low; recommend antibody review or
  re-IP.
- If no biological replicates → confidence: low; recommend pseudo-replicate
  IDR + caveat.

## Evidence
- Case 018 (Landt 2012 ENCODE guidelines): NSC/RSC/PBC/FRiP thresholds;
  IDR @ 0.05 vs intersect; per-target peak caller table.

## Linked anti-rule sections (rule 11)
ChIP-seq specific anti-rules: no input control, single replicate as final,
narrow caller for repressive marks, missing blacklist filter, IDR replaced
by intersect.
