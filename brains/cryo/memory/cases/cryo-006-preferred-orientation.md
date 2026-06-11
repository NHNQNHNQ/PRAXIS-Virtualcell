---
case_id: cryo-006-preferred-orientation
schema_version: 1
sample_type: any
target_pdb: 6VSB
target_emdb: EMD-21375
molecular_weight_kda: 480
symmetry_group: C3
resolution_target: "3-4"
resolution_achieved_a: 3.5
detector_type: K3
detergent_or_lipid: none
method_choice: [cryoef, three_d_fsc, cryosparc_orient_diag, tilt_collection, surfactant]
tools: [cryoSPARC v4 orientation diagnostics, cryoEF, RELION, 3DFSC]
status: validated
provenance:
  source_type: literature
  doi: "10.1038/nmeth.4347"
  citation: "Tan YZ, et al. Addressing preferred specimen orientation in single-particle cryo-EM through tilting. Nat Methods 2017"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: ["target = HA trimer (4FNK) and SARS-CoV-2 spike (6VSB) used as method exemplars"]
tags: [preferred_orientation, cryoEF, 3DFSC, angular_distribution, tilt_collection, surfactant, graphene_oxide, GraFix, mitigation]
---

# Preferred orientation：cryoEM 最常见的"伪高分辨率"陷阱

## Background
Preferred orientation = 粒子在 grid 上倾向某一方向（air-water interface 偏好），导致 angular distribution 不均匀 → 3D refinement 在 missing direction 模糊。**FSC 看似 3.0 Å 但 map 部分区域实际 5+ Å**——是 cryoEM 最常被忽视的 systematic error。

## What I actually did
1. **Diagnostic 1**：3D refinement 后查 angular distribution histogram (cryoSPARC plot_3D_refinement_histograms)；理想 isotropic（球面均匀）；clustered = bad
2. **Diagnostic 2**：cryoEF 计算 Efficiency Factor (0.5-1.0)；< 0.7 是 bad；< 0.5 是 severe
3. **Diagnostic 3**：3DFSC 算 directional FSC，看 worst direction vs best 比例
4. **Local resolution map**：map 的 worst region 通常对 missing direction
5. **Mitigation strategy**:
   - **Tilt grid collection**: 30° / 60° tilt acquisition 强制 fill missing direction
   - **Surfactant additives**: detergent (DDM, Octyl-glucoside) 改 air-water interface
   - **Graphene oxide / chameleon grid**: 改 surface chemistry
   - **Crosslinker**: GraFix（gradient + glutaraldehyde）固定 conformation
   - **Different grid type**: UltrAuFoil vs Quantifoil
6. **Re-collection 决策**：单 dataset 已 severe preferred → 改 prep 重新 collect 比 software fix 更有效
7. **Post-hoc rescue**：tilt + non-tilt particle merge → 改善但不彻底

## ★ 排除/不做的事
- **不查 angular distribution** post-refinement：missed preferred orientation = 错误高分辨率 claim
- **强 software 修 severe preferred**：用 0° tilt only data 处理 60° tilted reconstruction = 不可能
- **不报告 cryoEF / 3DFSC**：发表/公开 map 没这些 metric = 数据 quality 不透明
- **Tilt collection 不准 stage**：tilt acquisition 需 stage refinement，不准的 tilt 不修问题
- **Crosslink 太重**：GraFix 过度 crosslink 锁住 conformation 但失去 native state

## ★ 失败模式
- **Air-water interface denaturation**：preferred 倾向常因 protein 在 air 表面 partially denature
- **Detergent-induced opposite preferred**：换 detergent 反而把 preferred 翻向另一方向
- **Tilt 增加 ice movement**：tilt collection 引入额外 beam-induced motion
- **Mixed orientation populations**：part of dataset preferred， part isotropic → 难分类
- **Edge effect on grid**：边缘 vs 中心粒子 orientation 不同
- **HA trimer / spike trimer 知名 preferred case**：top-down view 主导

## Lessons → seeds for rules
1. **Angular distribution 必查 post-refinement**：cryoSPARC histogram + cryoEF + 3DFSC 三方
2. **cryoEF < 0.7 红旗**：考虑 mitigation
3. **Tilt collection** for severe preferred (not pure software fix)
4. **Surfactant / grid surface** 第一线 mitigation
5. **Local resolution-aware interpretation**：worst direction 对应 worst region
6. **Re-collection > post-processing 修正** for severe case
