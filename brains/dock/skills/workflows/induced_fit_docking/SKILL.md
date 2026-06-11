---
name: induced_fit_docking
description: Induced Fit Docking (IFD) — rigid docking RMSD > 4 Å 时的 fallback。Schrödinger IFD-MD (商业) 或 Rosetta RosettaLigand (开源)。Side chain flex (≤ 6 residues) — backbone change 不用 IFD（用 ensemble）。10-50× rigid docking 慢，适合 lead opt 不适合 hit-id。
status: skeleton
source_case: dock-008-induced-fit-ifd
host_env: antibody
---

# induced_fit_docking — Side-chain flex docking (rigid fallback)

## 一句话原则
**先 rigid 试，failure (RMSD > 3 Å) → IFD; flex_residues ≤ 6; backbone change 用 ensemble (不 IFD)**.

## 输入契约

```json
{
  "receptor_pdb": "/path/to/receptor.pdb",
  "ligand_smiles": "...",
  "binding_site_residues_5A": [12, 15, 17, 23, 45, 67],
  "flex_residues": [12, 15, 17, 23, 45, 67],
  "n_initial_poses": 20,
  "max_flex_residues": 6,
  "tool": "rosetta_ligand | schrod_ifd_md",
  "remote_gpu": false
}
```

## ★ Sanity checks
1. **First try rigid docking** before IFD (~70% case rigid 已足够)
2. **flex_residues ≤ 6** else BLOCK (case dock-008 lesson; 计算指数增长)
3. **Backbone change 用 ensemble**, not IFD (IFD 只 side chain)
4. **Ligand strain ≤ 5 kcal/mol** vs free state else warn
5. **Multi-trial reproducibility**: 不同 seed 跑 3 次 IFD 看 top pose 一致性
6. **Time budget**: IFD 适合 hit-to-lead (几十化合物); 不适合 hit-id (万级)
7. **Pocket water 不动** caveat — IFD 修 side chain 但 water rigid

## 实现状态: skeleton
Rosetta RosettaLigand 是开源 fallback；Schrödinger IFD-MD 商业。`run.py` 待实现。

## 引用案例
- **dock-008-induced-fit-ifd**: kinase Type II inhibitor (3LMK) — gatekeeper 重排经典 case

## 输出契约

```json
{
  "skill_id": "induced_fit_docking",
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
