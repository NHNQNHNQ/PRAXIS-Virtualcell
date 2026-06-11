---
case_id: dock-008-induced-fit-ifd
docking_type: induced_fit_protein_ligand
target_pdb: 3LMK (kinase with Type II inhibitor)
target_uniprot: any (case-by-case)
ligand_type: small_mol
tools: [Schrödinger IFD-MD, Rosetta RosettaLigand, AutoDock Vina + side chain flexibility, MOE Induced Fit]
key_paper_doi: 10.1021/jm060522a
status: validated
---

# Induced Fit Docking (IFD)：当 rigid docking RMSD > 4Å 时的拯救方案

## Background
Rigid docking 假设 receptor side chain 不变，但实际 ~30% protein-ligand binding 涉及 binding site side chain 重排（kinase gatekeeper, GPCR transmembrane re-pack 等）。IFD 让 binding site side chain 在 docking 中 flex。Schrödinger IFD-MD 是商业金标准；Rosetta RosettaLigand 是开源等价。

## What I actually did
1. **Trigger condition**：先 rigid docking → top score pose RMSD vs known crystal > 3 Å + score 不收敛 → IFD candidate
2. **Schrödinger IFD-MD pipeline**：
   - Step 1: Glide rigid docking（standard precision），生成 ~20 initial pose
   - Step 2: Prime side chain prediction，binding site 5 Å 残基重新 packing per pose
   - Step 3: Glide redocking 进重 packing receptor
3. **Rosetta RosettaLigand**：类似但 trajectory-based MC sampling
4. **Vina 加 side chain flex**：`--flexres "A:LYS:1234"` 参数，但限制 ≤ 4 个 flex residue（计算量爆炸）
5. **Validation**：IFD 给的 pose RMSD vs crystal 通常 < 2.5 Å (vs rigid 4-6 Å)
6. **Time cost**：IFD 比 rigid 慢 10-50 x；适合 lead optimization 不适合 library screening

## ★ 排除/不做的事
- **不先做 rigid docking 试一下**：~70% case rigid 已足够，IFD 是 fallback
- **IFD 跑 large library**：每 ligand 几分钟到几小时，library > 1000 不实际
- **不限 flex residue 数**：> 6 flex side chain 计算指数增长，return diminishing
- **IFD 当 ground truth**：仍是 docking 估计，> 1 kcal/mol error 仍是常态
- **Backbone flexibility 当 IFD 处理**：IFD 通常仅 side chain；backbone change 需 MD 或 ensemble docking
- **Ligand strain 不评估**：IFD 给 ligand 在 receptor 中位置，但 ligand 自身 conformation 高 strain 是 red flag

## ★ 失败模式
- **Backbone-level conformational change**：IFD 不动 backbone；kinase activation loop flip / GPCR TM helix shift 需 MD
- **Multiple IFD outcomes**：不同 initial pose 给不同 final，没收敛——top by score 不一定 right
- **Small molecule strain**：ligand 在 receptor 中扭曲到 high strain energy，physical 不可达
- **Side chain rotamer locked by H-bond network**：IFD 给的 packing 破坏 native H-bond → 假 stable
- **Pocket water 不动**：IFD 修 side chain 但 binding site water 仍 rigid
- **Force field 不准 in flexible region**：side chain repacking accuracy 受 force field 限制

## Lessons → seeds for rules
1. **IFD 是 rigid docking failure 的 fallback**，不是 first try
2. **Flex residue ≤ 6**：超过计算爆炸
3. **Backbone change 不用 IFD**：用 ensemble docking + MD
4. **Ligand strain energy 评估**：IFD pose 中 ligand internal energy ≤ 5 kcal/mol vs free
5. **Time budget**：IFD 适合 hit-to-lead（几十化合物），不适合 hit-id（万级）
6. **Multi-trial reproducibility**：不同 random seed 跑 3 次 IFD 看 top pose 一致性
