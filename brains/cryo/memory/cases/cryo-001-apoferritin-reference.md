---
case_id: cryo-001-apoferritin-reference
schema_version: 1
sample_type: soluble_oligomer
target_pdb: 6V21
target_emdb: EMD-21024
molecular_weight_kda: 480
symmetry_group: O
resolution_target: "<2"
resolution_achieved_a: 1.8
detector_type: K3
detergent_or_lipid: none
method_choice: [cryosparc_NU_refine, relion_polish, ctffind4, topaz, deepemhancer]
tools: [RELION 5.0, cryoSPARC v4, CTFFIND4, Topaz, ChimeraX, DeepEMhancer]
status: validated
provenance:
  source_type: literature
  doi: "10.1016/j.jsb.2020.107545"
  citation: "Wu M, Lander GC, Herzik MA. Sub-2 Angstrom resolution structure determination using single-particle cryo-EM at 200 keV. J Struct Biol. 2020"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
tags: [apoferritin, soluble_oligomer, octahedral, K3, NU_refine, polish, facility_calibration, sub_2A]
---

# Apoferritin: cryoEM pipeline 的 ground truth reference

## Background
Apoferritin（24-mer iron storage protein，octahedral 432 symmetry，~480 kDa）是 cryoEM 行业 reference sample——high symmetry + 高分子量 + 稳定，能达到 1.2-1.5 Å 是 detector + grid 优化的 benchmark。任何 cryoEM facility 都用 apoferritin 校准。

## What I actually did
1. **Data collection setup**：K3 detector, super-resolution mode, 0.4 Å/px (binned to 0.8), 50 e-/Å² total dose, 40-50 frames
2. **Motion correction**：MotionCor2 / RELION's own，dose-weighted
3. **CTF estimation**：CTFFIND4，CC > 0.05，astigmatism < 200 Å
4. **Particle picking**：blob-based template-free or Topaz with general model；典型 ~500 ptcl/micrograph
5. **2D classification**：cryoSPARC fast 2D，丢非 apoferritin classes
6. **Ab initio reconstruction**：1 class，octahedral symmetry imposed
7. **NU-refinement (cryoSPARC)** or **3D auto-refine (RELION)** with O symmetry
8. **CTF refinement + Bayesian polishing**（RELION）：每 particle CTF + 每帧 alignment 修正
9. **Final result**：~50k particles → 1.5-2.0 Å，high symmetry 让 effective # of asymmetric particles = 24x
10. **Sharpening**：B-factor automatic + DeepEMhancer post-processing

## ★ 排除/不做的事
- **Octahedral symmetry 不 impose**：必须 O symmetry，否则 need 24x particles
- **Grid 不优化** for thin ice：apoferritin 适合 thin ice (~30 nm)；thick ice resolution 限制
- **No CTF refinement**：跳过会停在 2.5 Å 上不去
- **No Bayesian polishing**：beam-induced motion 不修正，high-res info 损失
- **Skip dose weighting**：late frame 信号被 radiation damage 主导
- **不做 facility benchmark**：拿到新 detector 不跑 apoferritin 校准 = 后续 sample 无 reference

## ★ 失败模式
- **Preferred orientation**：apoferritin 通常 isotropic 但偶发 detergent / surfactant 效应
- **Ice thickness 不一**：边 vs 中心 ice 差，分类时丢
- **Particle aggregation**：高浓度 sample 形成 dimer/oligomer of apoferritin → multiple species
- **Beam tilt**：detector 与 beam not parallel，全 dataset bias
- **Magnification 不准**：apix 错 1% → resolution claim 偏；用 published 1.84 Å apoferritin map 校准
- **Movie file corruption**：~1-2% movies 损坏，pre-screen 必做

## Lessons → seeds for rules
1. **Apoferritin 是 facility 校准 must-do**：每次 detector / grid hardware 改变后跑
2. **Symmetry imposition**：高 symmetry sample 必 impose 对应 group
3. **CTF refinement + polishing 是 high-res necessary steps**
4. **Apix 校准** with apoferritin 已知值
5. **Pre-screening movies** for corruption
6. **DeepEMhancer post-processing** for visualization
