---
name: pose_buster_validate
description: PoseBusters 物理 sanity 检查（atom clash / 键长 / 价态 / chirality / planar amide / fixed amino acids / overall pass）。本地 Python lib（CPU OK），无 GPU 依赖，所有 docking 输出必跑这层。
status: usable
source_case: dock-009-af3-boltz-as-docking
host_env: praxis-dock
---

# pose_buster_validate — Physical sanity check for any docking output

## 一句话原则
**任何 docking pose 必跑 PoseBusters，物理 sanity 不通过 = 高 score 也不可信**。AF3 输出尤其需要（top-1 RMSD < 2Å 但含 atom clash 是常态）。

## 适用阶段
Stage 3 (Execution) — 任何 docking_type，作为后处理 filter。AF3/Boltz/Chai 输出强制跑（case dock-009 enforce）。

## 输入契约

```json
{
  "receptor_pdb": "/path/to/receptor.pdb",
  "ligand_sdf_or_pdb": "/path/to/ligand_pose.sdf",
  "checks_to_run": ["all"],
  "out_json": "/runs/{tid}/posebusters_report.json"
}
```

`checks_to_run` 可选子集：`["mol_pred_loaded", "rdkit_sanitization", "atoms", "bond_lengths", "bond_angles", "internal_steric_clash", "intermolecular_steric_clash", "valence", "kekulization", "geometry", "ring_flat", "double_bond_flat", "amide_planar", "passes_valence_inchi", "passes_kekulization", "passes_geometry", "all_atoms_connected", "smiles", "stereochemistry", "energy_ratio"]`

## 输出契约

```json
{
  "skill_id": "pose_buster_validate",
  "version": "0.6.5",
  "overall_pass": false,
  "n_checks": 19,
  "n_passed": 17,
  "failed_checks": ["intermolecular_steric_clash", "bond_lengths"],
  "per_check": {
    "mol_pred_loaded": true,
    "rdkit_sanitization": true,
    "atoms": true,
    "bond_lengths": false,
    "bond_angles": true,
    "internal_steric_clash": true,
    "intermolecular_steric_clash": false,
    "valence": true,
    "kekulization": true,
    "geometry": true,
    "ring_flat": true,
    "double_bond_flat": true,
    "amide_planar": true,
    "passes_valence_inchi": true,
    "passes_kekulization": true,
    "passes_geometry": true,
    "all_atoms_connected": true,
    "stereochemistry": true,
    "energy_ratio": true
  },
  "command": "python -m posebusters.cli ...",
  "runtime_sec": 3.2
}
```

## ★ 强制 sanity behaviour

1. **No silent skip**：缺 receptor 或 ligand → raise FileNotFoundError，绝不空过
2. **Overall pass = AND of all checks**：单一 check fail = overall fail
3. **Stereo check stricter for AF3 output**：AF3 偶尔翻转 chirality，必须警示
4. **Energy ratio check**：ligand 在 receptor 中的内能 vs 自由能，比值 > 7 = high strain → warn

## 实现状态: usable
- `run.py` 完整可跑：直接调 `posebusters` Python lib（pip install posebusters，已在 pyproject 中）
- 本地 CPU OK；无 GPU 依赖
- 输出 JSON + 可读的 markdown summary（`--md-summary` 选项）

## 引用案例
- **dock-009-af3-boltz-as-docking**: AF3 / Boltz-1 / Chai-1 在 PoseBusters benchmark 上 top-1 RMSD ≤ 2Å rate ~76%，但 ~50% 的 pose PoseBusters check fail（atom clash / 键长 / 价态异常）；强 enforcement 这层是 PRAXIS-Dock 与单纯 AF3 用法的核心区别
