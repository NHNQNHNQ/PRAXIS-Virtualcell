---
case_id: NEG-NO-GAP-CLOSING
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 12
task: live_cell_tracking_lineage
image_modality: fluorescence
sample_dimension: time_lapse
cell_type: generic_cell_line
assay_format: dish
channel_count: 2
dataset_accession: null
antibodies_rrid: []
software_versions:
  trackmate: ">=7.0"
  trackpy: ">=0.6"
tools: [LAP frame-to-frame only, no gap closing, no occlusion handling]
key_paper_doi: 10.1038/s41592-022-01507-1
provenance:
  source_type: literature
  doi: 10.1038/s41592-022-01507-1
  citation: "Ershov D et al. TrackMate 7: integrating state-of-the-art segmentation algorithms into tracking pipelines. Nat Methods. 2022;19(7):829-832. (Jaqaman 2008 LAP two-step algorithm for tracking + gap closing)"
  extracted_at: 2026-05-02
  extraction_confidence: high
  unverified_details: []
tags: [anti_pattern, no_gap_closing, no_occlusion, lap_only, live_cell_tracking]
causal_tag: causal
---

# NEG-NO-GAP-CLOSING — LAP linker without gap closing on live-cell tracking

## What this NEG- case records
**Anti-pattern**: tracking live cells frame-to-frame with `scipy.optimize.linear_sum_assignment` (or TrackMate's first-pass LAP) but treating any 1-frame missed detection as a track end. No gap-closing pass that allows tracks to skip 1-2 frames and rejoin.

## Where the failure mode was published
Jaqaman 2008 (cited in Ershov 2022 TrackMate 7 Nat Methods) — the canonical LAP tracker — defines a TWO-step optimization: (1) frame-to-frame LAP, (2) segment-to-segment LAP for gap closing + division. Implementations that omit step 2 break tracks at every brief occlusion or missed detection.

## Mechanism — why it fails
- Real live-cell movies have ~1-2 % per-frame "missed detection" rate (focus drift, photo-bleaching dim cells, brief occlusion behind another cell).
- Without gap closing, every missed detection ends one track and starts another.
- Over 60 frames, ~50 % of true tracks get fragmented into 2+ pieces.
- Mitosis detection (which depends on a parent track ending + 2 daughter tracks starting nearby) becomes ambiguous because every gap looks like a mitosis candidate.
- Lineage tree quality drops sharply — fragments outnumber true mitoses.

## Concrete numerics (from PRAXIS-Cell cell-004 validated_run)
- Synthetic 60-frame movie, 30 cells + 8 divisions + 4 deaths + 3 planted occlusions
- With gap-closing (1-frame gap, threshold 35 px): track recall 0.52, mitosis recall 0.50, **gap-close rate 0.67** (2/3 occlusions survive)
- Without gap-closing: gap-close rate would be 0/3 = 0; track recall would drop to ~0.30 (each occlusion fragments a track)
- Real TrackMate 7 (Jaqaman two-step LAP) achieves ~0.85 track recall on similar data — the gap-closing pass is the difference

## ★ Reviewer hard-stop
Any live-cell tracking design plan that uses LAP frame-to-frame only (no gap closing, no segment-to-segment second pass) on movies > 20 frames must be vetoed. Required: Jaqaman two-step LAP, OR TrackMate, OR btrack with gap-closing parameter set.

## Maps to anti-rule
**anti-rule #12**: LAP frame-to-frame tracking without gap closing on live-cell movies > 20 frames is forbidden. Required: gap-closing pass (Jaqaman two-step or equivalent).

## Anti-retrieval keywords
no gap closing, lap frame to frame only, no occlusion handling, no segment to segment, no jaqaman two-step
