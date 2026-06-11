---
name: flexpepdock_peptide
description: PyRosetta FlexPepDock — 多肽-蛋白 docking with peptide backbone + side-chain flex（5-20 aa peptide）。> 20 aa 必须切 AF-Multimer（自动 reject）。Initial backbone secondary structure (helix/extended) 必先 predict。Receptor side chain flexibility 必开（peptide 诱导 induced fit）。
status: skeleton
source_case: dock-005-flexpepdock-peptide
host_env: DL-masif
---

# flexpepdock_peptide — Peptide-protein docking

## 一句话原则
**Peptide ≤ 20 aa 用 FlexPepDock; > 20 aa 切 AF-Multimer + MD refinement + receptor side chain 必 flex + initial secondary structure 必预测**.

## 输入契约

```json
{
  "receptor_pdb": "/path/to/receptor.pdb",
  "peptide_sequence": "RHIM",
  "binding_cleft_residues": [12, 15, 17, 23],
  "peptide_secondary_structure": "extended",
  "n_trajectories": 200,
  "receptor_flex_residues": [12, 15, 17, 23],
  "post_dock_md_check": true
}
```

## ★ Sanity checks
1. **Length ≤ 20 aa** else BLOCK (use af3_complex_predict instead, case dock-005)
2. **Secondary structure pre-predicted** (PSIPRED / NetSurfP) else warn
3. **Receptor side chain flex** mandatory（peptide induces induced fit）
4. **Cyclic / non-natural aa** → use HADDOCK with custom topology, NOT FlexPepDock
5. **Post-dock MD short check** (< 50 ns, peptide unfold check)
6. **Length-dependent confidence**: 5-15 aa medium-high; 15-20 aa medium; > 20 aa low

## 实现状态: skeleton
PyRosetta 依赖；远程 SSH bridge。`run.py` 待实现。

## 引用案例
- **dock-005-flexpepdock-peptide**: 1ELW (HSP70-peptide); 5-15 aa ~50% medium quality, > 20 aa < 20%

## 输出契约

```json
{
  "skill_id": "flexpepdock_peptide",
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
