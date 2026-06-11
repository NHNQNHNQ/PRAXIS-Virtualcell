---
case_id: NEG-NO-MOTION-CALCIUM
schema_version: 1
case_polarity: negative
status: anti_pattern
maps_to_anti_rule: 10
task: calcium_imaging_spike_inference
image_modality: fluorescence
sample_dimension: time_lapse
cell_type: neural_tissue
assay_format: dish
channel_count: 1
dataset_accession: null
antibodies_rrid: []
software_versions:
  caiman: ">=1.9"
tools: [no motion correction, no NoRMCorre, no rigid alignment, raw 2-photon stack]
key_paper_doi: 10.7554/eLife.38173
provenance:
  source_type: literature
  doi: 10.7554/eLife.38173
  citation: "Giovannucci A et al. CaImAn an open source tool for scalable calcium imaging data analysis. eLife. 2019;8:e38173. (defines motion correction (NoRMCorre) as mandatory upstream step)"
  extracted_at: 2026-05-02
  extraction_confidence: high
  unverified_details: []
tags: [anti_pattern, no_motion_correction, no_normcorre, calcium_imaging, two_photon, neural]
causal_tag: causal
---

# NEG-NO-MOTION-CALCIUM — 2P calcium imaging without motion correction

## What this NEG- case records
**Anti-pattern**: feeding raw 2-photon GCaMP imaging movie (10k-100k frames at 30 Hz) directly into CNMF source extraction or spike inference without first applying NoRMCorre (or Suite2p ImageReg) non-rigid motion correction. Brain pulsation (heart rate ~3-5 Hz) + breathing (~0.5-1 Hz) + animal motion produce sub-pixel residual drift that breaks ROI extraction.

## Where the failure mode was published
Giovannucci 2019 CaImAn eLife — the canonical 2P calcium-imaging pipeline paper — flags motion correction as MANDATORY upstream of CNMF. Even head-fixed mice + Piezo stage have 1-3 µm pulsation amplitude in the imaging plane.

## Mechanism — why it fails
- CNMF source extraction assumes per-pixel time-series belongs to a STATIC source.
- Brain pulsation (~3-5 Hz heart rate) shifts the imaging plane by 0.5-2 µm at the pulse rate.
- Without motion correction, every pixel's trace is a mixture of multiple cells' signals, modulated by the pulse-rate shift.
- CNMF then either: (a) fails to extract clean ROIs (ROI footprints blur to ovals matching the motion direction); (b) extracts a "pulse-modulated artifact" component that explains 20-40 % of variance with no biology meaning.
- Spike deconvolution on contaminated trace produces false spikes at the pulse rate.

## Concrete numerics (from PRAXIS-Cell cell-013 validated_run)
- Synthetic GCaMP6f trace, 60 s @ 30 Hz, 95 true Poisson spikes, NO planted motion
- AR(1) inverse + ΔF/F + scipy peak-detect: recall 0.69, precision **1.0**, count recovery 0.69
- Same pipeline with planted 5 % motion (typical 2P brain-pulsation amplitude): expected precision drops to ~0.5 (motion-aliased false spikes), recall drops to ~0.4

## ★ Reviewer hard-stop
Any 2P calcium-imaging design plan whose pipeline_steps list does not include a motion-correction step (NoRMCorre, Suite2p ImageReg, or rigid+non-rigid stack alignment) before CNMF / source-extraction must be vetoed. Required: motion correction first.

## Maps to anti-rule
**anti-rule #10**: 2P calcium imaging without motion correction is forbidden. Required: NoRMCorre or Suite2p ImageReg upstream of CNMF.

## Anti-retrieval keywords
no motion correction, no normcorre, calcium imaging, raw 2-photon, no rigid alignment, no Suite2p, brain pulsation ignore
