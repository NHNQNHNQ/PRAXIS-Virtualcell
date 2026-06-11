---
rule_id: 06-anti-rules-from-NEG-cases
schema_version: 1
scope: anti_pattern_systematization
applies_to:
  cell_task: ALL
  image_modality: ALL
confidence: high
causal_tag: causal
n_evidence_neg_cases: 12
created_at: 2026-05-02
last_updated: 2026-05-02
status: active
---

# Rule 06 — 12 anti-rules systematized from NEG- cases

This rule formalizes 12 forbidden patterns extracted from `memory/cases/_neg/NEG-*.md`. Each anti-rule is anchored to ONE NEG- case that documents the failure mode + a published paper. Reviewer hard-stops at design-plan time; anti-retrieval index (`indices/anti/`) vetoes candidate plans at retrieval time.

## The 12 anti-rules (confidence: high; causal_tag: causal)

| # | Anti-rule | NEG- anchor | Required correction |
|---|---|---|---|
| 1 | Default-watershed segmentation on touching cells without DL | `NEG-WATERSHED-DEFAULT` | Try Cellpose / StarDist / Mesmer first |
| 2 | Per-image-only profile for HCS profiling (no per-cell, no per-well median) | `NEG-PER-IMAGE-PROFILE` | per-cell features → per-well median |
| 3 | Raw plate-level Z-score without B-score / SSMD on edge-effect plate | `NEG-Z-NORM-NO-PLATE` | median-polish B-score or per-plate DMSO median+MAD |
| 4 | Pearson alone for colocalization (no Manders, no Costes randomization) | `NEG-PEARSON-ONLY` | Pearson + Manders + Costes block-shuffle (3-method consensus) |
| 5 | 2D segmentation per-plane on 3D z-stack (no `do_3D=True`, no anisotropy) | `NEG-2D-ON-3D` | cellpose `do_3D=True` + anisotropy, OR 3D-aware tool |
| 6 | Linear intensity for IMC / CODEX (no arcsinh) | `NEG-LINEAR-IMC` | arcsinh transform with cofactor=5 |
| 7 | Phenotype clustering without reference MoA compound anchor | `NEG-CLUSTER-NO-ANCHOR` | ≥ 3 reference compounds + nearest-anchor MoA assignment |
| 8 | IMC pipeline without hot-pixel filter | `NEG-NO-HOTPIXEL-IMC` | Steinbock `--filter-pixels` or scipy median_filter 3×3 + 5× threshold |
| 9 | SMLM acquisition > 5 min without drift correction | `NEG-NO-DRIFT-SMLM` | Cross-correlation drift correction or fiducial-marker tracking |
| 10 | 2P calcium imaging without motion correction | `NEG-NO-MOTION-CALCIUM` | NoRMCorre or Suite2p ImageReg upstream of CNMF |
| 11 | Cellpose with default diameter (no per-image estimation) | `NEG-CELLPOSE-DEFAULT-DIAMETER` | Explicit diameter from prior knowledge OR cellpose `--diameter 0` auto |
| 12 | LAP frame-to-frame tracking without gap closing on movies > 20 frames | `NEG-NO-GAP-CLOSING` | Jaqaman two-step LAP (frame + segment), TrackMate, or btrack |

## How this rule is used

### Retrieval-time veto (anti-retrieval)
`scripts/retrieval/test_anti_retrieval.py` enumerates the 12 NEG- cases and verifies each blocks its target anti-pattern keyword query. 12/12 self-consistency must pass before any new design plan can use the retrieval pipeline.

### Reviewer-time hard-stop
Each of the 12 anti-rules maps to one Reviewer check in `agents/prompts/reviewer.md`. If a design_plan triggers any anti-rule pattern (e.g., `pipeline_steps` lists "watershed" only on touching cells), Reviewer emits `passed: false` with `required_repairs` enumerating the violated anti-rule.

The IMC hot-pixel anti-rule (#8) is also enforced by the dedicated unit test `tests/sanity/test_reviewer_imc.py`.

### RMCP write-back exclusion
Per Phase 2 (Triage) of the RMCP pipeline: any candidate rule extracted via `scripts/distill/extract.py` that matches one of the 12 anti-rule patterns is automatically `discard`ed with bucket-tag `failure_mode`. NEVER promotes to `memory/rules/`.

## Provenance — every anti-rule is anchored to a real-paper-documented failure mode

| # | Anchored paper |
|---|---|
| 1 | Stringer 2021 Cellpose Nat Methods (Fig 1 watershed vs DL F1 benchmark) |
| 2 | Caicedo 2017 Nat Methods (Cell Painting per-well median vs per-image variance) |
| 3 | Brideau 2003 J Biomol Screen (B-score introduction + raw-Z FPR quantification) |
| 4 | Bolte 2006 J Microsc (colocalization 3-method consensus standard) |
| 5 | Pachitariu 2022 Cellpose 2.0 Nat Methods (`do_3D` + anisotropy introduction) |
| 6 | Giesen 2014 Nat Methods (IMC dynamic range; arcsinh recommendation) |
| 7 | Bray 2016 Nat Protoc (Cell Painting reference compound anchor protocol) |
| 8 | Giesen 2014 Nat Methods (IMC detector hot-pixel artifacts) |
| 9 | Ovesný 2014 Bioinformatics (ThunderSTORM drift-correction mandate) |
| 10 | Giovannucci 2019 eLife (CaImAn motion correction mandate) |
| 11 | Stringer 2021 Cellpose Nat Methods (diameter as critical hyperparameter) |
| 12 | Ershov 2022 TrackMate 7 Nat Methods (Jaqaman two-step LAP + gap closing) |

All 12 source DOIs are CrossRef-verified (these are the same DOIs as the corresponding positive cases in `memory/cases/cell-001..020.md`).

## Causal-vs-correlational tagging

All 12 are tagged `causal_tag: causal` because each documents a mechanistic failure (distance-transform topology fails on touching cells; raw Z aliases edge gradient; etc.) that transfers across all data sharing the same mechanism. None are correlational (within-family or near-family only).

## Empirical confirmations within PRAXIS-Cell validated_runs/

| Anti-rule | Confirmed by validated_run | Empirical margin |
|---|---|---|
| #3 Raw Z vs B-score | `cell-002` | B-score recall 0.94 vs raw-Z 0.81 (+13 pp) |
| #4 Pearson alone | `cell-005` | 3-method consensus all flag high-coloc p=0.005; random control all flag null |
| #6 Linear IMC | `cell-009` | arcsinh 402× compression; cell-typing 100 % accuracy |
| #7 Cluster no anchor | `cell-010` | held-out MoA matching 5/5 with anchor; impossible without |
| #8 No hot-pixel filter | `cell-009` | 100 % of 1 498 planted hot pixels caught; per-cell intensity Pearson 0.99999 |
| #11 Cellpose default diameter | `cell-001`, `cell-real-biology-skimage`, `cell-real-biology-cellpose-vs-stardist` | Each used explicit per-image diameter (24 / 80 / 23.7 px); IoU 0.85+ each |

6 of 12 anti-rules have direct empirical confirmation from PRAXIS-Cell's validated_runs/. The other 6 are documented in their NEG- case bodies via reference-paper concrete numerics.
