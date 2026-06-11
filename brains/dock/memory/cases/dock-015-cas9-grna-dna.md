---
case_id: dock-015-cas9-grna-dna
docking_type: protein_nucleic_acid
target_pdb: 4OO8
target_uniprot: Q99ZW2
target_class: CRISPR_endonuclease
ligand_type: nucleic_acid
system_specifics:
  na_strandedness: ds
  sequence_specificity: PAM
tools: [HDOCK, AlphaFold3 (NA), RoseTTAFold-2NA, NPDock, ChimeraX visualization]
flexibility_required: backbone_flex
validation_benchmark: none
key_paper_doi: 10.1038/nature13579
status: validated
source: praxis_seed
tags: [NA, CRISPR, Cas9, gRNA, sgRNA, PAM, NGG, 4OO8, ribonucleoprotein]
---

# SpCas9 + sgRNA + target dsDNA：CRISPR ribonucleoprotein docking

## Background
Streptococcus pyogenes Cas9 (SpCas9) 是 CRISPR genome editing 主流酶；与 simple TF-DNA (case dock-010) 不同，CRISPR docking 涉及三重复合物：
- **Protein** (Cas9, ~1368 aa)
- **gRNA** (single-guide RNA, ~100 nt — crRNA + tracrRNA scaffold)
- **target dsDNA** (~20 bp protospacer + PAM)
完整 ribonucleoprotein (RNP) docking 不能用单步 protein-NA tool — 必须分层：(1) Cas9-sgRNA pre-bind, (2) RNP + target dsDNA。
4OO8 (Anders 2014 Nature) 是首个 SpCas9-sgRNA-target DNA 三元复合物 crystal — PRAXIS-Dock 在此 case 学习 RNP-DNA 多步 docking + PAM specificity。

## What I actually did
1. **Cas9-sgRNA pre-bind**: 从 4OO8 取 Cas9 + sgRNA 部分 (chain A + chain B); apo Cas9 (4CMP) 与 sgRNA-bound (4OO8) RMSD ~10 Å — 必须用 holo (gRNA-bound)
2. **Target DNA prep**: 用户 input target sequence (e.g., "GACGCATAAAGATGAGACGCTGG" — 20 nt protospacer + NGG PAM); RNAComposer 出不适用 (DNA), 用 sequence-specific 3DNA / Discovery Studio build dsDNA
3. **PAM 必显式 specify**: NGG (SpCas9 canonical); 输入 SMARTS-like flag — 检查 docking pose 把 NGG 摆到 PI domain (residues 1097-1130 of Cas9)
4. **Multi-method consensus**:
   - **AlphaFold3 (NA mode)**: 输入 Cas9 seq + sgRNA seq + target DNA seq → joint fold
   - **HDOCK**: blind RNP-DNA docking (no PAM hint) + cluster score
   - **NPDock**: NA-specific docker
   3 个 top-1 pose 比较 — AF3 + HDOCK 一致 = high confidence
5. **Sequence specificity validation**:
   - PAM-PI domain contact: Arg1333/Arg1335 ↔ G of NGG (Hsu 2014)
   - Seed region (PAM-proximal 8-12 bp) protospacer-sgRNA Watson-Crick pairing — 检查 H-bond network
   - 远端 (PAM-distal) bulged DNA conformation
6. **Conformational change warning**: Cas9 经历大幅 HNH domain rotation (~180°) when sgRNA loaded; rigid docking 假设破坏

## ★ 排除/不做的事
- **用 apo Cas9 (4CMP) docking sgRNA**: apo→holo gap 过大，rigid docking 失败
- **PAM 不显式指定**: docking 任意把 dsDNA 摆向 — 物理可成 binding 但 sequence-specific cleavage geometry 错
- **直接 single-step Cas9 + DNA docking (skip sgRNA)**: 没 sgRNA 时 Cas9 没结合 specificity；必须先 RNP pre-bind
- **复用 TF-DNA docker (case dock-010 HDOCK 设置)**: PAM 几何与 TF-DNA PWM motif 不同 — RNP 不是 TF
- **DNA 假设 B-form rigid**: target DNA 在 R-loop conformation (sgRNA-DNA hybrid) 是 A/B 混合 form; rigid B-form 错
- **HNH/RuvC catalytic domain rigid**: HNH 切 target strand, RuvC 切 non-target; docking 不直接预测 cleavage activity 但要保留 catalytic pocket geometry
- **Off-target prediction by docking score alone**: 真实 off-target 由 mismatch tolerance + chromatin accessibility 决定; docking 是 in-silico filter 但不全
- **不验证 R-loop hybrid base pairing**: protospacer-sgRNA 互补对 (20 bp) 必须 Watson-Crick — docking pose 必查每个 base pair 的 H-bond

## ★ 失败模式
- **Mismatch tolerance**: SpCas9 容忍 PAM-distal 1-3 bp mismatch; docking pose 不能直接告诉哪个 mismatch site 残留 cleavage
- **Chromatin context**: in-vivo accessibility 来自 nucleosome positioning + epigenetic marks; docking 单复合物不模拟 chromatin
- **Sa/St/Cas12/Cas13 cross-orthogonal**: 每个 Cas family PAM 不同 (SaCas9 NNGRRT; St1Cas9 NNAGAAW; Cas12a TTN; Cas13 RNA target); 必须 family-specific
- **Anti-CRISPR proteins (AcrIIA/IIC)**: 抑制因子直接 occlude PAM 结合 → docking 不直接显示 inhibition mechanism
- **R-loop cleaved state (post-cut)**: docking 是 pre-cleavage; cleaved state 蛋白释放 ≠ docking pose
- **gRNA secondary structure error**: tracrRNA scaffold 折叠错 → 整个 RNP 几何错
- **Mg2+ in HNH/RuvC active site**: 缺失则 catalytic geometry 错; 显式建模

## Lessons → seeds for rules
1. **CRISPR docking 必须分层**: Cas9-sgRNA → RNP-target dsDNA — 不能 single-step
2. **PAM 必显式**: SpCas9 NGG; SaCas9 NNGRRT; Cas12a TTN — 每个 Cas family 不同
3. **R-loop hybrid base pairing 强制 validate**: docking pose 中 sgRNA-DNA 20 bp Watson-Crick H-bond network must form
4. **Use holo (sgRNA-bound) Cas9** crystal/AF3 prediction — apo 不可用
5. **Family-specific docker**: SpCas9 和 Cas12a 的 PI domain geometry 不同; 不能交叉参数
6. **AF3 NA mode is first-line** for full RNP-DNA prediction (case dock-009 + dock-013 RFAA 共识 + NA-specific 升级)
7. **Mg2+ 显式建模** for catalytic activity prediction (off-target nuclease activity 评估)
