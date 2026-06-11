---
case_id: NEG-09-ensemble-too-short-md
schema_version: 1
docking_type: ensemble_protein_ligand
target_pdb: anti-pattern reference (HIV-1 protease)
target_class: protease
ligand_type: small_mol
system_specifics:
  ligand_drug_likeness: drug_like
  interface_type: transient
tools: [GROMACS, AutoDock Vina 1.2.5, gmx_cluster]
flexibility_required: ensemble
validation_benchmark: none
key_paper_doi: 10.1021/ci2002704
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-09-ensemble-md-too-short
tags: [NEG, anti-pattern, ensemble, MD-too-short, sampling-insufficient]
---

# NEG-09: Ensemble docking with MD < 100 ns trajectory (anti-rule-09)

## Background (anti-pattern)
团队跑 30 ns apo MD on HIV protease + cluster top 5 representatives + Vina dock library on each conformer。
**MD 30 ns 不够 — flap 仍 around starting structure，cluster representatives 几乎 identical**。
Best-of-N enrichment 与 single rigid docking 同 (~0% improvement)。湿实验 selectivity panel 失败：
ensemble 没采到 flap-open conformation, 漏掉 60% true binders。

## ★ 排除/不做的事
- ❌ **MD < 50 ns for ensemble docking** (immediately fail; sampling around starting basin)
- ❌ **MD 50-100 ns** without RMSD plateau check + warning
- ❌ **Holo MD trajectory** for cryptic pocket discovery (apo needed; case dock-007 lesson)
- ❌ **取所有 frames** (1000s) 当 ensemble (computational waste; cluster 5-10 即可)
- ❌ **Single force field** (CHARMM only OR Amber only): critical case 必双跑 cross-check
- ❌ **Boltzmann weighted scoring without ΔG calibration**: ad-hoc weighted 引入 bias
- ❌ **Membrane protein 用 water-only MD**: 必须 lipid bilayer (case dock-012 GPCR caveat)
- ❌ **Cofactor / metal 缺失 of MD**: active site geometry 错

## ★ 失败模式
- **Trajectory not converged**: 100 ns 看似 stable 但 hidden slow degree (domain motion) 需 μs
- **Force field bias to closed conformation**: 某 FF 偏 stable closed state, open under-sampled
- **Apo→holo conformation gap**: G-protein-coupled signaling 大 conformational change apo MD 找不到 holo state
- **Cryptic pocket missed**: MD 短 → 偶尔暴露 pocket 不显; case dock-007 关键 cryptic 在 200+ ns 才出现
- **Cluster representative all identical**: cluster_size = N total frames in single basin, no useful ensemble

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-007):
1. **MD trajectory length ≥ 100 ns** mandatory; ≥ 200 ns recommended for cryptic pocket / GPCR / complex flexibility
2. **Apo MD** for cryptic pocket discovery (NOT holo — holo loses induced-fit signal)
3. **RMSD plateau check** before clustering: backbone RMSD vs frame 0 must show plateau
4. **Cluster 5-10 representatives** (case dock-007 sweet spot)
5. **Best-of-N scoring** for recall (case dock-007); Boltzmann only when proper ΔG calibration
6. **Multi-FF cross-check** for critical predictions (CHARMM36 vs Amber14SB)
7. **Lipid membrane** for membrane proteins; **explicit cofactor / metal**

**Why this beats the anti-pattern**:
- 100 ns is empirical floor for typical pocket flexibility (literature consensus)
- ensemble best-of-N enrichment ~2× rigid for HIV protease (case dock-007); only realized at adequate sampling
- Cryptic pocket discovery: case dock-007 case_lesson — 30 ns 漏掉, 200 ns 抓到

## ★ Validation metric
- docking_type == ensemble_protein_ligand + md_trajectory_length_ns < 50 → BLOCK
- md_trajectory_length_ns 50-100 → WARN (needs RMSD plateau evidence)
- ensemble_docking_pipeline 用 holo MD instead of apo for cryptic pocket case → WARN
- n_cluster_representatives outside 5-10 range → BLOCK (太少漏 state, 太多浪费)

## Lessons → anti-rule
- **anti-rule-09**: ensemble docking MD < 50 ns → BLOCK; 50-100 ns → WARN; apo for cryptic pocket
- Cross-case evidence: dock-007 (HIV protease flap)
- Confidence: medium-high (single case but well-studied; literature consensus)
