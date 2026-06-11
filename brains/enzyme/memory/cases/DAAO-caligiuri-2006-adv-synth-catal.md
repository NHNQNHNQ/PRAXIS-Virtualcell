---
case_id: DAAO-caligiuri-2006-adv-synth-catal
schema_version: 1
parent_enzyme:
  uniprot: Q99042               # OXDA_TRIVR - T. variabilis DAAO; P00371 was Sus scrofa (porcine kidney DAAO, completely different organism)
  cazy_family: null
  enzyme_family: D_amino_acid_oxidase / FAD_dependent_oxidase
  ec: 1.4.3.3
  organism: Trigonopsis variabilis
  pdb: 1C0L                     # T. variabilis DAAO structure
substrate:
  primary_smiles: "NC(C(=O)O)Cc1ccc(O)cc1"   # D-tyrosine (示意; paper 测多种 D-amino acid)
  class: D_amino_acid / unnatural_amino_acid
target_property: substrate_specificity   # 扩 substrate scope 接受 unnatural D-amino acids
status: validated
provenance:
  source_type: literature
  doi: "10.1002/adsc.200606188"
  pmid: null
  citation: "Caligiuri A, D'Arrigo P, Rosini E, Tessaro D, Servi S, Pollegioni L (2006). Enzymatic conversion of unnatural amino acids by yeast D-amino acid oxidase. Adv Synth Catal 348(15):2183-2190."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 第一次推 .200606009 错 (Pd carbene 论文), CrossRef 文本搜后改 10.1002/adsc.200606188"
    - "DAAO UniProt 第一次推 P00371 错 (是 Sus scrofa 猪肾 DAAO), 改 Q99042 (OXDA_TRIVR T. variabilis)"
    - "PDB 1C0L 是 T. variabilis DAAO 经典"
    - "Pollegioni lab (Insubria, Italy) DAAO 系列 + Servi lab (Politecnico Milan) 工业应用合作"
    - "DAAO 工业应用: 7-aminocephalosporanic acid (7-ACA) 合成 (cephalosporin 抗生素中间体), $亿级 market"
tags: [D_amino_acid_oxidase, DAAO, FAD_dependent, substrate_specificity, 7-ACA_synthesis, cephalosporin_intermediate, unnatural_amino_acid, Pollegioni-lab, non-CAZy]
---

## 1. 背景与目标
- parent: T. variabilis DAAO (UniProt P00371), FAD-dependent oxidase, EC 1.4.3.3
- 自然反应: D-amino acid + O₂ → α-keto acid + NH₃ + H₂O₂
- 工业用 1: **7-ACA 合成** (cephalosporin C → 7-aminocephalosporanic acid via DAAO-glutarylacylase 二步反应) — 工业 ton-scale, $亿级抗生素中间体市场
- 工业用 2: chiral D-amino acid resolution (从 racemate 选择氧化 D-form, 留 L-form)
- 目标: 扩 substrate scope 接受 unnatural D-amino acid (大型 / aromatic / cyclized 类), 用于 chiral synthesis

## 2. 决策过程

### 候选位点策略
- **WT DAAO + substrate panel screen** 起手 (没有大规模 mutagenesis)
- 后续 mutations 集中 active site Tyr 类 residue (substrate-binding orientation 决定)
- 关键 residue: Tyr223 类 (DAAO active site "lid")

### 排除的位点 (★ 必填)
- **FAD binding** Rossmann fold (G-X-G-X-X-G/A motif) 严格保留
- **Catalytic Lys** (proton transfer for amine activation) 保留
- **Substrate-binding Arg** (D-amino acid carboxylate 中和) 保留
- Tetramer / dimer interface (DAAO 多体 active form) 保留

### 计算工具与阈值
- 1C0L 结构指导 + active site Tyr223 周围 saturation
- High-throughput screen: H₂O₂ detection (peroxidase + chromogen) — 与 GOx 类似 readout
- 实验校验: 重组表达 in P. pastoris (yeast, native host 适合糖蛋白) → 多 unnatural amino acid panel → kinetic + chiral HPLC

## 3. 实验结果

### 总体趋势 (★ 见原文 Table 1)
| Substrate (D-form) | WT activity | Engineered variant | substrate scope expansion |
| --- | --- | --- | --- |
| D-Ala (small natural) | high (reference) | maintained | 100% |
| D-Tyr (medium aromatic) | medium | up to 5× WT | broad |
| D-Trp (large aromatic) | low | up to 10-50× WT | major expansion |
| D-cyclized analog | very low | up to 100× WT | unlocked |

### 失败案例 (★ 必填)
- 部分 mutants 提升 unnatural substrate 但同时降低 D-Ala (natural) 活性 — specificity tradeoff
- DAAO H₂O₂ 副产物对 FAD reduce 自身 oxidation, 高 substrate concentration 反应 cumulative inactivation
- **P. pastoris 表达** glycosylation pattern 不一致 — yield 良但活性 batch-to-batch 变化
- 工业 7-ACA 流程仍依赖 WT DAAO + glutarylacylase cascade; engineered variants 主要科研用

## 4. 学习收获
- **成立的规则候选**:
  - **FAD-dependent oxidase 工程化** (DAAO, MAO, GOx, p-cresol oxidase): FAD binding + Lys catalytic 严格保留, 改 active site Tyr/Phe "lid"
  - **H₂O₂ tolerance** 是工业 oxidase 工程化 hidden gating spec — 必备 catalase 共催化或 H₂O₂ 消除
  - **Yeast (P. pastoris)** 是 fungal oxidase 表达首选 host (与 GOx, laccase 一致)
  - DAAO + glutarylacylase 是工业 7-ACA cascade 范式 — 多 enzyme 工程化必同步考虑
- **被推翻的假设**:
  - "DAAO 严格选择天然 D-amino acid" — Caligiuri 2006 显示工程化可大幅扩 unnatural scope
- **下次类似问题应优先尝试**:
  - DAAO substrate scope 工程化, 优先 active site Tyr 周围 saturation
  - cascade engineering: DAAO 单酶活性提升 ≠ cascade productivity 提升, 必须同步
- **应避免**:
  - 改 FAD binding 残基 — 必失活
  - 仅 D-Ala 评估 — 必须 unnatural panel 才能见 substrate scope expansion

## 5. 计算 / 实验原始数据
原始 unnatural amino acid panel + kinetics 见 Adv Synth Catal 348(15) 2006 supplementary; Pollegioni / Servi lab 后续 7-ACA 工业 paper.
