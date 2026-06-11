---
case_id: NEG-02-single-method-no-consensus
schema_version: 1
docking_type: protein_ligand
target_pdb: anti-pattern reference
target_class: mixed
ligand_type: small_mol_drug_like
system_specifics: {}
tools: [AutoDock Vina 1.2.5]
flexibility_required: rigid
validation_benchmark: none
key_paper_doi: 10.1038/s41586-024-07487-w
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-02-single-method
tags: [NEG, anti-pattern, single-method, no-consensus]
---

# NEG-02: Single docking method ranked & shipped (anti-rule-02)

## Background (anti-pattern)
团队仅用 Vina top-1 score 排序候选，**没跑 GNINA / AF3 / Boltz cross-check**。Vina top-1 RMSD vs crystal
平均 ~3.5 Å (优秀但有 ~50% 在 3-10 Å 区间)；GNINA CNN_score 与 Vina 经典 score 在某些 case 系统性
分歧 (kinase hinge water 重要 → Vina 漏，GNINA CNN 抓得到)；AF3 / Boltz 在 OOD 化合物上失败模式
完全不同。**Single method = single failure mode → 假阳率高**。

## ★ 排除/不做的事
- ❌ **只跑 Vina (or GNINA, or AF3) 单方法** + ship top-1
- ❌ **Cross-method consensus level 缺失字段** in execution_results
- ❌ **当 Vina/GNINA score 与 AF3 iPTM 分歧时不报 divergent**
- ❌ **不计算 cross_method top-1 pose RMSD** (作为 consensus quality metric)
- ❌ **声称 "Vina top-1 是最优 pose"** 而无独立 cross-validation

## ★ 失败模式
- **Kinase hinge water-mediated H-bond**: Vina 漏 → 错排候选；GNINA CNN 偶尔抓
- **Macrocycle / large rotatable bond ligands**: Vina sampling 不足；DiffDock 偏 blind 模式失败
- **Novel scaffold (post-2021 PDB)**: AF3 训练不全 → 退化到 Vina 水平甚至更差
- **Metalloprotein**: 所有方法都偏，但失败模式不同 → consensus 暴露分歧 = warning
- **湿实验 hit rate 比 multi-method 低 30-50%** (industry estimates)

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-001 + dock-009 + dock-013):
1. **≥ 2 method mandatory**: e.g., vina_gnina_dock + af3_complex_predict (Boltz)
2. **Cross-method consensus**: top-1 RMSD between methods < 2 Å = high; 2-4 Å = medium; > 4 Å = divergent
3. **3-way for high-stakes**: AF3 + Boltz + RFAA (case dock-013)
4. **Method picks complementary failure modes**:
   - Vina (rigid scoring) ↔ GNINA (CNN re-scoring) ↔ AF3 (foundation model)
   - 不同失败模式 = consensus 真正信息

**Why this beats the anti-pattern**:
- Method 间分歧本身是 useful signal (不是 noise) — divergent → low confidence label
- Single method top-1 RMSD ≤ 2 Å rate ≈ 50%; 2-method consensus ≈ 70%; 3-method ≈ 80% (industry)
- Failure modes 互补: Vina 漏 hinge water + GNINA 漏 OOD scaffold + AF3 漏 cofactor → 三方 alibi

## ★ Validation metric
- design_plan.chosen_methods.length < 2 → BLOCK (PRAXIS-Dock multi-method consensus rule)
- execution_results.cross_method_consensus.level == null → BLOCK
- consensus.level == "divergent" 但 confidence_label ∉ {low, cold_start} → BLOCK
- 唯一豁免：case dock-007 ensemble docking 单方法但 N conformer (counts as multi-pose)

## Lessons → anti-rule
- **anti-rule-02**: ≥ 2 docking methods mandatory; single-method = auto-reject
- Cross-case evidence: dock-001 (Vina + GNINA + DiffDock), dock-009 (AF3 + Boltz), dock-013 (RFAA tri-consensus)
- Confidence: high
