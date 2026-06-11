---
case_id: cell-013-caiman-calcium-imaging
schema_version: 1
task: calcium_imaging_spike_inference
input_data: 2-photon time-lapse calcium imaging movie (GCaMP), 1000-100k frames at 10-30 Hz
image_modality: fluorescence
sample_dimension: time_lapse
cell_type: neural_tissue
assay_format: dish
channel_count: 1
dataset_accession: null
antibodies_rrid: []
software_versions:
  caiman: ">=1.9"
  suite2p: ">=0.14"
  mesoscale: ">=0.5"
tools: [CaImAn, Suite2p, EZcalcium, MIN1PIPE, NoRMCorre (motion), CNMF, MLspike]
key_paper_doi: 10.7554/eLife.38173
provenance:
  source_type: literature
  doi: 10.7554/eLife.38173
  citation: "Giovannucci A et al. CaImAn an open source tool for scalable calcium imaging data analysis. eLife. 2019;8:e38173."
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
tags: [calcium_imaging, two_photon, neural, gcamp, cnmf, deconvolution, motion_correction, caiman, suite2p]
status: validated
---

# CaImAn / Suite2p：钙成像 ROI 提取 + spike inference

## Background
2-photon calcium imaging（GCaMP6f/s/m, jGCaMP7/8）→ 神经元 fluorescence 时序 → 神经活动 proxy。**核心 pipeline**：(1) motion correction (rigid + non-rigid); (2) source extraction / ROI detection (CNMF = Constrained NMF); (3) ΔF/F trace; (4) spike deconvolution (OASIS / MLspike). CaImAn (Giovannucci 2019 eLife) 是开源 SOTA.

## What I actually did
1. **Image stack**：30 Hz × 30 min × 512x512 px, 1 channel (GCaMP6f); 50k frames
2. **Motion correction**：NoRMCorre (non-rigid via piecewise rigid) — **mandatory**, animal motion + brain pulsation
3. **Source extraction (CNMF)**:
   - Initialize: greedy ROI seed from local maxima
   - Decompose Y = AC + B (A = spatial footprints, C = temporal, B = background)
   - Iterate alternating updates of A, C
   - Component evaluation: SNR > 2.5, spatial footprint correlation > 0.85, temporal CNN classifier ≥ 0.5
4. **ΔF/F**：per-ROI baseline F0 from running 8th-percentile; ΔF/F = (F - F0) / F0
5. **Spike deconvolution**：OASIS auto-regressive AR(1) with constraint a ∈ [0, 1] for GCaMP6f
6. **QC**: Reject components with low SNR / high noise / non-cellular shape
7. **Output**: per-ROI ΔF/F trace, spike rate, footprint location

## ★ 排除/不做的事
- **Skip motion correction**：even mild drift breaks ROI extraction
- **Manual ROI without CNMF**：subjective + miss low-SNR cells
- **Raw fluorescence F (not ΔF/F)**：bleaching / illumination drift confound
- **Spike rate from raw ΔF/F (no deconvolution)**：ΔF/F has slow GCaMP decay (~1 s tau)
- **Single SNR threshold without CNN classifier**: passes vascular / bleed-through artifact
- **Default tau for indicator**: GCaMP6f tau ≠ jGCaMP8m; must set per-indicator
- **Across-session ROI reuse without re-registration**: tissue micro-motion misaligns

## ★ 失败模式
- **Photobleaching trend**：long imaging → baseline drift compounds with biology
- **Brain motion (heartbeat / breathing)**：sub-pixel residual after rigid; need non-rigid
- **Vasculature pulsation**：rhythmic artifact mimics neural activity
- **ROI overlap (overlapping dendrites)**：spatial footprints share variance → mixed traces
- **Z-axis drift**：cells move in/out of focus → false ΔF/F changes
- **Indicator saturation at high firing**：very active neurons fluorescence saturates → underestimate spike rate
- **Cross-session matching**：same neurons across days difficult; need ROI alignment

## Lessons → seeds for rules
1. **Motion correction (non-rigid) mandatory** — NoRMCorre / Suite2p ImageReg
2. **CNMF + CNN component classifier** dual filter
3. **ΔF/F with running baseline** (8th percentile or median)
4. **Spike deconvolution per-indicator tau** (OASIS / MLspike)
5. **Reject low-SNR components** (typical SNR > 2.5)
6. **Vasculature flag** — exclude Z-stack of large blood vessels
7. **Cross-session ROI re-registration** (CaImAn `register_multisession`)
