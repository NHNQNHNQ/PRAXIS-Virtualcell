---
case_id: dock-001-redocking-pdbbind-benchmark
docking_type: protein_ligand_redocking
target_pdb: PDBbind core set 2020 (285 complexes)
target_class: mixed (kinase/protease/GPCR/...)
ligand_type: small_mol_drug_like
tools: [AutoDock Vina 1.2.5, GNINA 1.0, Smina, DiffDock 1.1, AutoDock4.2.6]
key_paper_doi: 10.1021/acs.jcim.8b00545
status: validated
---

# PDBbind redocking：所有 docking 方法的金标准 benchmark

## Background
Redocking = 把已知共结晶的 ligand 重新 docking 回 receptor，看 top pose 与 crystal pose RMSD。PDBbind 2020 core set（285 个非冗余复合物）是行业标准 benchmark。**任何 docking pipeline 跑这个 < 30% RMSD ≤ 2Å 算不及格**。

## What I actually did
1. **Receptor prep**：每个 PDB → 去 ligand → 去水（保留 conserved interface water if specified）→ Reduce 加 H → MGLTools/Meeko PDBQT
2. **Ligand prep**：从 crystal 提 ligand → RDKit assign bond order → ETKDGv3 重新 3D → Open Babel 加 H pH 7.4
3. **Docking modes**：
   - Vina：`--exhaustiveness 32 --num_modes 9 --energy_range 4`，box 22 Å³ 居中 crystal ligand
   - GNINA：CNN re-scoring on Vina pose
   - Smina：Vina-fork，custom scoring function
   - DiffDock：DL-based blind docking（不指定 box，全蛋白搜索）
   - AutoDock4：传统 LGA 算法
4. **关键 metric**：
   - Top-1 RMSD ≤ 2 Å rate（最严）
   - Top-5 RMSD ≤ 2 Å rate（更宽容）
   - Average RMSD across 285 cases
5. **典型结果**（行业公开 benchmark）：
   - Vina top-1 ≤ 2Å: ~50-60%
   - GNINA top-1 ≤ 2Å: ~55-65%
   - DiffDock top-1 ≤ 2Å: ~38% (blind, no box)
   - AutoDock4 top-1 ≤ 2Å: ~45%
6. **Failure mode 分析**：DiffDock 在 PDBbind 不如 box-guided，但 blind 设置下其他工具更差

## ★ 排除/不做的事
- **不做 redocking validation 直接 trust docking**：black box，任何 production pipeline 必须有 self-redocking sanity
- **跨 train/test split**：DiffDock 训过 PDBbind，比较时要看 time-split / similarity-split benchmark（PDBbind core 与训练有泄漏）
- **只看 average RMSD**：被极端 outlier 拉偏；要看 % ≤ 2Å 这种 categorical metric
- **Box 太大让 Vina 飘**：box > 30 Å 会显著降 success rate
- **不重新 prep ligand**：直接用 crystal coordinates 进 Vina = 作弊（信息泄漏）
- **混 metalloproteins / cofactor 进 default benchmark**：金属 + 共因子需特殊参数

## ★ 失败模式
- **Receptor flexibility caused failures**：> 30% redocking failure 来自 binding site 在 holo vs apo 形态差异（即使是 holo 重 docking 也可能受 prep 步骤影响）
- **Symmetric ligand pose ambiguity**：苯环对称、双键 cis/trans 让 RMSD 计算虚假高
- **Tautomer/protonation 默认值不准**：~10% case 的 ligand 在 pH 7.4 不是 default RDKit 给的状态
- **Bridging water 缺失**：2-3% cases binding 完全靠保守 water-mediated H-bond（如 HIV protease），删掉 = 必死
- **Metalloprotein 失败率高**：Zn/Mg coordination 默认 force field 不对
- **Macrocycle / rotatable bonds > 10**：搜索空间大，sampling 不充分

## Lessons → seeds for rules
1. **Redocking benchmark 必须做**：production docking 上线前在自己的 target 上 redock，% ≤ 2Å < 30% 就警告
2. **Box-guided > blind**：信息可知时不用 blind docking
3. **多 method 并跑**：Vina + GNINA + DiffDock 至少两个，consensus rank
4. **Metric 用 categorical**（% ≤ 2Å）not continuous（mean RMSD）
5. **Ligand prep 是常被低估的失败源**：tautomer/protonation/stereo 三件套 enum
6. **Conserved water 文献查 + 显式保留**：HIV protease、kinase hinge water 等
