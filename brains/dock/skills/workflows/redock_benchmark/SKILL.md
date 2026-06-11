---
name: redock_benchmark
description: PRAXIS-Dock 自检模块 — 在用户 receptor 上跑 redocking benchmark（5-50 个 known crystal complexes），输出 top-1/5/10 RMSD ≤ 2 Å rate，作为 production docking 上线的 self-test gate。≥ 30% threshold 才允许 production。
status: skeleton
source_case: dock-001-redocking-pdbbind-benchmark
host_env: praxis-dock
---

# redock_benchmark — Self-test gate before production PL docking

## 一句话原则
**Production PL docking 前必跑 redock self-test，top-1 ≤ 2Å rate < 30% 直接 block**。这是 PRAXIS-Dock 与 black-box pipeline 的核心区别。

## 输入契约

```json
{
  "receptor_pdb": "/path/to/receptor.pdb",
  "crystal_complexes": [
    {"complex_pdb": "/path/to/1m17_complex.pdb",
     "ligand_chain": "L", "ligand_resname": "AQ4"}
  ],
  "docker": "vina_gnina_dock",
  "min_top1_le_2A_rate": 0.30,
  "n_complexes_required": 5
}
```

## 输出契约

```json
{
  "skill_id": "redock_benchmark",
  "n_complexes_tested": 50,
  "top1_le_2A_rate": 0.58,
  "top5_le_2A_rate": 0.78,
  "top10_le_2A_rate": 0.85,
  "average_rmsd": 1.94,
  "passes_threshold": true,
  "per_complex_details": [...],
  "outliers": [{"pdb": "...", "reason": "metalloprotein"}]
}
```

## ★ Sanity checks
1. **Top-1 ≤ 2 Å rate ≥ 30%** else block
2. **% rate (categorical) > average RMSD (continuous)** for reporting
3. **Box ≤ 22 Å³** for typical PL；> 30 Å³ warn
4. **Self-redock with re-prepped ligand** — 不能直接用 crystal coords（信息泄漏 = 作弊）

## 实现状态: skeleton
计划用 `vina_gnina_dock` 在循环中调用 + RMSD 比对。当前仅契约。

## 引用案例
- **dock-001-redocking-pdbbind-benchmark**: PDBbind core set 285 complexes, Vina top-1 ≤ 2Å ~50-60%, GNINA ~55-65%
