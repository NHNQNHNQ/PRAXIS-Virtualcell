---
case_id: dock-007-ensemble-docking-md
docking_type: ensemble_protein_ligand
target_pdb: 3PXF (HIV-1 protease)
target_uniprot: P03366
ligand_type: small_mol
tools: [GROMACS / OpenMM (MD), AutoDock Vina, GNINA, RMSD-based clustering, gmx_cluster]
key_paper_doi: 10.1021/ci2002704
status: validated
---

# Ensemble docking：用 MD snapshot 对付 receptor flexibility

## Background
单 crystal structure docking 假设 receptor 是 rigid，但实际 binding 涉及 induced fit / conformational selection。Ensemble docking = 取 MD trajectory 多个 snapshot 作 receptor → 对 ligand 库 docking → 综合排名。HIV protease flap 高度柔性是经典 case。

## What I actually did
1. **MD prep on apo receptor**：100-500 ns MD（OpenMM Amber 14SB + TIP3P）
2. **Trajectory clustering**：每 ns 取 frame → RMSD-based clustering（gromos algorithm，cutoff 1.5 Å backbone）
3. **Receptor 选择**：top 5-10 cluster representatives 作 ensemble；优先选有"open pocket" 的 frames（pocket volume 用 fpocket 算）
4. **Docking on each conformer**：相同 ligand 库对每 conformer 跑 Vina
5. **Score combine**：
   - **Best-of-N**：每 ligand 取 N 个 conformer 中最低 score（增加 recall）
   - **Weighted average**：按 cluster 大小（population）加权
   - **Boltzmann weighted**：exp(-E/kT) 加权 ensemble
6. **Validation**：known active 在 ensemble best-of-N enrichment 比 single rigid docking ~2x 高
7. **Cryptic pocket 检测**：MD 中偶尔暴露的 pocket 在 single crystal 看不到——ensemble 抓住

## ★ 排除/不做的事
- **MD 太短** (< 50 ns)：sampling 不足，cluster 还是 around starting structure
- **取所有 frames 当 ensemble** (1000s)：computational waste；cluster representative 5-10 即可
- **Boltzmann weight without proper dG calibration**：ad-hoc weighted 反而引入偏
- **MD 在 holo 形态**：失败的 receptor 无 induced fit 信号；apo MD 才能找 cryptic
- **Single force field**：CHARMM vs Amber 给的 ensemble 不同；critical case 双跑
- **不分 stable cluster vs transient**：population < 1% 的 transient frame 不应作 main scoring receptor

## ★ 失败模式
- **Trajectory not converged**：100 ns 看似 stable 但 hidden slow degree（domain motion）需 μs
- **Forcefield bias to closed conformation**：某 force field 偏 stable closed state，open state under-sampled
- **Apo vs holo conformation gap**：apo MD 找不到 holo state（如 G-protein-coupled signaling 大幅 conformational change）
- **Membrane protein 缺 lipid**：水溶 MD 给的 ensemble 不真实
- **Cofactor / metal ion impact**：apo MD 不含 cofactor，pocket 几何错
- **Computational cost**：每 ligand × 10 conformer = 10x cost；library size 受限

## Lessons → seeds for rules
1. **MD 长度** ≥ 100 ns for typical pocket flexibility，或直至 RMSD plateau
2. **Cluster 5-10 representative**：太多浪费、太少漏 state
3. **Best-of-N scoring** for recall；Boltzmann 仅 well-calibrated 系统用
4. **Apo MD** for cryptic pocket 发现
5. **Multiple force field cross-check** for critical predictions
6. **Computational budget 预报**：library_size × conformer × time/ligand
