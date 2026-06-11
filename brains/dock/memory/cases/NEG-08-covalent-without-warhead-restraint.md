---
case_id: NEG-08-covalent-without-warhead-restraint
schema_version: 1
docking_type: covalent_protein_ligand
target_pdb: anti-pattern reference (KRAS G12C / BTK)
target_class: GTPase
ligand_type: covalent_warhead_small_mol
system_specifics:
  warhead_type: acrylamide
  reactive_residue: Cys12
tools: [AutoDock Vina 1.2.5]
flexibility_required: rigid
validation_benchmark: none
key_paper_doi: 10.1021/acs.jcim.9b00037
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-08-covalent-no-restraint
tags: [NEG, anti-pattern, covalent, warhead, no-distance-constraint, KRAS-G12C]
---

# NEG-08: Covalent ligand with plain Vina (no warhead detection / no Cys restraint) (anti-rule-08)

## Background (anti-pattern)
团队用 plain Vina 对 sotorasib analog (含 acrylamide warhead) 在 KRAS G12C apo 上 dock。
**Top-1 score -10.2 kcal/mol 但 warhead α-carbon 朝外 (距 Cys12 SG 7.8 Å) — 物理上不可成共价键**。
Team 据此 score 排序送湿实验，所有 top-100 化合物 in vitro 共价标记 KRAS Cys12 失败 (LC-MS 无 +mol mass shift)。

## ★ 排除/不做的事
- ❌ **plain Vina (without `--covalent-residue` / Meeko `--tether_smarts`) on covalent ligand**
- ❌ **Reactive_residue 不指定** (case dock-006 + dock-011 + rule_01 strict requirement)
- ❌ **Distance constraint > 2.0 Å** (or absent)
- ❌ **不识别 warhead SMARTS** (acrylamide / chloroacetamide / Michael acceptor / vinyl sulfonamide / cyanoacrylamide / α-chloroketone / epoxide / boronic acid / nitrile / vinyl ether — 12 patterns)
- ❌ **多个 reactive Cys 不区分** (KRAS Cys12 vs Cys118; BTK Cys481 vs Cys527)
- ❌ **GSH 稳定性不评估** (高反应性 + 低 logP → in-vivo detox)
- ❌ **Cys oxidation state 不验证** (sulfenylated / disulfide → 不可反应)

## ★ 失败模式
- **Warhead points away (>5 Å from SG)**: 高 Vina score 但物理不可共价
- **Wrong target Cys**: 多 Cys receptor，Vina top-1 偶尔指向 secondary Cys (case dock-006 lesson)
- **Reaction kinetics ≠ docking score**: kinact/Ki 来自 QM/wet-lab, not docking; high docking score 不预测 kinact
- **Off-target reactive Cys**: BTK Cys481 selective ibrutinib 同时打 ITK Cys442 (proteome-wide reactive Cys panel 漏)
- **C481S resistance prediction 漏**: 没 reactive_residue 指定 → 不能 dock C481S 评估失活
- **In-vitro LC-MS 无 +mol mass shift**: 共价反应失败的金标准检测

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-006 + dock-011 + rule_01):
1. **Warhead detection** (SMARTS pattern matching, 12 patterns) — auto-detect from SMILES
2. **`reactive_residue` mandatory** in `system_specifics` (e.g., "Cys12") — chain:3-letter:resnum format for Meeko
3. **Distance constraint ≤ 2.0 Å** between warhead α-C and reactive atom (Cys SG / Ser OG / Lys NZ)
4. **Two-step approach**:
   - Step 1: Meeko `--tether_smarts "[CX3]=[CX3][CX3](=O)" --rec_residue "A:CYS:12"` → covalent-attached PDBQT
   - Step 2: Vina with constrained PDBQT → optimize rest-of-ligand around tether
5. **Validate**: top pose RMSD < 2 Å vs known crystal complex (warhead固定, non-warhead atoms 比较)
6. **Off-target Cys panel**: proteome reactive Cys reactivity prediction (recommended)
7. **GSH stability heuristic**: high reactivity + logP < 2 → flag in-vivo detox risk

**Why this beats the anti-pattern**:
- Distance constraint enforces physical possibility of covalent bond
- Meeko `--tether_smarts` 把 warhead 锁到 Cys SG, 强制几何
- C481S / G12C / G12D resistance mutation pre-prediction enabled (旋转 reactive_residue 输入)
- LC-MS +mol mass shift in vitro confirmed in case dock-011 (BTK ibrutinib)

## ★ Validation metric
- docking_type == covalent_protein_ligand + reactive_residue == null → BLOCK (rule_01)
- distance_constraint_A > 2.0 → BLOCK (rule_01)
- chosen_methods 含 vina_gnina_dock 但缺 `--covalent-residue` flag for covalent type → BLOCK
- Warhead SMARTS detection failure (no warhead found in ligand_smiles) + docking_type == covalent → BLOCK or revert to non-covalent

## Lessons → anti-rule
- **anti-rule-08**: covalent_protein_ligand 必有 reactive_residue + distance ≤ 2 Å + warhead SMARTS confirmed; vina_gnina_dock 单跑 → BLOCK
- Cross-case evidence: dock-006 (KRAS G12C sotorasib), dock-011 (BTK Cys481 ibrutinib), rule_01 (formal 5-point)
- Confidence: high (formal rule)
