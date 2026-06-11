---
case_id: cryo-010-focused-refinement
schema_version: 1
sample_type: large_complex
target_pdb: 6CP3
target_emdb: EMD-7544
molecular_weight_kda: 600
symmetry_group: C1
resolution_target: "3-4"
resolution_achieved_a: 3.2
detector_type: K3
detergent_or_lipid: none
method_choice: [relion_focused_refine, cryosparc_local_refine, phenix_mask_create, chimerax_volume, signal_subtract]
tools: [RELION 5 focused refinement, cryoSPARC v4 local refinement, Phenix 1.20, ChimeraX 1.7]
status: validated
provenance:
  source_type: literature
  doi: "10.1016/j.jsb.2018.08.007"
  citation: "Bai XC, et al. Sampling the conformational space of the catalytic subunit of human gamma-secretase. Methods (review of focused refinement)"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: ["target_pdb = ATP synthase / virus capsid asymmetric reconstruction as method exemplars"]
tags: [focused_refinement, signal_subtract, soft_mask, local_resolution, composite_map, mask_creation, ROI, large_complex]
---

# Focused refinement：在大复合物里"放大"特定区段

## Background
Full complex refinement 平均所有 inter-domain motion → 局部 resolution 受限。**Focused refinement** = mask 出感兴趣区段 → 只 align particles 围绕该区 → 该区 resolution 提升 0.3-1.0 Å。配合 multibody 是大复合物处理 standard。

## What I actually did
1. **Identify region of interest**：local resolution map 显示该区比 overall 差 0.5+ Å
2. **Mask creation**：用 ChimeraX / RELION mask_create 围绕 ROI；soft edge ~6 voxel
3. **Focused refinement (RELION)** with mask + signal subtraction
4. **Signal subtraction**：减掉 ROI 外的 signal，只 refine ROI；典型应用对 small subunit / antibody / ligand 区
5. **Local refinement (cryoSPARC)**：相同 idea，pose updates 只看 mask 区
6. **Composite map**：focused refined ROI 与 full map combine（局部高 res + 全局上下文）
7. **Validation**：FSC at masked region > FSC at full map；ROI Q-score 提升

## ★ 排除/不做的事
- **Mask 太小**：< ROI size，会切断 contacts
- **Mask 太严 (no soft edge)**：sharp edge artifact in FSC
- **Multiple ROI 同时 focused**：每次一个 region；并行做多 mask
- **Signal subtraction 不需要时强用**：small ROI < 1/3 complex 才显著获益
- **Composite map 不告诉用户合成的部分**：发表时必须说明 final map 是哪几部分 stitched

## ★ 失败模式
- **Mask 漏 inter-domain contact**：focused 只看一边，contact 不正确
- **Particle count 不足 for focused**：focused refine 等于 only ROI signal，需 high particle count
- **ROI flexible 程度高**：focused refine 也没用，只能 cryoDRGN-like 处理
- **Composite map 不一致**：不同 mask 的 focused refined region 间 boundary discontinuity
- **Over-fitting focused**：tightly masked region FSC 假高，用 conservative mask 避免

## Lessons → seeds for rules
1. **Local resolution map first** 决定 ROI
2. **Soft edge mask** (~6 voxel) 强制
3. **Signal subtraction** for small ROI in big complex
4. **Multi-ROI separately**，不并发
5. **Composite map 必文档** which region from which refinement
6. **Particle count check**：focused need same population as full
