---
case_id: dock-003-cluspro-blind-pp
docking_type: protein_protein_blind
target_pdb: 7DMU (mAb-RBD)
target_uniprot: [P0DTC2_RBD, custom mAb]
ligand_type: protein_antibody_or_partner
tools: [ClusPro 2.0 (PIPER FFT), ZDOCK 3.0.2, RosettaDock, PyDock]
key_paper_doi: 10.1038/nprot.2016.169
status: validated
---

# ClusPro：纯 blind 蛋白-蛋白 docking 的 baseline

## Background
当 zero 实验信息（无 NMR、无 mutagenesis、无同源 interface）时，FFT-based docking 是唯一可行 baseline。ClusPro PIPER 在 6D 旋转-平移空间穷尽搜索，~70k poses → cluster → top 10 by cluster size。CAPRI 比赛常年高排名。

## What I actually did
1. **Receptor + ligand 上传**（< 999 残基/链，无 hetero atom）；ClusPro 自动 prep
2. **选 scoring weight set**：
   - Balanced（默认）：通用
   - Electrostatic-favored：高带电界面
   - Hydrophobic-favored：疏水 patch interface
   - Antibody mode（针对抗体-抗原，限制 paratope 区到 CDR）
3. **PIPER**：FFT 搜索 ~70,000 rotational sample × 平移
4. **Cluster top 1000 by RMSD 9Å**，取 top 30 cluster
5. **Ranking 关键**：**cluster size 是 main signal，不是 PIPER score**——大 cluster 说明 docking landscape 收敛到那
6. **多 weight 投票**：同一 ligand-receptor 的 top cluster 在 ≥ 3 个 weight set 重复出现 → high confidence
7. **本案 (mAb-RBD)**：使用 antibody mode + Balanced weight 跑两次取 consensus，top cluster 命中 epitope 残基与已知 cryo-EM 一致

## ★ 排除/不做的事
- **盲信 PIPER score**：top 1 by score 经常是 outlier，cluster size 才是
- **不用 antibody mode 跑抗体**：default weight set 不知 paratope 限制，输出 antibody framework 直接 dock 上
- **Skip multi-weight 验证**：单 weight set 的 top cluster 不可信
- **Cluster radius 太小**（< 5Å）：cluster 数过多没意义；> 12Å 太粗合并不同 binding mode
- **ClusPro server 上传 holo（含 partner）**：自动 prep 删 hetero 但残留 conformation 影响，应自己 split chain
- **大蛋白 (> 999 残基) 直接跑**：ClusPro 限制；要先 truncate domain 或用 local install

## ★ 失败模式
- **Conformational selection 错**：apo input 与 holo conformation 差，FFT rigid 找不到正确接触面
- **Multi-domain 蛋白**：两个 domain 间有 hinge，rigid 模式假设 domain 不动 → 错
- **Symmetric 错配**：C2 对称同源 dimer，FFT 给 multiple equivalent solution，cluster 错位
- **Coiled coil interface**：周期性界面让 FFT 多个 solution 平局，cluster size 不主导
- **Cofactor / metal ion 至 interface**：模型不显式建，interface 接触面错位
- **Large flexible ligand (e.g., IgG)**：FFT 视 IgG 为 rigid → CDR + Fc 方向乱

## Lessons → seeds for rules
1. **Cluster size > docking score** for blind PP ranking
2. **Multi-weight 投票**：≥ 3 weight set 出现 = consistent
3. **Antibody mode 必开**当 ligand 是抗体
4. **Cluster radius 9-10 Å** 默认 sweet spot
5. **Multi-domain 警告**：> 2 domain rigid 蛋白先 split domain
6. **Apo input 标 conformational risk**：apo→holo RMSD 已知大的目标，单纯 blind 难
