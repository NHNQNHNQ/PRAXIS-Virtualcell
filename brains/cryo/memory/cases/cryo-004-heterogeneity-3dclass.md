---
case_id: cryo-004-heterogeneity-3dclass
schema_version: 1
sample_type: heterogeneous_complex
target_pdb: 5VN8
target_emdb: EMD-8645
molecular_weight_kda: 500
symmetry_group: C3
resolution_target: "3-4"
resolution_achieved_a: 3.3
detector_type: K3
detergent_or_lipid: nanodisc
method_choice: [relion_3d_class, cryosparc_3dva, cryodrgn, manifoldEM, focused_refine]
tools: [RELION 3D class, cryoSPARC 3DVA, cryoDRGN, ManifoldEM]
status: validated
provenance:
  source_type: literature
  doi: "10.1038/s41592-020-01049-4"
  citation: "Zhong ED, et al. CryoDRGN: reconstruction of heterogeneous cryo-EM structures using neural networks. Nat Methods 2021"
  extracted_at: 2026-04-29
  extraction_confidence: high
  unverified_details: ["Sample = HIV Env trimer / EF-Tu intermediates as method exemplars; specific PDB swappable"]
tags: [heterogeneity, 3D_classification, 3DVA, cryoDRGN, conformational, compositional, latent_space, multi_state]
---

# Heterogeneity：discrete 3D classification vs 连续 cryoDRGN

## Background
真实 sample 几乎都 heterogeneous：(1) compositional（partial complex）/(2) conformational（multiple states）/(3) compositional + conformational mix。**单一 refinement 强行 average → 模糊**。3D classification（discrete）+ cryoDRGN（continuous latent space）是两条路线。

## What I actually did
1. **Initial refinement**：first single-class 看 overall map quality；FSC 不达预期 + map 局部模糊 = heterogeneity 信号
2. **Discrete 3D classification (RELION)**：
   - K = 3-5 class，10-20 iterations
   - 看 class distribution + 每 class resolution + structural difference
   - 选 stable class 单独 refine
3. **3DVA (cryoSPARC)**：linear mode，3-5 dim，看 principal motion；通常显示 hinge / breathing motion
4. **cryoDRGN**：训练 VAE on particles → continuous latent space → sample latent points → reconstruct → animate
5. **Selection**：functional state of interest 的 particles → focused refinement
6. **典型 outcome**：50k particle dataset → 3 class，class 1 (60%) main state 3.0 Å, class 2 (25%) intermediate 3.5 Å, class 3 (15%) junk
7. **Verification**：同一 particle dataset 跑 3 个工具一致结论 → robust

## ★ 排除/不做的事
- **强 single-class refinement on heterogeneous sample**：FSC 假高，actual map 模糊
- **3D class K 太大**：K > 10 + 50k particle 每 class < 5k，resolution 不够
- **cryoDRGN single run**：随机 latent embedding，多 seed cross-check
- **Junk class 不丢弃**：保留 noise class 影响 main class refinement
- **Heterogeneity 解读为 single state**：multi-state 样本强行单一 model build = 错
- **Compositional vs conformational 不区分**：完全不同生物意义

## ★ 失败模式
- **K-means in latent space artifact**：cryoDRGN 输出 manifold 但没 ground-truth class label
- **Particle re-extraction bias**：3D class 后 re-extract 阶段 bias
- **Mixed compositional + conformational**：class 数被同时切两个 dimension，resolution 都不够
- **Slow mode under-sampled**：100 ms+ conformational change 在 cryoEM grid 不可能 capture
- **Continuous interpretation**：cryoDRGN movie 看着平滑 ≠ 真生物学，只是 manifold smoothness
- **Sample too few**：< 10k particle heterogeneity 分析 unreliable

## Lessons → seeds for rules
1. **Heterogeneity 必 explore**：FSC 不达预期 + map 局部模糊 = 信号
2. **Discrete 3D class + 3DVA + cryoDRGN 三方**：不同工具不同视角
3. **K 选择**：3-5 default；particle count 决定上限
4. **Stable class focused refinement** for high-res state
5. **Compositional vs conformational 区分**：mass spec / SEC 帮助
6. **Multi-seed 验证** continuous latent space
