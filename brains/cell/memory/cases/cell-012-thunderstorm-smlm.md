---
case_id: cell-012-thunderstorm-smlm
schema_version: 1
task: super_resolution_localization
input_data: PALM / STORM / dSTORM single-molecule blinking time-series (10k-100k frames)
image_modality: fluorescence
sample_dimension: 2d_single_cell
cell_type: generic_cell_line
assay_format: dish
channel_count: 1
dataset_accession: null
antibodies_rrid: []
software_versions:
  thunderstorm: ">=1.3"
  fiji: ">=2.14"
  picasso: ">=0.7"
  smap: ">=2.0"
tools: [ThunderSTORM (Fiji), Picasso, SMAP, decode (DL), DeepSTORM, MATLAB SMAP]
key_paper_doi: 10.1093/bioinformatics/btu202
provenance:
  source_type: literature
  doi: 10.1093/bioinformatics/btu202
  citation: "Ovesný M et al. ThunderSTORM: a comprehensive ImageJ plug-in for PALM and STORM data analysis and super-resolution imaging. Bioinformatics. 2014;30(16):2389-2390."
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: ["ThunderSTORM is widely used baseline; modern alternatives (Picasso, decode) often outperform but have steeper learning curves."]
tags: [smlm, palm, storm, super_resolution, single_molecule, localization, thunderstorm, fiji]
status: validated
---

# ThunderSTORM：SMLM 单分子定位 super-resolution

## Background
SMLM (Single Molecule Localization Microscopy, e.g. PALM / STORM / dSTORM) 通过让 fluorophore 稀疏 blink，每帧 fit Gaussian PSF 拿到 sub-diffraction-limit 单分子坐标 → 累积 reconstructed image，分辨率 ~10-30 nm。**ThunderSTORM**（Ovesný 2014 Bioinformatics）是 Fiji plugin 标准 baseline；现代 DL alternatives (DeepSTORM / decode) 在 high-density 场景胜出。

## What I actually did
1. **Image acquisition**：10k-100k frames at 30-100 ms exposure, single channel, blinking buffer (β-mercaptoethylamine for dSTORM)
2. **Pre-process**：drift correction (cross-correlation between time chunks) — **mandatory**, even on Piezo stage
3. **Detection**：wavelet filter or LoG → local maxima above threshold
4. **Localization**：integrated Gaussian PSF fit, sub-pixel (precision typically 10-20 nm)
5. **Filter**：sigma_x / sigma_y ratio < 1.5 (rejects elongated PSFs from defocus); intensity > N photon threshold
6. **Drift correction**：post-fit cross-correlation (necessary for >5 min imaging)
7. **Render**：Gaussian rendering or histogram with pixel size = localization_precision / 4
8. **Validation**: NPC nucleoporin Nup96 — known 8-fold symmetry should be visible (32-fold in TM domain) at < 20 nm precision

## ★ 排除/不做的事
- **Forget drift correction**：>5 min imaging without drift = blurred image
- **Use widefield reconstruction directly**：SMLM ≠ deconvolution; require single-molecule fit
- **Per-frame detection threshold static**：should adapt to background drift
- **Render at pixel size larger than localization precision**：waste of resolution
- **High-density activation without DL**：>5 emitters per PSF area → ThunderSTORM fails; use decode / DeepSTORM
- **Without uncertainty filter**：keeping low-precision localizations = blurry final image

## ★ 失败模式
- **Buffer degradation**：blinking buffer ages over hours → blink rate changes
- **Fluorophore underactivation**：too few blinks → sparse final image
- **Sample drift**：mechanical / thermal → blur even with correction
- **Multi-emitter overlap**：dense activation → mis-fit
- **Bleaching saturation**：late frames have less signal
- **PSF aberration**：astigmatism / coma → sigma filter rejects but loses good loc
- **Out-of-focus emitter**：sigma filter helps but not perfect

## Lessons → seeds for rules
1. **Drift correction mandatory** (cross-correlation between chunks)
2. **Sigma filter** for sigma_x/sigma_y ratio (1.0-1.5)
3. **Photon count filter** (typical > 500 photons)
4. **Render pixel ≤ localization precision / 4**
5. **Density check**: high-density → DL methods; low-density → ThunderSTORM
6. **Validation by known symmetry** (NPC Nup96 8-fold; clathrin coat triskelion)
7. **Buffer age tracking** for multi-day acquisitions
