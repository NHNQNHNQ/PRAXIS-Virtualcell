---
case_id: NEG-03-rigid-receptor-large-conformational-gap
schema_version: 1
docking_type: protein_ligand
target_pdb: anti-pattern reference (kinase activation loop)
target_class: kinase
ligand_type: small_mol
system_specifics:
  ligand_drug_likeness: drug_like
tools: [AutoDock Vina 1.2.5]
flexibility_required: rigid
validation_benchmark: none
key_paper_doi: 10.1021/jm060522a
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-03-rigid-when-conformational-change
tags: [NEG, anti-pattern, rigid-receptor, conformational-change, kinase]
---

# NEG-03: Rigid receptor docking with apo→holo gap > 3 Å (anti-rule-03)

## Background (anti-pattern)
团队拿到 kinase apo crystal (DFG-out / activation-loop 折叠形态) 直接 rigid Vina 对 type II inhibitor
(known to bind DFG-in conformation)。**没识别出 apo→holo activation loop RMSD 的预期幅度**。
结果 top-1 pose RMSD vs known crystal complex ≈ 5.8 Å (anti-pattern threshold > 3 Å)。
Rigid receptor 假设破坏 → docking pose 物理可行但生物学错。

## ★ 排除/不做的事
- ❌ **rigid docking 时不查 apo vs holo conformation 文献**: 已知大幅变化 (DFG-in/out / αC helix in/out / activation loop) 的系统不能 rigid
- ❌ **跨 conformation state**: apo → 找 type II/III inhibitor; agonist holo → 找 antagonist (case dock-012 lesson)
- ❌ **single rigid pose 当 final**: 即使 docking score 好，先怀疑 conformation 假设
- ❌ **不显式 declare flexibility_required: rigid** in design_plan when system requires sidechain_flex / backbone_flex / ensemble

## ★ 失败模式
- **Kinase DFG-out vs DFG-in**: type II inhibitors (imatinib-like) 在 DFG-out 才结合; rigid DFG-in apo → 漏 50%+ true hits
- **GPCR active vs inactive**: TM6 outward movement ~14 Å; antagonist 在 inactive crystal docking, agonist 在 active
- **Allosteric kinase activation loop**: 前所有 type III BCR-ABL allosteric pose 漏掉 if rigid + active state
- **Cofactor-induced conformational change** (e.g., HIV protease flap closure): apo flap-open vs holo flap-close ~6 Å

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-007 ensemble + dock-008 IFD):
1. **Step 0**: 查 PDB 多 entry 是否有同一蛋白 multiple conformations + 比对 RMSD
2. **If apo→holo RMSD > 3 Å**: switch to:
   - **ensemble_docking_pipeline** (apo MD ≥ 100 ns + cluster 5-10 reps + best-of-N) — case dock-007
   - OR **induced_fit_docking** (rigid baseline first; flex residues ≤ 6) — case dock-008
   - OR **af3_complex_predict** (foundation model handles backbone flex)
3. **For GPCR specifically**: state-match — antagonist 用 inactive crystal, agonist 用 active (case dock-012)
4. **Confidence label**: rigid-on-rigid-target = high; rigid-on-flex-target = low (auto-degrade)

**Why this beats the anti-pattern**:
- 30% protein-ligand binding 涉及 induced fit (literature consensus)
- Ensemble docking enrichment ~2x vs rigid (case dock-007)
- Cost: ensemble +10x runtime; IFD +30x; **but failure cost (湿实验 fail) is much higher**

## ★ Validation metric
- design_plan.flexibility_required == "rigid" 但 system 已知 conformational change > 3 Å → WARN
- 缺 `apo_vs_holo_rmsd_check` in scoping_plan.problem.constraints → WARN
- For kinase target_class: 必须 declare DFG state hypothesis OR plan ensemble — else WARN

## Lessons → anti-rule
- **anti-rule-03**: 已知 apo→holo conformational change > 3 Å + rigid docking → BLOCK; route to ensemble or IFD
- Cross-case evidence: dock-007 (HIV protease flaps), dock-008 (kinase Type II), dock-012 (GPCR state matching)
- Confidence: high
