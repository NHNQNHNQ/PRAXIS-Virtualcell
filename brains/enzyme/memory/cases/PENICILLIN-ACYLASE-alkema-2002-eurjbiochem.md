---
case_id: PENICILLIN-ACYLASE-alkema-2002-eurjbiochem
schema_version: 1
parent_enzyme:
  uniprot: P06875               # E. coli penicillin acylase (PAC_ECOLI)
  cazy_family: null
  enzyme_family: penicillin_acylase / Ntn_hydrolase
  ec: 3.5.1.11
  organism: Escherichia coli
  pdb: 1AJN                     # E. coli penicillin acylase 经典结构 (Duggleby 1995)
substrate:
  primary_smiles: "CC1(C)S[C@@H]2N(C(=O)C[C@H]2NC(=O)Cc3ccccc3)C1C(=O)O"   # benzylpenicillin (penicillin G)
  class: beta_lactam_antibiotic / acylated_amino_compound
target_property: substrate_specificity   # acyl transfer activity for synthesis (vs hydrolysis)
status: validated
provenance:
  source_type: literature
  doi: "10.1046/j.1432-1033.2002.02857.x"
  pmid: null
  citation: "Alkema WB, Dijkhuis AJ, de Vries E, Janssen DB (2002). The role of hydrophobic active-site residues in substrate specificity and acyl transfer activity of penicillin acylase. Eur J Biochem 269(8):2093-2100."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1046/j.1432-1033.2002.02857.x 我推测; QA via CrossRef 验证"
    - "E. coli PA UniProt P06875 高把握"
    - "PDB 1AJN 是 PA 经典结构 (Duggleby 1995); 论文用其变体"
    - "Janssen lab (Groningen) penicillin acylase 系列工程化"
    - "PA 是 Ntn-hydrolase (N-terminal nucleophile), N-端 Ser 是 catalytic base"
tags: [penicillin_acylase, Ntn_hydrolase, antibiotic_synthesis, substrate_specificity, acyl_transfer, hydrophobic_pocket, semi_synthetic_antibiotics, Janssen-lab, non-CAZy]
---

## 1. 背景与目标
- parent: E. coli penicillin acylase (PA, UniProt P06875), Ntn-hydrolase, EC 3.5.1.11
- 自然反应: penicillin G + H₂O → 6-aminopenicillanic acid (6-APA) + phenylacetate (hydrolysis)
- 工业用 1: 抗生素生产 (6-APA 是 semi-synthetic penicillin 中间体, 工业 ton-scale)
- 工业用 2: **逆反应 (acyl transfer)**: 6-APA + activated acyl donor → semi-synthetic penicillin
- 目标: 通过 hydrophobic active site mutation 调 hydrolysis vs acyl transfer 平衡 — 让 PA 偏向 synthesis 反应

## 2. 决策过程

### 候选位点策略 — Rational hydrophobic pocket engineering
- **Hypothesis**: active site 周围 hydrophobic residues (Phe / Trp / Leu cluster) 决定 substrate 取向 + acyl-enzyme 中间体稳定性
- 选择 ~5-7 关键 hydrophobic residues:
  - Phe24α (β subunit) — substrate hydrophobic pocket
  - Phe71β
  - Met149β
  - Phe146β
- Site-directed mutagenesis 选 single + double mutants

### 排除的位点 (★ 必填)
- Ntn-hydrolase **N-terminal Ser1β** (catalytic nucleophile) 严格保留 — autoprocessing + reaction 必需
- α/β subunit interface (PA 是 αβ heterodimer formed via autoprocessing) 不动
- Oxyanion hole 主链 NH 保留
- Pre-pro 区 (PA 自切割成熟必需) 不动

### 计算工具与阈值
- 1995-2002 年代: PyMOL + active site geometry visualization
- Activity assay: hydrolysis (penicillin G → 6-APA) + transferase (6-APA + activated donor → product)
- 实验校验: 重组表达 in E. coli → 多 substrate panel + kinetics → kobs(transferase) / kobs(hydrolysis) ratio

## 3. 实验结果

### 关键发现 (★ 见原文 Table 1-2)
| Variant | Hydrolysis kcat/Km | Transferase / hydrolysis ratio |
| --- | --- | --- |
| WT PA | high | ~0.2 (mostly hydrolysis) |
| Single hydrophobic mutation | moderate | up to ~1.0 |
| Double mutation (e.g., F24A + F71L) | reduced hydrolysis | up to ~3-5 |
| Strategy | hydrophobic pocket 越"开放", transferase ratio 越高 |

### 失败案例 (★ 必填)
- 部分 hydrophobic-pocket mutations 大幅 reduce 整体活性 — 必须双指标
- Semisynthetic penicillin synthesis 仍受 substrate inhibition 限制
- Transferase ratio 提升通常 cost specificity (同时接受 unwanted side reaction)
- 部分变体 autoprocessing (mature αβ formation) 失败 — pre-pro region 周围 mutation risky

## 4. 学习收获
- **成立的规则候选**:
  - **Ntn-hydrolase 工程化的核心**: 不动 N-terminal nucleophile + autoprocessing, 改 active site 周围 hydrophobic pocket
  - **Hydrolysis vs transferase 平衡**: 这是 PA 类 enzyme 工业 application 决定性 spec, 必须 explicit 设计
  - **Hydrophobic pocket "openness"** 决定 acyl-enzyme intermediate 偏好的 nucleophile (water vs amine) — 工程化目标
- **被推翻的假设**:
  - "PA 工业反应路径只能 hydrolysis" — Alkema 2002 显示 transferase ratio 可大幅工程化
- **下次类似问题应优先尝试**:
  - 任何 hydrolytic enzyme 工业用于 synthesis 反应, 评估 transferase ratio engineering
  - Hydrophobic pocket residues (Phe/Trp/Leu cluster) 是 specificity 工程化高价值
- **应避免**:
  - 触动 autoprocessing required residues (pre-pro, processing site)
  - 仅 hydrolysis 评估 — 工业用必同测 transferase

## 5. 计算 / 实验原始数据
原始 PA 工程化 + 反应数据见 Eur J Biochem 269(8) 2002 supplementary; Janssen lab 后续 Alkema 2003 Protein Eng follow-up.
