---
case_id: dock-010-protein-rna-dna-docking
docking_type: protein_nucleic_acid
target_pdb: 1FJG (30S ribosome with mRNA), 1MEY (TF-DNA)
target_uniprot: TF, ribosome subunits
ligand_type: RNA / DNA / oligo
tools: [HDOCK (PP+nucleic), NPDock, AlphaFold3 (NA support), RoseTTAFold-2NA, HADDOCK with NA]
key_paper_doi: 10.1093/nar/gkx1037
status: validated
---

# Protein-RNA/DNA docking：核酸 backbone 柔性 + 序列特异性

## Background
RNA-binding protein（RBP）、转录因子（TF-DNA）、CRISPR Cas-gRNA 等 case：核酸 backbone 比 protein 更柔性 + 碱基 stacking 让 conformational sampling 困难。专用 tool（HDOCK、NPDock、AF3-NA）比 PP docking 更适合。AF3 (2024) 引入 NA 支持是 game-changer。

## What I actually did
1. **Input prep**：
   - Protein receptor（apo or holo）
   - RNA/DNA：从序列 → 用 simRNA / RNAComposer 出 3D，或用 known RNA structure (Rfam family)
2. **HDOCK 跑**：FFT-based blind docking（类 ClusPro），加 NA-specific scoring
3. **AF3 直接 input**：`protein_sequence:ATGC...` 形式，AF3 自动联合 fold
4. **Sequence specificity**：TF-DNA 对应的 motif (PWM) 必须与 docking pose interface 残基一致；Cas-gRNA 必须 PAM 序列正确放置
5. **Validation**：1MEY (Zif268-DNA) 是 TF benchmark；docking interface RMSD < 3 Å + key Arg 与 GC base contact
6. **AF3 vs HDOCK**：AF3 pose accuracy 高（top-1 acceptable rate ~50%），HDOCK ~30%；但 AF3 训练含 PDB-NA 复合物，OOD 序列下降

## ★ 排除/不做的事
- **用 PP docking** (ClusPro/HADDOCK 不带 NA mode) **跑 NA**：scoring function 偏 protein-protein，NA 接触面 underweight
- **不考虑 sequence specificity**：TF docking pose 与 PWM 不一致 = wrong；docking 必须 sequence-aware
- **RNA 用 helix-only 假设**：复杂 RNA 有 hairpin/internal loop/pseudoknot，单 helix 模型 oversimplify
- **DNA 默认 B-form**：实际 binding 时 DNA 可弯曲（TBP-TATA 弯 90°），rigid B-form docking 错
- **不验证 base recognition**：interface 残基必须与碱基 (A/T/G/C) 形成 specific H-bond，否则 sequence specificity 假
- **Cas-gRNA 不指定 PAM**：CRISPR docking 必须 PAM (NGG for SpCas9) 显式 specify

## ★ 失败模式
- **Single-stranded vs double-stranded RNA**：ssRNA 极柔，rigid docking 假设破坏
- **RNA secondary structure incorrect**：input 3D structure 错（loop/stem 不对），下游 docking 全错
- **DNA bending in TF binding**：TBP/IHF 等弯 DNA 蛋白，要 ensemble of bent DNA 形态
- **R-loop / triplex / G-quadruplex**：罕见 NA 结构，多数 docker 不支持
- **CRISPR off-target prediction**：sequence mismatches → docking score 应 reflect specificity，但当前 tool 弱
- **Modified bases**（5mC, 6mA, m1A）：docking force field 缺参数

## Lessons → seeds for rules
1. **NA-specific docking tool** 必用，不通用 PP
2. **NA 3D structure quality 是上游瓶颈**：RNA 用 RNAComposer 出 + 验证；DNA 用 sequence-specific bent模型
3. **Sequence specificity 强制 validation**：interface residue ↔ base 形成 specific contact
4. **Cas-gRNA PAM 强制 specify**
5. **AF3 NA 支持是 first-line**，但仍需 HDOCK / NPDock cross-check
6. **Modified base 走专用 force field**（CHARMM-modified-DNA 等）
