---
case_id: protein-013-bhardwaj2016-hyperstable-cyclic-peptide
design_task: cyclic_peptide_de_novo
target_pdb: nan
target_uniprot: nan
fold_class: cyclic_macrocycle
length_range: 7-14
tools: [Rosetta, Generalized_Kinematic_Closure_GenKIC, Rosetta_Score, NMR, X-ray]
key_paper_doi: 10.1038/nature19791
key_metrics:
  designs_synthesized: "12 head-to-tail cyclic + disulfide-stapled peptides"
  validated_by_NMR: "all 12 fold to design-target conformation (within ensemble)"
  Tm_designs: ">95 deg C (hyperstable, no melting transition observed up to limit)"
status: validated
schema_version: 1
source: literature
extracted_at: 2026-05-01
tags: [cyclic-peptide, macrocycle, GenKIC, Rosetta, hyperstable, NMR-validated, de-novo]
unverified_details:
  - "Exact PDB IDs of NMR/X-ray structures: see supp; not enumerated here"
  - "All-atom RMSD between design model and NMR ensemble centroid: paper reports backbone RMSD < 1.5 Å for most designs"
---

# 超稳定 cyclic peptide 从零设计（Bhardwaj et al. Nature 2016）

## Background
- 起点：1990s 起 cyclic peptide drug 已有（cyclosporin A 等）但全是天然产物。de novo 计算设计的 cyclic peptide 之前都不能达到天然产物的 hyperstability
- 目标：用 Rosetta 设计 7-14 aa head-to-tail 环肽（含 disulfide），让设计在水溶液中 fold 到唯一构象，hyperstable（不温度去折叠）
- 应用：奠基性论文，建立了"de novo cyclic peptide design"领域。后续 RFdiffusion / AfCycDesign / HighFold 等 cyclic peptide 工具的 reference benchmark

## What I actually did（基于论文）
1. **Topology enumeration**：枚举 7-14 aa 头尾环 + 0/1/2 disulfide bridge 的所有可能 D/L-aa 组合 backbone topology
2. **Generalized Kinematic Closure (GenKIC)**：Rosetta 的环闭合算法，构造满足闭环约束的 backbone（包括 D-aa / L-aa）
3. **Backbone sampling**：每个 topology 跑 ~10^5 GenKIC closure → 几何上合法的 backbone 池
4. **Sequence design**：fixed-backbone Rosetta FastDesign，氨基酸 type 选择最低 Rosetta score
5. **Stability filter**：跑 Rosetta ab initio 折叠，只留下设计 backbone 是 ab initio 全局最低能量 funnel 的 candidate
6. **Selection**：12 个 candidate 选定（覆盖不同长度 7/9/11/14 + 0/1/2 SS）
7. **Synthesis**：固相多肽合成 + 头尾环化 + disulfide 形成（air oxidation）
8. **Validation**：NMR（CD + 2D NOE + temperature serie）+ 部分 X-ray（小分子衍射）
9. **结果**：12/12 设计在 NMR 上 fold 到设计 target conformation；多数 Tm > 95°C（含温度上限测试），多数在 6 M GdmCl 仍 fold

## ★ 排除的位点/区域
- **D-aa 在没有 chiral 设计需求的位置**：D-aa 引入仅用于 closing 几何要求；其他位置全 L
- **proline 在不需要 turn 的位置**：Pro 锁 phi 角，乱用打乱 helix；Pro 仅在 turn motif 的 i+1 / i+2 位置
- **疏水内核暴露表面**：与全长蛋白不同，cyclic peptide 表面积小，疏水残基要内嵌；表面优先极性
- **Disulfide bridge 在 i / i+3 距离**：Cys-Cys 几何上要 4-9 Å；过近过远扭曲 backbone
- **Met / Trp in solvent-exposed positions**：氧化敏感（Met）+ 大基团 entropy cost（Trp 表面）
- **All-Gly stretches**：会让结构 entropy 太高，多构象

## ★ 失败模式
- **未通过 NMR 验证**：早期 prototype（论文之前）部分 design 在 NMR 显示多 conformation populated，没 unique fold——通过更严格的 Rosetta funnel 选择解决
- **合成失败**：head-to-tail 环化产率 < 50%（部分 sequence 需要多次纯化）
- **Disulfide 错配**：双 disulfide 的 design 可能形成错误 SS 配对（不是设计意图的 1-3, 2-4，而是 1-4, 2-3）；通过 SS-mapping 验证
- **D-aa 合成成本**：D-aa 单体价格高 5-10x，限制 SAR 探索
- **温度 / 蛋白酶 challenge 失败例**：极少数 design 在高温稳定但 trypsin / chymotrypsin 切割快——可优化但论文未深入

## ★ 方法选择决策链
- **为什么 GenKIC 而非自由 backbone sampling**：cyclic peptide 必须满足闭合 constraint（首尾相接 + disulfide）；GenKIC 在闭合空间上枚举 vs 自由 sampling 99% 不闭合
- **为什么 Rosetta FastDesign 而非 ProteinMPNN**：2016 年 ProteinMPNN 还没出现；Rosetta talaris 2014 score function 在 cyclic peptide 上验证过
- **为什么 ab initio 折叠 funnel filter**：design backbone 是合法的不够——必须是 sequence 折到此 backbone 的全局最低能量；否则 in vitro 会 fold 到别的 conformation
- **为什么 7-14 aa 范围**：< 7 aa 几何上闭合困难，无 secondary structure；> 14 aa 设计搜索空间爆炸 + 合成困难
- **为什么 NMR 验证而非 X-ray 优先**：cyclic peptide 难结晶；NMR ensemble 是 cyclic peptide 标准验证 modality

## ★ In silico vs in vitro 差距
- **No standard pLDDT / iPTM / Rosetta_ddG metrics**：本论文用 Rosetta talaris score function（pre-AF2）打分 backbone funnel；不 report pLDDT（AF2 metric 当时不存在）
- **Surface chemistry 隐式由 Rosetta SAP score 控制**——表面疏水残基设计中过滤
- **设计 → NMR fold 验证率**：12 designs → 12 fold correctly = **100% in vitro success**（这是 cyclic peptide design 的高水准）
- **合成产率**：大部分 ~30-50%（环化反应限制）
- **稳定性测试**：12/12 在测试温度 (95°C) 下未去折叠，多数在 6 M GdmCl 中仍 fold
- **比 mini-protein binder（Cao 2020 LCB ~1%）**：cyclic peptide 这条路 in silico → in vitro 转化率显著高，因为：
  1. 设计 size 小 (7-14 aa)，less degrees of freedom
  2. Disulfide / 头尾环化是强约束，几何选择性高
  3. 无 binder 要求（fold-only target），不需要 interface 验证
- **但**：本案例是 fold-only 设计，没有 functional binding 需求；加入 binding 后转化率会大幅下降（见后续 Bhardwaj 2022 / Wu 2023 binder cyclic peptide 案例）

## Lessons → seeds for rules
1. **GenKIC 是 cyclic peptide design 的 gateway algorithm**——闭合 constraint 满足是 necessary
2. **Ab initio funnel filter 是质量护城河**：不只是 design backbone 合法，而是 sequence 真折到此 backbone
3. **D-aa / disulfide / 头尾环化是设计杠杆**：可大幅 expand 可达 conformation space
4. **Cyclic peptide fold-only 任务转化率显著高于 mini-binder**——在 7-14 aa range 100% NMR fold 是可达成的
5. **NMR ensemble 是 cyclic peptide 标准验证**：X-ray 不易；CD + 2D NOE + DOSY 联合
6. **设计要 hyperstable 才有意义**：Tm < 60°C 的 cyclic peptide 在血清/胃肠环境快速去折叠；Tm > 95°C 是 drug-like 起点

## 数据指针
- 论文 + supp: https://doi.org/10.1038/nature19791
- NMR 结构 ensemble 在 supp 中
- Rosetta 协议 RosettaScripts XML 在 supp materials
