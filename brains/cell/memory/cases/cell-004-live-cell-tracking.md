---
case_id: cell-004-live-cell-tracking
schema_version: 1
task: live_cell_tracking_lineage
input_data: time-lapse fluorescence (mitotic event detection)
image_modality: fluorescence
sample_dimension: time_lapse
cell_type: generic_cell_line
assay_format: dish
channel_count: 3
dataset_accession: null
antibodies_rrid: []
software_versions:
  trackmate: ">=7.0"
  trackpy: ">=0.6"
  btrack: ">=0.6"
  cellpose: ">=3.0"
tools: [Trackmate (Fiji), Cellpose + linker, TrackPy, Btrack, deepBlink, MaMuT (lineage)]
key_paper_doi: 10.1038/s41592-022-01507-1
provenance:
  source_type: literature
  doi: 10.1038/s41592-022-01507-1
  citation: "Ershov D et al. TrackMate 7: integrating state-of-the-art segmentation algorithms into tracking pipelines. Nat Methods. 2022;19(7):829-832."
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
tags: [live_cell, tracking, lineage, mitosis, lap_tracker, gap_closing, time_lapse, photobleaching]
status: validated
---

# Live cell tracking + lineage tree：cell cycle 动态分析

## Background
Live cell imaging（h-day 时长，秒-分钟 间隔）→ track 单 cell over time → mitotic event + apoptosis + migration。**lineage tree** = 把所有 daughter cell 关联到 founder cell。**核心难度**：(1) cell death / mitosis 让 track 中断；(2) overlap / occlusion；(3) intensity variation due to focus drift。

## What I actually did
1. **Image stack**：30 min interval × 24h, 3 channel (DIC + nuclear marker + apoptosis sensor)
2. **Per-frame segmentation**：Cellpose nuclear mask
3. **Linking frame to frame**：TrackMate 的 LAP (Linear Assignment Problem) tracker
4. **Mitotic event detection**：daughter mask 出现 + parent disappear 同帧 → mitosis；distance threshold for daughter pair
5. **Apoptosis detection**：apoptosis sensor signal rise + cell shrink
6. **Track quality**：fragment length / number of gaps / linking confidence
7. **Lineage tree (MaMuT)**：parent-daughter linkage 形成 tree；time × lineage 2D plot
8. **Cell cycle metric**：interphase duration distribution + division asymmetry

## ★ 排除/不做的事
- **Per-frame segmentation independent**：linking 用 nuclear segmentation 才 stable
- **No gap closing**：cell occlude 1-2 frame，没 gap closing 让 track break
- **Mitosis detection by intensity alone**：need spatial proximity + size halving
- **Manual track for > 100 cells**：DL tracker 必备
- **Single channel tracking**：DIC + fluorescence dual channel 准
- **Focus drift uncompensated**：z-stack tracking 必备 z-correction

## ★ 失败模式
- **Cell crowding**：dense cell linking 错位
- **Photobleaching**：long imaging marker fading → tracking 弱
- **Phototoxicity**：illumination 杀 cell - 改变 biology
- **Out-of-frame / out-of-focus**：cell migrate out 或 out of focus
- **Heterogeneous intensity**：cell-to-cell brightness 差让 linker 偏
- **Mitosis vs cell death confusion**：sometimes 形态相似

## Lessons → seeds for rules
1. **DL segmentation + LAP linking**
2. **Gap closing** for short occlusion
3. **Mitosis = spatial proximity + size halving + time near**
4. **Multi-channel tracking** (DIC + fluorescence)
5. **Focus drift correction**
6. **Photobleaching correction** for long imaging
7. **Phototoxicity awareness**：minimize laser power
