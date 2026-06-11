---
case_id: dock-002-haddock-pp-restraints
docking_type: protein_protein_with_restraints
target_pdb: 1AVX (BPTI-trypsin)
target_uniprot: [P00761, P00974]
ligand_type: protein
tools: [HADDOCK 2.4 / 3.0, AIR (Ambiguous Interaction Restraints), Rosetta, ZDOCK]
key_paper_doi: 10.1038/nprot.2010.32
status: validated
---

# HADDOCK 蛋白-蛋白对接：用 NMR/突变/同源信息引导

## Background
纯 ab initio 蛋白-蛋白 docking 成功率（top 10 中 acceptable hit）通常 < 30%。HADDOCK（Bonvin lab）允许用 NMR chemical shift perturbation、mutation hotspot、同源同源 interface 等"模糊信息"作 AIR 约束，把成功率提到 60-80%。BPTI-trypsin (1AVX) 是 docking benchmark 经典 case。

## What I actually did
1. **输入 prep**：apo BPTI（1BPI）+ apo trypsin（5PTP）—— 用 apo 因为已知 holo 复合物等于答案泄漏
2. **AIR 定义**：
   - Active residues：实验证据（NMR CSP / 突变扫描）已知贡献界面的残基
   - Passive residues：active 周围 5Å 邻居
   - 可有 ambiguous restraint（残基 A-B 中至少一对接触）
3. **HADDOCK 三阶段**：
   - **rigid-body docking** (it0, ~1000 个 model)
   - **semi-flexible refinement** (it1, top 200, 界面侧链 flex)
   - **water refinement** (itw, top 200, water bath + 短 MD)
4. **Cluster + select**：top 200 by HADDOCK score → cluster RMSD 5 Å → 取 top cluster representative
5. **CAPRI quality**：interface RMSD < 1 Å + ligand RMSD < 1 Å = high；< 2/2 = medium；< 4/4 = acceptable
6. **AIR 来源对成功率影响**：
   - 实验 mutation/NMR：成功率高（70-80%）
   - 同源 interface transfer：中（40-60%）
   - 完全 blind（无 AIR）：低（< 30%）

## ★ 排除/不做的事
- **没有任何 AIR 跑 HADDOCK**：等于纯 ab initio，HADDOCK 不是为这设计的
- **Holo 结构当 input**：信息泄漏，任何 benchmark 必用 apo 或 unbound
- **Active residues 范围太广**（> 30 个）：约束被淹没，效果同 blind
- **不做 cluster**：top score 单一 model 可能是 outlier，cluster 才是 ranking 信号
- **CAPRI quality 不报**：只给 top score 不告诉用户 model 物理可信度
- **跳过 water refinement**：interface H-bond 缺水帮助，能量评估偏

## ★ 失败模式
- **Conformational change**：受体在 binding 时大幅 conformational change（kinase activation loop、antibody CDR）→ apo docking 必失败
- **Interface symmetry**：同源 dimer 的两个 monomer 同样可能（C2 对称 vs asymmetric），HADDOCK 不强制对称
- **Multiple binding modes**：真生物学有多个 stable 复合物（如 antibody 有 multiple paratope/epitope），HADDOCK top cluster 只给一个
- **Disordered region in interface**：IDR 参与 interface（~30% 蛋白质相互作用涉及 IDR），rigid docking 概念上失败
- **Glycosylation 影响**：糖屏蔽 interface 残基，模型不含
- **Allosteric vs competitive**：HADDOCK 假设 surface contact，allosteric（远端调节）不适用

## Lessons → seeds for rules
1. **PP docking 必须用 AIR / restraints**——纯 blind 不可行
2. **Apo unbound input** for benchmark；real prediction 用 best available
3. **Cluster size > raw score** for ranking
4. **CAPRI quality label** 必报：high/medium/acceptable/incorrect
5. **Conformational change 警告**：apo→holo RMSD 已知 > 3 Å 的系统标 low confidence
6. **Multiple interface 报多个 cluster**，不只 top 1
