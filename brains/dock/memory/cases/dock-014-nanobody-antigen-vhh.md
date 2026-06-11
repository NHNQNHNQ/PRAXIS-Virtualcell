---
case_id: dock-014-nanobody-antigen-vhh
docking_type: antibody_antigen
target_pdb: 7VOA
target_uniprot: [P0DTC2, custom_VHH]
target_class: antibody
ligand_type: protein_antibody
system_specifics:
  CDR_H3_length: 17
  interface_type: transient
tools: [Rosetta SnugDock, NanoNet (preprocessing), AlphaFold-Multimer, IgFold]
flexibility_required: backbone_flex
validation_benchmark: CAPRI
key_paper_doi: 10.1038/s41467-021-25789-9
status: validated
source: praxis_seed
tags: [antibody, nanobody, VHH, single_domain, SARS-CoV-2_RBD, 7VOA, CDR_H3]
---

# Nanobody (VHH) + SARS-CoV-2 RBD：单域抗体 docking 的特殊性

## Background
Nanobodies (VHH = variable heavy domain only, ~15 kDa, derived from camelid heavy-chain Ab) 与传统 Fab/Fv (case dock-004) 在 docking 上有本质差异：
1. **No light chain** — paratope 只来自 H1/H2/H3 (无 L1/L2/L3 配对)；CDR3 通常更长更柔 (> 18 aa 占 ~40%)；
2. **No framework-paratope cross-talk**: traditional antibody framework + light chain 限制 paratope 朝向；nanobody 自由度大；
3. **Convex paratope geometry**: 倾向于结合 cryptic / concave epitope (如 enzyme active site, viral RBD cleft) — 与 IgG 倾向 flat surface 不同；
4. **Format simplicity**: docking 用 single chain，不需 IgFold 配对 H+L。
SARS-CoV-2 RBD-binding nanobody (e.g., Ty1, Nb20, multiple from 2021 papers) 在 7VOA + 类似复合物有大量 cryo-EM/crystal data。

## What I actually did
1. **Nanobody prep**: NanoNet (Cohen-Khait et al. 2022) 专为 VHH 设计的 structure predictor (vs IgFold 用于 Fv)；从 sequence 出 H1/H2/H3 loops
2. **Antigen prep**: SARS-CoV-2 spike RBD (residues 333-527, P0DTC2)；保留 receptor-binding motif (RBM, residues 437-508) — 关键 epitope 区
3. **Initial placement**: epitope hint = ACE2-binding interface 残基 (G446/Y449/Y453/L455/F456/A475/N487/Y489/Q493/Q498/T500/N501/G502/Y505) + RBD 周边 RBM
4. **SnugDock with VHH-mode**: paratope-only restriction ON (CDR1+CDR2+CDR3); n_trajectories 1500 (>1000 typical because longer H3)
5. **CDR H3 length gate**: 该 nanobody H3 = 17 aa ≤ 18 cutoff (case dock-004 lesson) → confidence not auto-degraded
6. **Cross-check**: AlphaFold-Multimer 上 same input → 比较 CDR H3 conformation；RFAA 也跑作为 3rd opinion

## ★ 排除/不做的事
- **用 IgFold (Fab/Fv 工具) on VHH**: IgFold 假设有 light chain，VHH 输出 framework 错位
- **CDR1+CDR2 不参与 paratope**: VHH 大量 binding 来自 H1/H2 (而 Fab 主要 H3 + L1/L2/L3)；不能仅 H3 限制
- **Framework "前面" face 朝向 antigen**: VHH 没有 L chain → framework β-sheet 不同；某些 framework 残基 (e.g., Trp52 hallmark) 反而参与 binding — 不能盲目 framework-only restriction
- **直接套用 case dock-004 SnugDock 参数**: case dock-004 是 Fab; nanobody n_trajectories 应该更多 (H3 自由度大) + paratope mask 不同
- **不验证 ACE2 binding-mode mimicry**: 大多数 spike-binding nanobody 通过 ACE2-mimicry 起作用; docking pose interface RMSD vs ACE2 binding mode 是 sanity (~ < 4 Å)
- **Glycan shielding 缺失**: Spike N343 glycan 部分 mask RBD; glycan-aware nanobody (e.g., Sb#15, Sb#68) 与 non-glycan-aware 应有不同 docking 结果

## ★ 失败模式
- **Long CDR H3 (> 18 aa)** in some VHH (~40% incidence): SnugDock + AF-Multimer 都失败
- **Convex paratope on flat epitope**: VHH 通常找 cryptic pocket — 当 antigen 是 flat surface (e.g., HIV gp120 broad neutralizing site) 时 VHH 表现差
- **Cysteine bridge between CDR1/CDR3**: ~30% camelid VHH 含 noncanonical Cys-Cys (CDR1-CDR3) — 默认 SnugDock 处理不当
- **Allosteric inhibition**: VHH 偶尔 binding 到 enzyme allosteric site → docking 给"correct geometric" 但 in-vivo activity 来自 conformational stabilization 不是 active-site occlusion
- **N-terminal extension**: 某些 VHH 在 N-term 加 myc/HA tag — docking 时不剥离会假 binding
- **Multi-VHH heterodimer (biparatopic)**: 双价 binding 不能单 VHH 单 dock；需 multi-domain (case dock-004 bispecific lesson 推广)

## Lessons → seeds for rules
1. **VHH ≠ Fab in docking**: 必须用 NanoNet (structure prep) + SnugDock VHH-mode (paratope mask 包含 H1+H2+H3 全部, 不仅 H3)
2. **CDR H3 length gate (case dock-004 lesson)** still applies; > 18 → low conf
3. **Convex paratope → seek cryptic/concave epitope**: epitope hint 优先选 pocket-like region
4. **Camelid noncanonical Cys-Cys bridge** must be modeled when present (~30% VHH)
5. **Trajectories ≥ 1500** for VHH (vs 1000 for Fab) due to longer/freer H3
6. **3-way consensus**: SnugDock + AF-Multimer + (RFAA or Boltz) for nanobody-antigen docking; biparatopic nanobody 拆 chain 后并联 dock
