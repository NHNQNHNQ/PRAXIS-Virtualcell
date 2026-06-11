---
rule_id: 13-time-course-priors
rule_type: case_distilled
applies_to:
  modality: [scRNA_seq, bulk_RNA_seq, spatial_transcriptomics, CITE_seq, bulk_multiomics, proteomics]
  study_design: time_course
  tissue_class: ALL
  task: [integration, DE, trajectory, batch_correction]
evidence_cases:
  - case_id: omics-015-pijuan-sala-2019-gastrulation-time-course
    page_hint: "What I actually did + Lessons (stage is biology not batch)"
  - case_id: omics-017-demichev-2021-covid-plasma-proteomics
    page_hint: "longitudinal mixed-effect model"
confidence: high
status: active
created: 2026-04-29
---

# Time-course priors — stage is biology, not batch

## Statement
1. **Stage / time / age / pseudotime is biology, NOT batch**.
   `batch_key` must NOT include the time variable; `biology_key` should.
2. **Per-stage / per-timepoint QC thresholds**: cells / tissue change with time
   (size, metabolism, viability). Use stage-stratified QC.
3. **HVG taken across stages: union, not intersection** (different lineage
   markers active at different stages).
4. **Trajectory inference + topology check** (PAGA / force-directed) — UMAP
   alone can fold time backward.
5. **Statistics**: longitudinal designs use mixed-effect models with random
   subject term `(1|donor)`; not pseudobulk-flatten across time.
6. **Multi-seed robust trajectory**: trajectory inference is seed-sensitive;
   ≥ 3 seeds, keep robust branches.

## Decision tree
```
Is stage / time the variable I want to keep?
├─ YES (biology of interest)
│   → batch_key = technical batch only (lane / donor / instrument)
│   → biology_key includes stage/time
│   → integration: MNN / scVI with batch=technical (NOT stage)
│   → DE: ~ stage * condition + (1|donor) for longitudinal
│   → trajectory: Palantir / scVelo / cellRank
└─ NO (time is a nuisance, e.g. batch effect over week of collection)
    → batch_key includes time
    → biology_key excludes time
    → standard rule 04 applies
```

## Evidence
- Case 015 (Pijuan-Sala gastrulation E6.5–E8.5): putting `batch=stage` would
  collapse the development continuum; correct approach is MNN + retain stage
  in design. T (Brachyury) only at E7.5 → if stage is "removed", T appears
  to vary nonsensically.
- Case 017 (Demichev COVID plasma): time × severity covariate; mixed-effect
  with random subject. Not pseudobulk across time per subject.

## Per-tissue / per-modality time-course quirks
- **Embryo / development**: stage labels often ±2-3 hours imprecise; cross-
  validate with morphology + lineage marker.
- **Drug response**: t=0 sample has high inter-donor variance → ratio to
  baseline preferred over absolute.
- **Plasma proteomics longitudinal**: ICU patients have early sampling bias
  (severity-correlated with survival → late samples are mild); covariate
  must include survival censoring.
- **Maternal contamination in early embryo** (case 015 failure): mother RNA
  in dam blood → looks like "early hematopoietic"; pre-filter via Y-chr
  or mother-specific markers.

## Cold-start fallback
- If time variable is unclear → ask user explicitly.
- If only one timepoint per donor: this is NOT a time-course, treat as
  cohort with one snapshot.
