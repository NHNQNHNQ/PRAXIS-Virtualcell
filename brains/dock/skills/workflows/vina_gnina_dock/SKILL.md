---
name: vina_gnina_dock
description: PRAXIS-Dock 的 PL 默认主力 — AutoDock Vina + GNINA CNN re-scoring consensus，强制 ligand prep（stereo / protonation / tautomer enum）+ box ≤ 22 Å³ + redock self-test gate（top-1 ≤ 2Å rate ≥ 30% else SanityFail）。GNINA 通过 SSH bridge 在远程 GPU 跑（Vina 本地 CPU OK）。
status: usable
source_case: dock-001-redocking-pdbbind-benchmark
host_env: praxis-dock
---

# vina_gnina_dock — Vina + GNINA consensus PL docking

## 一句话原则
**Multi-method consensus（≥ 2 docker）+ 必跑 redock self-test + ligand 三件套 enum + box ≤ 22 Å³**。任何 production PL docking 不跑 redock self-test = 自动 reject。

## 适用阶段
Stage 3 (Execution) — `docking_type ∈ {protein_ligand, protein_ligand_redocking, induced_fit_protein_ligand}`.

## 输入契约

```json
{
  "receptor_pdb": "/path/to/receptor.pdb",
  "ligand_smiles": "CC(C)Oc1cnc(NC2CCC(C(=O)NC3CC3)CC2)nc1",
  "ligand_sdf": null,
  "box_center": [x, y, z],
  "box_size": [22, 22, 22],
  "exhaustiveness": 32,
  "num_modes": 9,
  "energy_range": 4.0,
  "redock_self_test": true,
  "redock_crystal_ligand_path": "/path/to/crystal.sdf",
  "redock_min_top1_rate": 0.30,
  "use_gnina": true,
  "gnina_remote": true,
  "n_seeds": 3,
  "out_dir": "/runs/{tid}/vina_gnina_dock/"
}
```

`gnina_remote=true` 触发 SSH bridge 到 zkyd@10.102.106.53；`use_gnina=false` 跳过 GNINA（仅 Vina）。

## 输出契约

```json
{
  "skill_id": "vina_gnina_dock",
  "ligand_prep": {
    "n_variants": 6,
    "tautomer_enumerated": true,
    "protonation_states": ["pH 7.4 default"],
    "stereo_enumerated": true
  },
  "vina_results": {
    "version": "1.2.7",
    "command": "vina --receptor ... --ligand ... --exhaustiveness 32 --num_modes 9",
    "runtime_sec": 142.3,
    "top_n_poses": [{"rank": 1, "score": -8.4, "pose_path": "..."}]
  },
  "gnina_results": {
    "version": "1.0.3",
    "command": "ssh zkyd@10.102.106.53 'gnina --receptor ... --autobox_ligand ...'",
    "runtime_sec": 45.7,
    "top_n_poses": [...],
    "remote_executed": true
  },
  "consensus_pose": {
    "rank": 1, "vina_score": -8.4, "gnina_cnn_score": 0.91,
    "consensus_rmsd_to_top1_A": 1.2,
    "pose_path": "/runs/{tid}/vina_gnina_dock/consensus_pose1.sdf"
  },
  "redock_self_test": {
    "performed": true,
    "n_tests": 5,
    "top1_le_2A_rate": 0.60,
    "passes_threshold": true,
    "threshold_used": 0.30
  },
  "passed_sanity": true,
  "provenance": {"all_commands": [...], "all_versions": {...}}
}
```

## ★ 强制 sanity checks (case dock-001 lessons)

1. **Ligand prep 三件套**：tautomer enum + protonation @ pH 7.4 + stereo enum — RDKit ETKDGv3 + Dimorphite-DL（缺则 raise SanityFail）
2. **Box ≤ 22 Å³**：box > 30 Å³ 报 warning（飘失败率高）
3. **Redock self-test**：先 redock crystal ligand（最少 5 个），top-1 ≤ 2Å rate < 30% → raise SanityFail（block production）
4. **Multi-method consensus**：必须同时跑 Vina + GNINA（除非用户显式 `use_gnina=false`）
5. **Conserved water**：默认保留所有 receptor water；删除需文献证据（用户传入 `delete_water_resnums` 列表）
6. **Metalloprotein 警告**：检测到 receptor 含 Zn/Mg/Mn/Ca → warn "金属配位力场默认参数不准"

## 实现状态: usable
- `run.py` 完整可跑：Vina 通过 `vina` Python lib（CPU OK），GNINA 通过 SSH bridge 走 zkyd@10.102.106.53 GPU
- Ligand prep: RDKit + meeko + Dimorphite-DL（需 `pip install dimorphite-dl`）
- Receptor prep: BioPython + Reduce（缺 Reduce 时 fall back to PDB 原始 H）
- Redock self-test 自动触发（默认 on）

## 引用案例
- **dock-001-redocking-pdbbind-benchmark**: PDBbind core set 285 个复合物 benchmark, top-1 ≤ 2Å rate Vina 50-60% / GNINA 55-65%
- 失败模式 covered: receptor flexibility (apo→holo gap), symmetric ligand pose, tautomer/protonation 默认错, bridging water 缺失, metalloprotein, macrocycle (rotatable bonds > 10)
