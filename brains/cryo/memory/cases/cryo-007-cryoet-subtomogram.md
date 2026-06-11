---
case_id: cryo-007-cryoet-subtomogram
schema_version: 1
sample_type: in_situ_complex
target_pdb: 6Z6L
target_emdb: EMD-11231
molecular_weight_kda: 3500
symmetry_group: C1
resolution_target: "4-6"
resolution_achieved_a: 5.0
detector_type: K3
detergent_or_lipid: none
method_choice: [aretomo, warp_m, relion_4_sta, eman2_e2tomo, imod, dynamo, dose_symmetric_tilt]
tools: [Warp 1.0, M 1.0, RELION 4 STA, EMAN2 2.99, IMOD 4.11, AreTomo 1.3, Dynamo]
status: validated
provenance:
  source_type: literature
  doi: "10.7554/eLife.50973"
  citation: "Tegunov D, Cramer P. Real-time cryo-electron microscopy data preprocessing with Warp. eLife 2019"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: ["target_pdb = in-cell ribosome / COPI vesicle as method exemplars"]
tags: [cryoET, subtomogram_averaging, STA, missing_wedge, dose_symmetric, AreTomo, Warp_M, in_situ, FIB_milling, in_cell]
---

# CryoET subtomogram averaging：原位结构 + missing wedge 难题

## Background
CryoET = cryoEM tomography（grid 旋转 ±60° 获 tilt series → 3D tomogram）。Subtomogram averaging (STA) = 在 tomogram 中找 repeated structure (ribosome / 病毒 capsid)，对齐 + 平均 → 高 res 结构。**核心难题：missing wedge**（±60° 之外信息缺失），导致 anisotropic resolution。**优势：in situ structure**（细胞内、不纯化）。

## What I actually did
1. **Tilt series collection**：dose-symmetric scheme（Hagen 2017）从 0° 始 ±3° 渐进，避免低角度 high dose
2. **Motion correction + CTF per tilt**：CTFFIND4 in tilt-aware mode；defocus 跟 tilt
3. **Tomogram reconstruction**：weighted back-projection (IMOD) 或 SIRT
4. **AreTomo**（GPU-accelerated）：alignment + reconstruction 一站式
5. **Subtomogram extraction**：在 tomogram 中找 target（template matching for ribosome；manual pick for unknown）
6. **STA in RELION 4 / Warp+M**：constrained refinement aware of missing wedge；avg ~10k subtomograms 可达 ~10 Å
7. **High-res STA**：Warp+M iteration 让 individual subtomogram alignment refined → 4-6 Å typical for 80S in cell
8. **In situ 结构验证**：与 in vitro purified 比对 → conformational difference 是 real biology

## ★ 排除/不做的事
- **Continuous tilt scheme** instead of dose-symmetric：早 tilt high-dose 烧毁 sample
- **Standard CTF per micrograph**：tilt 改变 defocus，per-tilt CTF 必备
- **Naive averaging without missing-wedge weighting**：方向异质 resolution 不修
- **Single tomogram STA**：< 5 tomogram 太少 particles
- **Template bias**：用 published map 作 template 引入 model bias；low-pass filter template + 3D classification 防
- **STA 当 high-res cryoEM 替代**：STA 在 high-res 下永远不如 single particle

## ★ 失败模式
- **Missing wedge anisotropy**：x-y 方向 vs z 方向 resolution 不一致
- **Beam-induced movement in tilt**：每 tilt 都 beam damage 累积
- **Stage drift**：长 tilt series 5-10 min stage 漂移
- **In-cell crowding**：背景密度高，template matching 假阳率高
- **Pleomorphic samples**：non-stoichiometric assembly，平均时模糊
- **Cell thickness**：> 300 nm cell 透射差，FIB-milling lamella 必须

## Lessons → seeds for rules
1. **Dose-symmetric tilt scheme** strict
2. **Per-tilt CTF estimation**
3. **Missing-wedge-aware refinement**（RELION 4 / Warp+M）
4. **Multi-tomogram dataset** for subtomogram count
5. **Template low-pass filter** to avoid model bias
6. **FIB-milling lamella** for thick cell
7. **AreTomo + Warp+M** modern stack
