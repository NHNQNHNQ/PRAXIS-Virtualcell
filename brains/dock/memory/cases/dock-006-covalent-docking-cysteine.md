---
case_id: dock-006-covalent-docking-cysteine
docking_type: covalent_protein_ligand
target_pdb: 6OIM (KRAS G12C, sotorasib)
target_uniprot: P01116
ligand_type: covalent_warhead_small_mol
tools: [AutoDock Vina (covalent), Schrödinger CovDock, GOLD covalent, ICM-Covalent, RxDock]
key_paper_doi: 10.1021/acs.jcim.9b00037
status: validated
---

# Covalent docking：Cys-warhead 共价反应的 docking 特殊性

## Background
Covalent inhibitor 的 docking 必须同时满足 (1) reversible binding pose 把 warhead 摆到 Cys SG 附近，(2) 共价键形成几何（C-S 距离 < 2 Å）。普通 docking 不知 covalent，会给"看似合理但 warhead 朝外"的 pose。Sotorasib-KRAS G12C (6OIM) 是教学 case。

## What I actually did
1. **识别 reactive Cys**：从 protein 序列 + 结构找潜在 nucleophile（通常 surface-exposed Cys with low pKa）
2. **Warhead 识别**：ligand 含 acrylamide / chloroacetamide / Michael acceptor 等
3. **Two-step approach**:
   - Step 1: warhead 与 Cys SG 形成 bond（pre-attached）
   - Step 2: rest of ligand pose optimize around the constraint
4. **Vina covalent extension**：用 `--ligand_pdbqt` 含已 attached warhead 的版本，加 distance restraint
5. **CovDock (Schrödinger)**：自动两步——先 reversible docking 再 covalent attachment + minimization
6. **Validation**：与 6OIM crystal pose RMSD < 2 Å for non-warhead atoms（warhead 本身 fixed）
7. **Multi-conformer Cys**：Cys SG 旋转 isomers，可能需多 conformer
8. **MS confirmation simulation**：模拟 MS/MS 确认 mod site；docking 给 Cys12 modification 与实测一致

## ★ 排除/不做的事
- **用普通 Vina 跑 covalent ligand**：score 高但 warhead 朝错方向，pose 物理不可成键
- **不指定 distance restraint**：docking 不强制 C-S 接近，自由能 minimum 不在共价 pose
- **跨 reactive Cys 不区分**：proteome 有 ~100 reactive Cys，docking 需限定到 target Cys
- **Reaction kinetics 不考虑**：docking 只给 binding pose，不给 kinact/Ki；后者需另 QM 或 wet lab
- **Warhead reactivity 假设**：所有 acrylamide 反应活性不同（取代基影响 EWG/EDG），docking 不区分
- **Off-target Cys 不评估**：单 docking 看 target，不看 proteome-wide 反应性

## ★ 失败模式
- **Cryptic pocket → reactive Cys**：apo 结构 Cys 不暴露，必须 holo 或 MD 才看到
- **多个候选 Cys**：受体多个 Cys 都可能 reactive（KRAS Cys118 vs Cys12），docking 需多 trial
- **GSH reactivity 假阳**：高反应性 warhead 在体内被 GSH detox，docking pose 体外正确但体内无效
- **Reversible covalent 与 irreversible 区分**：reversible covalent (cyanoacrylamide 等) 平衡态分析不同
- **Cys oxidation state**：Cys 可能 disulfide / sulfenylation 形态，不可反应
- **Docking 给 high score 但 in vitro 不 covalent**：共价反应 require 几何 + 反应活性两件，docking 只管几何

## Lessons → seeds for rules
1. **Covalent docking 用专用工具**：Vina + restraint 或 CovDock，不普通 docking
2. **Distance constraint 必加**：C-S < 2 Å enforce
3. **Two-step approach**：reversible binding → covalent formation
4. **Off-target Cys 评估**：proteome reactive Cys panel 跑反应性 prediction
5. **Reaction kinetics 单独评估**：kinact/Ki 不来自 docking score
6. **GSH stability 评估**：避免 in vivo detox
7. **Cys oxidation state 报告**：reactive Cys 必须 reduced 形态
