---
case_id: dock-004-snugdock-antibody-cdr-flex
docking_type: antibody_antigen
target_pdb: 1IQD (Anti-FactorVIII Fab)
target_uniprot: [P00451, custom_Fab]
ligand_type: protein_antibody
tools: [Rosetta SnugDock, AbDock, AbAdapt, IgFold (preprocessing), AlphaFold-Multimer]
key_paper_doi: 10.1371/journal.pcbi.1000644
status: validated
---

# SnugDock：抗体-抗原 docking with CDR flexibility

## Background
通用 PP docking 在抗体上失败率高，因为 (1) CDR loop 高度 flexible（特别 H3）；(2) framework 区不应接触抗原（应限定到 CDR）；(3) paratope 几何 vs epitope 匹配复杂。SnugDock 是 Rosetta 模块专为此设计：CDR flexible refinement + paratope-only sampling restriction。

## What I actually did
1. **Antibody prep**：序列 → IgFold 出 Fv 结构（保留正确 framework conformation）
2. **Antigen prep**：apo 或 holo 都行，最好已知 epitope region
3. **Initial placement**：epitope hint（如来自 escape mutation 或 alanine scan）→ 抗体 paratope CDR 朝向 epitope，距离 ~6 Å
4. **SnugDock protocol**：
   - Rigid body 大幅扰动 + RB minimization
   - CDR loop kinematics rebuild（all 6 CDR）
   - Side chain repacking interface
   - 重复 1000 trajectories
5. **Score 与 select**：interface energy + Rosetta full atom score；filter 同时跑 packstat、shape complementarity
6. **CAPRI quality**：通常 medium-acceptable rate ~40%（远高于通用 docking ~10%）
7. **Validation**：与 1IQD crystal 对比，top model interface RMSD < 2.5 Å

## ★ 排除/不做的事
- **用通用 ClusPro/HADDOCK 跑抗体**：没 paratope restriction，抗体可能 framework 朝向抗原（生物学不可能）
- **CDR 不 flexible**：rigid CDR sampling 在 H3 长 loop case 必失败
- **不用 epitope hint**：epitope blind 时 SnugDock 也降到 < 20% success
- **SnugDock 直接跑 long H3 (> 18 aa) Fab**：H3 conformational sampling 不够，需要预先 IgFold + 长 H3 ensemble
- **Antibody framework 用 homology model**：framework 必须高质量（IgFold/ImmuneBuilder 出，不要传统 homology）
- **Single trajectory**：< 1000 trajectory 采样不足

## ★ 失败模式
- **Long CDR H3** (> 20 aa)：所有 antibody-specific docker 在 H3 极长上失败，纯 in silico 无解
- **Conformational epitope vs linear**：序列上不连续但结构上相邻的 epitope，docking 难定位
- **Glycan-shielded epitope**：糖屏蔽部分（spike, gp120），模型不含糖时 docking 给假 binding
- **Allosteric antibody**：抗体作用通过远端 conformational change（如 GPCR allosteric Ab），docking 概念失效
- **Intrinsically disordered antigen**：IDR 抗原（如 alpha-synuclein）单一结构假设错
- **Cooperativity (multivalent binding)**：bispecific Ab 或 IgG with two Fab → 单 SnugDock 仅一 Fab，错失 avidity 效应

## Lessons → seeds for rules
1. **抗体走专用 tool**（SnugDock / AbDock / AbAdapt），通用 PP docking 假阳率高
2. **IgFold prep Fv** 不用 homology model
3. **Epitope hint 是 success 关键**：blind epitope 即使 SnugDock 也不灵
4. **CDR H3 > 18 aa 标 low confidence**：当前所有方法此 case 难
5. **Glycan / IDR / allosteric 标 caveat**：模型外因素必显式声明
6. **Bispecific / IgG 用 multi-paratope mode**，不能只 dock 单 Fab
