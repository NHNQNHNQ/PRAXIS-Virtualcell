---
case_id: NEG-NO-DRIFT-SMLM
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 9
task: super_resolution_localization
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: generic_cell_line
assay_format: dish
channel_count: 1
dataset_accession: null
antibodies_rrid: []
software_versions:
  thunderstorm: ">=1.3"
tools: [SMLM acquisition, no drift correction, no fiducial markers, no cross-correlation]
key_paper_doi: 10.1093/bioinformatics/btu202
provenance:
  source_type: literature
  doi: 10.1093/bioinformatics/btu202
  citation: "Ovesný M et al. ThunderSTORM: a comprehensive ImageJ plug-in for PALM and STORM data analysis and super-resolution imaging. Bioinformatics. 2014;30(16):2389-2390. (defines drift correction as mandatory for >5min imaging)"
  extracted_at: 2026-05-02
  extraction_confidence: high
  unverified_details: []
tags: [anti_pattern, no_drift_correction, smlm, palm, storm, no_cross_correlation]
causal_tag: causal
---

# NEG-NO-DRIFT-SMLM — SMLM acquisition (>5 min) without drift correction

## What this NEG- case records
**Anti-pattern**: acquiring 10 000-100 000 frames of PALM / STORM / dSTORM single-molecule blinking data over 5-30 min total acquisition time without applying drift correction (cross-correlation between time chunks, or fiducial-marker tracking). Resulting reconstructed image has localizations smeared across 50-200 nm of stage drift, destroying super-resolution.

## Where the failure mode was published
Ovesný 2014 ThunderSTORM Bioinformatics — and every modern SMLM methods paper — flags drift correction as MANDATORY for any acquisition > 5 min. Even Piezo-stabilized stages typically drift 50-200 nm over a 30-min acquisition due to thermal expansion and mechanical creep.

## Mechanism — why it fails
- SMLM's whole point: localize single emitters to ~10-20 nm precision per frame.
- Stage drifts ~5-10 nm/min (Piezo-stabilized) to ~20-50 nm/min (regular stages) due to thermal + mechanical effects.
- Over 30-min acquisition, drift sums to 150-1500 nm.
- Without drift correction, the reconstructed super-resolved image has localizations smeared across this drift envelope → resolution drops from 10-20 nm to 100-1500 nm, defeating the purpose of SMLM.

## Concrete numerics (from PRAXIS-Cell cell-012 validated_run)
- Synthetic 10-frame SMLM @ 30 Hz, 80 sparse emitters, SNR 25, NO planted drift
- LoG detection + 2D Gaussian fit + sigma + photon filters → **RMS 10 nm** localization, recall 87 %
- Same pipeline with planted 1-pixel-per-frame drift over 10 frames (= 100 nm total): RMS would degrade from 10 nm to ~50 nm
- Real 30-min acquisition without drift correction: RMS would degrade from 10 nm to 200-1000 nm

## ★ Reviewer hard-stop
Any SMLM design plan with acquisition time > 5 min that does not include drift correction (cross-correlation between time chunks, OR fiducial-marker tracking) must be vetoed. Required: drift correction step before render reconstruction.

## Maps to anti-rule
**anti-rule #9**: SMLM acquisition > 5 min without drift correction is forbidden. Required: cross-correlation drift correction or fiducial-marker tracking.

## Anti-retrieval keywords
no drift correction, smlm, palm, storm, no cross correlation, no fiducial, long acquisition no drift, raw localization
