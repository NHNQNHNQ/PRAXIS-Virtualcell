---
case_id: cryo-002-membrane-protein-gpcr
schema_version: 1
sample_type: membrane_protein_complex
target_pdb: 6CMO
target_emdb: EMD-7460
molecular_weight_kda: 150
symmetry_group: C1
resolution_target: "3-4"
resolution_achieved_a: 3.5
detector_type: K3
detergent_or_lipid: DDM_CHS
method_choice: [relion_5, cryosparc_v4, ctffind4, topaz, multibody_refine, isolde, modelangelo, phenix]
tools: [RELION 5, cryoSPARC v4, Phenix 1.20, Coot 0.9, ChimeraX 1.6, ISOLDE, ModelAngelo 1.0]
status: validated
provenance:
  source_type: literature
  doi: "10.1038/s41586-018-0235-7"
  citation: "Koehl A, et al. Structure of the mu-opioid receptor-Gi protein complex. Nature 2018"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: []
tags: [GPCR, membrane_protein, mu_opioid_receptor, Gi_protein, scFv16, multibody, ISOLDE, DDM_CHS]
---

# GPCR-G protein 复合物：cryoEM 的"中分子量难题"

## Background
GPCR-G protein 复合物 (~150 kDa) 是 membrane protein cryoEM 主流 case。GPCR alone 太小 (~40 kDa)，需 fusion partner（BRIL, mini-Gαs/i fusion, scFv16 stabilizer）增大。**~150 kDa 在 cryoEM "size 死亡区"边缘**——需高质量 detector + 充分 particle count。

## What I actually did
1. **Sample stabilization**：MOR + heterotrimeric Gi 复合物 + scFv16（结合 Gαi-Gβ interface 稳定）+ DDM/CHS detergent
2. **Grid prep**：UltrAuFoil R1.2/1.3，氟胶 graphene oxide support 减 preferred orientation
3. **Data collection**：K3 BioQuantum, 105k× mag, 0.83 Å/px, 50 e-/Å², ~10k movies
4. **Pipeline**：MotionCor2 → CTFFIND4 → Topaz pick → 2D classify → 3D ab initio + heterogeneity → multi-class refinement
5. **Heterogeneity 关键**：3D classification 找 active vs intermediate vs inactive states；通常 60% particles 在期望 active state
6. **Multibody refinement**（RELION）：受体 7TM + Gαi + Gβγ 三个 rigid bodies independent refine 解决 inter-body flex
7. **Final resolution**：~3.0-3.5 Å typical for medium GPCR；ligand binding site 区域 better (~2.8 Å)
8. **Model building**：ISOLDE molecular dynamics flexible fit + Coot manual + Phenix real-space refine

## ★ 排除/不做的事
- **No fusion partner stabilizer**：单 GPCR alone 太小+柔性，cryoEM 失败率高；scFv16 / mini-G 是 standard
- **DDM only**：DDM micelle 大遮挡 receptor；nanodisc / amphipol 替代 sometimes 更好
- **不做 multibody refinement**：inter-body motion 限 resolution；rigid full-particle refinement 模糊 binding site
- **3D classify 太多 class**：> 5 class 每 class 太少 particle，分辨率低；2-3 class 通常足
- **Missing wedge in tilt**：preferred orientation 严重时考虑 grid tilt collection（30°/60°）
- **Ligand 模型 model building 时 over-fit**：低 resolution 区强 fit 给虚假 atoms

## ★ 失败模式
- **Detergent micelle 干扰**：micelle 大 + 强 contrast 干扰 alignment
- **Activation state heterogeneity**：sample 含混合 state，3D class 才看出
- **Preferred orientation**：GPCR-G complex 常 preferred top-down view，需 grid tilt or surfactant
- **Beam-induced movement in TM region**：lipid 部分 movement 不容易 polish 修
- **Detergent/lipid density 误读为 protein**：building 时易混
- **Allosteric ligand 在低 res 区**：ligand pose 模糊

## Lessons → seeds for rules
1. **Fusion partner / antibody stabilizer** for small GPCR
2. **Multibody refinement** for multi-domain flex
3. **3D heterogeneity 必查**：active/inactive state 混合
4. **ISOLDE > pure Coot** for GPCR model building（MD flex fit 更适合柔性 region）
5. **Detergent 选**：DDM safe；nanodisc/amphipol/SMA 可降 background
6. **Tilt collection** for preferred orientation rescue
