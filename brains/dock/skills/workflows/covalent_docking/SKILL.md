---
name: covalent_docking
description: 共价配体 docking（Cys / Ser / Lys 等 nucleophile + warhead）— 两步 approach: warhead pre-attached 到 reactive residue + rest-of-ligand pose 优化。Vina covalent extension 或 Schrödinger CovDock。distance constraint < 2 Å enforce。proteome-wide off-target Cys 评估推荐.
status: skeleton
source_case: dock-006-covalent-docking-cysteine
host_env: praxis-dock
---

# covalent_docking — Covalent inhibitor docking

## 一句话原则
**两步 approach: pre-attach warhead 到 reactive Cys + distance constraint < 2 Å + reactive Cys 必指定 + GSH stability 评估推荐**.

## 输入契约

```json
{
  "receptor_pdb": "/path/to/receptor.pdb",
  "ligand_smiles": "C=CC(=O)Nc1ccc...",
  "reactive_residue": "Cys12",
  "warhead_pattern": "acrylamide",
  "distance_constraint_A": 2.0,
  "off_target_cys_panel": false,
  "docker": "vina_covalent | schrod_covdock"
}
```

## ★ Sanity checks
1. **reactive_residue 必填** else BLOCK (Reviewer rule)
2. **warhead detection**: acrylamide / chloroacetamide / Michael acceptor SMARTS 自动识别；不识别 → warn
3. **distance constraint ≤ 2.0 Å** mandatory
4. **Multi-conformer Cys**: SG rotamer enum
5. **Off-target Cys panel** (recommended)：proteome reactive Cys 反应性 prediction
6. **GSH stability** evaluation: 高反应性 warhead 在体内 detox
7. **Cys oxidation state**: must be reduced (not disulfide / sulfenylation)
8. **Reaction kinetics 单独评估**: kinact/Ki 不来自 docking score（docking 只管几何）

## 实现状态: skeleton
计划用 Vina covalent extension（pre-attached warhead PDBQT + distance restraint）。Schrödinger CovDock 是商业 fallback。`run.py` 待实现。

## 引用案例
- **dock-006-covalent-docking-cysteine**: KRAS G12C / sotorasib (6OIM) — 教学 case

## 输出契约

```json
{
  "skill_id": "covalent_docking",
  "receptor": "",
  "ligand": "",
  "best_affinity": 0.0,
  "poses": [
    {
      "rank": 1,
      "affinity_kcal_per_mol": 0.0,
      "pose_path": ""
    }
  ],
  "runtime_sec": 0.0,
  "diagnostics": {
    "brain": "dock",
    "archetype": "docking"
  }
}
```
