---
case_id: immuno-010-tcr-pmhc-docking
schema_version: 1
task: tcr_pmhc_complex_modeling
immuno_task: tcr_pmhc_complex_modeling
antigen_class: viral
hla_class: HLA_I
hla_alleles: ["HLA-A*02:01"]
peptide_length_bin: "9"
disease_indication: infection_htlv
target_pdb: 2BNQ (HLA-A2 + Tax peptide + TCR A6)
target_protein_uniprot: []
tools: [TCRdock, TCRen, ESM-IF, AlphaFold-Multimer with custom MSA, Rosetta SnugDock]
key_paper_doi: 10.1038/s41587-023-01989-0
status: validated
source: praxis_seed
---

# TCR-pMHC docking：T cell antigen recognition 结构建模

## Background
TCR-pMHC 复合物结构是 T cell antigen recognition 核心。Crystal 难得（~600 PDB structures），ML/docking 方法成主流。**特殊难点**：(1) TCR CDR3 高度柔性；(2) docking footprint canonical （diagonal across MHC)；(3) MHC restriction 决定 CDR3 binding mode。

## What I actually did
1. **Inputs**：TCR α + β chain sequences + peptide sequence + HLA allele
2. **Initial structure**：
   - TCR：IgFold for VαVβ Fv structure
   - pMHC：AF-Multimer (HLA + peptide) → docked complex
3. **TCRdock (specialized model)**：trained specifically on TCR-pMHC PDB → 直接预测
4. **AF-Multimer with custom MSA**：3 chains (TCR α + TCR β + HLA) + peptide as second sequence
5. **Validation against crystal**：2BNQ 是 reference，docking pose interface RMSD < 3 Å
6. **CDR3 flexibility**：multiple seed sample，看 CDR3 conformation cluster
7. **Specificity prediction**：given TCR + peptide library, rank likelihood
8. **Use case**：TCR-T therapy 设计 → 推 TCR sequence 与 target neoantigen 互动

## ★ 排除/不做的事
- **通用 PP docker**：HADDOCK / ClusPro 在 TCR-pMHC 不适合（specialized binding mode）
- **No HLA prep**：HLA needs peptide loaded; apo HLA docking 错
- **Single seed**：CDR3 flex 高，多 seed 必备
- **Skip MHC restriction**：peptide-MHC 必须先 stable，再 TCR engagement
- **Class II 用 class I model**：HLA-DR vs HLA-A docking pose 不同，preditor 分开
- **不做 specificity ranking**：TCR-T therapy 必须排序 candidate TCR

## ★ 失败模式
- **TCRdock 训练数据少**：~600 crystal structure，OOD 容易错
- **CDR3 H3 long > 15 aa**：sampling 不足
- **Peptide-MHC instability**：unstable pMHC 不 present, TCR engagement 不重要
- **Cross-reactivity prediction**：TCR 通常 cross-react multiple peptides，single docking 不能 capture
- **TCR signaling vs binding**：binding ≠ activation；structural docking 不预测 signaling
- **TCR avidity**：单 TCR-pMHC affinity vs T cell avidity (multiple TCR) 完全不同 scale

## Lessons → seeds for rules
1. **Specialized TCR docker (TCRdock) > generic**
2. **HLA + peptide loaded** before TCR docking
3. **AF-Multimer with TCR α/β + HLA + peptide** as alternative
4. **Multiple seed for CDR3 flex**
5. **Class I vs II separate pipeline**
6. **Validation against crystal 2BNQ etc.**
7. **Specificity ranking** for therapy design
