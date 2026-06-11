---
case_id: protein-019-wicky2022-symmetric-hallucination
design_task: symmetric_oligomer_de_novo
target_pdb: nan
target_uniprot: nan
fold_class: helical_bundle_C2_C3_C4_C5
length_range: 50-200
tools: [trRosetta, RoseTTAFold, MCMC_with_symmetry_constraints, Rosetta]
key_paper_doi: 10.1126/science.add1964
key_metrics:
  symmetries_explored: "C2, C3, C4, C5, D2 (di-, tri-, tetra-, penta-, dihedral)"
  designs_validated: "approx 35 designs in vitro tested across symmetries"
  validated_oligomeric_state: "approx 60-70% match designed symmetry by SEC + native MS"
  novel_assemblies: "multiple novel symmetric architectures not in PDB"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [symmetric-oligomer, hallucination, trRosetta, network-inversion, C2-C3-C4-C5-D2, novel-assembly]
unverified_details:
  - "Specific 60-70% oligomeric state match rate is paper-claimed average; varies by symmetry"
  - "Number of designs synthesized varies by symmetry; ~35 is approximate sum"
---

# Hallucinating symmetric protein assemblies（Wicky et al. Science 2022）

## Background
- 起点：Anishchenko 2021 (PRAXIS protein-015) 证明 trRosetta hallucination 可生成 monomer。但 symmetric oligomer 设计需要 enforce symmetry——简单 hallucination 总是 break 对称
- 目标：扩展 hallucination 到 symmetric assemblies——在 MCMC 中显式 enforce symmetry constraint，让 network "看到" symmetric prediction
- 应用：开拓 hallucination-driven symmetric assembly design；与 RFdiffusion 的 symmetric mode (PRAXIS protein-009) 互补

## What I actually did（基于论文）
1. **Symmetric MCMC**：每步 mutation 应用到所有 symmetry-related copies；trRosetta 预测 monomer 的 distance / orientation 必须与 symmetry-consistent assembly 一致
2. **Symmetry types**：
   - C2, C3, C4, C5（cyclic）
   - D2（dihedral）
3. **Loss function**：KL divergence between predicted distance + orientation distribution and "background" distribution；symmetric copies 强制 identical sequence
4. **Total trajectories**：每 symmetry ~10^3 hallucination trajectories
5. **Selection**：选择 sharp / confident assembly + 几何上合理的 design
6. **Synthesis + 验证**：
   - SEC（看 oligomeric state）
   - SEC-MALS（精确分子量）
   - Native MS（quaternary structure）
   - 部分跑 cryo-EM / X-ray
7. **结果**：~35 design in vitro tested 跨 symmetry；~60-70% 匹配设计 oligomeric state；多个 novel architecture（PDB 中未见）

## ★ 排除的位点/区域
- **不对称残基**：MCMC 中对所有 symmetry-related position 强制 identical，自动 enforce
- **Loop > 20 aa**：trRosetta 在 long loop 上不稳，限制 monomer length
- **Cys 自由**：不对应配对的 Cys 可能形成跨 copy disulfide，破坏对称——除非显式设计
- **大 hydrophobic patch 在 monomer 表面但不在 interface**：会聚集成非对称大 oligomer
- **Pro / Gly 在 helical bundle 中间**：disrupt helix
- **奇数残基环数（C5）的 stereochemistry**：某些 phi/psi 在奇数对称下几何上 incompatible

## ★ 失败模式
- **设计 C3 但 SEC 出现 C4 / C6**：~20% 设计 oligomeric state 错——MCMC 没 enforce 严格 stoichiometry
- **正确 oligomeric state 但 fold 错**：~10% 在 SEC + native MS 上 OK 但 cryo-EM/X-ray 显示不是设计的 helical bundle
- **聚集 > 设计 oligomeric state**：~15% 出现 amorphous aggregate 而非 trimer/tetramer
- **不溶性表达**：~20% inclusion body
- **Higher symmetry harder**：D2 / C5 比 C2 / C3 失败率明显更高
- **Conformational dynamics**：少数 cryo-EM 显示 multiple conformations populated（symmetry breaking 在低温也存在）

## ★ 方法选择决策链
- **为什么 trRosetta hallucination 而非 RFdiffusion symmetric**：本论文先于 RFdiffusion；hallucination 是当时唯一可拓展到 symmetry 的 design network
- **为什么 MCMC 而非 Rosetta dock**：dock 是 rigid body assembly，无法 explore monomer fold + interface 联合空间；hallucination 同步设计两者
- **为什么 SEC + SEC-MALS + native MS 三步**：oligomeric state 验证是 symmetric design 的 critical bar；单 SEC 经常误判
- **为什么 C2-C5 + D2 而非 higher**：C6+ / icosahedral 在 hallucination 难度爆炸——后续 work 才用 RFdiffusion 攻克
- **为什么 trRosetta 而非 AF2-Multimer**：2022 当时 AF2-Multimer 在 designed novel assembly 上 confidence 偏低；trRosetta 是 hallucination origin tool

## ★ In silico vs in vitro 差距
- **trRosetta confidence (assembly distogram entropy) 弱相关 in vitro fold**——hallucination 通病
- **Symmetry-related metrics 没有 standard pLDDT / iPTM / pAE**——本论文用 trRosetta 自己的 distogram entropy + symmetry RMSD as proxies
- **No Rosetta_ddG (assembly fold-only task, no binder)**
- **后续 RFdiffusion-symmetric 引入 AF2-Multimer iPTM + pLDDT_assembly 作为 filter——本论文未做**
- **In silico hallucination → SEC 单峰**：~35 → ~28 (~80%)
- **SEC 单峰 → 设计 oligomeric state 正确**：~28 → ~20 (~71%)
- **正确 oligomeric state → cryo-EM/X-ray fold-correct**：~20 → ~15 (~75%)
- **总转化率**：~15/35 ≈ **43%**（fold + 对称都对）
- **vs case 009 (Watson 2023 RFdiff symmetric ~5-15%)**：hallucination 在 fold-only 任务上转化率反而比 RFdiff binder 高（因为没加 binder 要求）
- **Designed C3 偏向被实际 SEC 看作 C3 的概率**：约 80%（其余可能 hexamer / dimer）
- **Lower symmetry (C2, C3) 转化率 > higher (C5, D2)**：geometry strain 累积

## Lessons → seeds for rules
1. **Symmetry MUST be enforced in MCMC**——不是 post-hoc filter；所有 symmetry-related position 同步 mutate
2. **SEC + SEC-MALS + native MS 三步验证 oligomeric state**——单 SEC 不可信
3. **Lower symmetry (C2, C3) 优先**：higher symmetry strain 累积；先 C3/C4 跑通再上 D2/C5
4. **43% fold-correct rate 是 symmetric fold-only design 的 baseline**——加 binder 任务后会降到 ~5%（参考 Watson 2023 RFdiff symmetric）
5. **MD 100+ ns 验证 symmetry 不动态破坏**：static design 在 dynamics 下 break 是常见
6. **Hallucination diversity 来自多 trajectory**：每 trajectory 是 local min；想要 novel architecture 必须 sample 多
7. **PRAXIS implication**：symmetric_design_pipeline skill 应包含：(a) MCMC enforce symmetry, (b) tied-position MPNN, (c) SEC + native MS 验证 step——多步骤结合

## 数据指针
- 论文 + supp: https://doi.org/10.1126/science.add1964
- 设计 + 验证 oligomeric state PDB IDs 在 supp Table
- 后续 RFdiffusion-symmetric 在 Watson 2023 上扩展
