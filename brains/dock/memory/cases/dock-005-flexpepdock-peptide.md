---
case_id: dock-005-flexpepdock-peptide
docking_type: peptide_protein
target_pdb: 1ELW (HSP70-peptide)
target_uniprot: P11142
ligand_type: peptide (5-30 aa)
tools: [Rosetta FlexPepDock, HPEPDOCK, AutoDock CrankPep, AlphaFold-Multimer (peptide as second chain)]
key_paper_doi: 10.1093/nar/gkn216
status: validated
---

# FlexPepDock：多肽-蛋白 docking 的特殊性

## Background
多肽（5-30 aa）docking 是 small molecule 与 protein-protein 之间的奇特 case：太大不能用 small molecule docker（柔性自由度爆炸），太小没有 stable fold（不能 rigid PP docking）。Rosetta FlexPepDock 引入 peptide-specific protocol：peptide backbone + side chain 全 flex。

## What I actually did
1. **Initial placement**：实验/同源信息确定 binding cleft；peptide initial backbone 用 sequence 类似 binder 或 helix prediction
2. **Three-stage**：
   - **Pre-pack**：peptide 在 isolation 中 packing
   - **Low-resolution refinement**：rigid body 调整位置
   - **Full-atom refinement**：peptide backbone + side chain + receptor side chain 全 flex
3. **Sampling 量**：100-200 trajectory（比 SnugDock 少，因 peptide 自由度大需更多但每个收敛更快）
4. **Filter metrics**：interface energy + peptide rmsd-from-start + receptor rmsd-from-start（受体不应大动）
5. **Length-dependent success**：5-15 aa 高（~50% medium quality）；> 20 aa 低（< 20%）
6. **Helix vs extended peptide 难度差**：螺旋 binder 高（已有 secondary structure 约束）；extended peptide 自由度大

## ★ 排除/不做的事
- **用 AutoDock Vina 跑 multi-residue peptide**：超过 ~10 rotatable bonds，Vina 搜索失效
- **HPEPDOCK 默认参数对长肽** (> 20 aa)：cluster radius 不合适
- **Peptide 不带 secondary structure prediction**：螺旋 vs extended 不知道，sample 路线不对
- **Receptor 当 fully rigid**：peptide 诱导 induced fit，binding site side chain 必动；rigid 低估
- **不验证 peptide stability post-docking**：docked pose 可能在水中 unfold，需短 MD verify
- **Peptide N/C terminus 不处理 protonation/charge**：默认 N+C- 或 N0/C0 影响接触

## ★ 失败模式
- **Peptide 无 reference fold**：完全 disordered peptide 找不到 docking start
- **Multiple binding sites on receptor**：HSP70 等 chaperone 有 promiscuous binding，docking top 可能 secondary site
- **Cyclized peptide / disulfide peptide**：FlexPepDock 默认 linear，cyclized peptide 需特殊处理
- **D-amino acids / 非天然 aa**：force field 缺，模型 OOD
- **Long peptide (> 25 aa)**：自由度太多，单一 docking trajectory 不收敛
- **Peptide-mediated PPI**：peptide 是更大蛋白的 fragment（IDP region），单独 dock 与 in context PPI 不同

## Lessons → seeds for rules
1. **Peptide ≤ 20 aa 用 FlexPepDock**；> 20 aa 用 AF-Multimer + MD refinement
2. **Initial backbone secondary structure** (helix/extended) 必须先 predict（PSIPRED / NetSurfP）
3. **Receptor side chain flexibility 必开**——peptide 诱导 induced fit
4. **Length-dependent confidence label**：5-15 aa medium-high；> 20 aa low
5. **Cyclic / non-natural peptide 用专用工具**（HADDOCK with custom topology）
6. **Post-dock MD short check**：docked pose 在 water 50 ns 内不 unfold = stable
