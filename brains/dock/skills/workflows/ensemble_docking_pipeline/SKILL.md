---
name: ensemble_docking_pipeline
description: Ensemble docking — apo MD trajectory (≥ 100 ns) → cluster (5-10 representatives) → 每个 conformer 跑 Vina/GNINA → best-of-N or Boltzmann weighted scoring。Cryptic pocket 发现需 apo MD（不是 holo）。MD < 50 ns 警告 / < 100 ns 不允许 production。
status: skeleton
source_case: dock-007-ensemble-docking-md
---

# ensemble_docking_pipeline — MD ensemble docking

## 一句话原则
**Apo MD ≥ 100 ns + cluster 5-10 representatives + best-of-N scoring + cryptic pocket 用 apo (不 holo)**.

## 输入契约

```json
{
  "receptor_pdb": "/path/to/apo_receptor.pdb",
  "md_trajectory_xtc": "/path/to/apo_md_100ns.xtc",
  "md_topology_pdb": "/path/to/topology.pdb",
  "ligand_library_sdf": "/path/to/library.sdf",
  "n_cluster_representatives": 8,
  "cluster_cutoff_A_backbone": 1.5,
  "scoring_method": "best_of_n",
  "remote_gpu": true
}
```

## ★ Sanity checks
1. **MD length ≥ 100 ns** else SanityFail (case dock-007)
2. **Apo input** for cryptic pocket discovery (holo 失去 induced fit signal)
3. **Cluster 5-10 representatives** — 太多浪费、太少漏 state
4. **Best-of-N for recall**; Boltzmann 仅 well-calibrated 系统用
5. **Multi force field cross-check** for critical predictions (CHARMM vs Amber)
6. **Computational budget**: library_size × conformer × time/ligand 必预报
7. **Membrane / cofactor 警告**: 水溶 MD 给的 ensemble 不真实 (membrane protein); 缺 cofactor 时 active site 几何错
8. **Trajectory convergence check** — RMSD plateau before docking

## 实现状态: skeleton
依赖 GROMACS / OpenMM (远程) + gmx_cluster + 多次 Vina/GNINA 调用。`run.py` 待实现。

## 引用案例
- **dock-007-ensemble-docking-md**: HIV-1 protease (3PXF) flap flexibility benchmark

## 输出契约

```json
{
  "skill_id": "ensemble_docking_pipeline",
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
