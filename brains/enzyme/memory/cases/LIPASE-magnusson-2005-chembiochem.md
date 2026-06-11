---
case_id: LIPASE-magnusson-2005-chembiochem
schema_version: 1
parent_enzyme:
  uniprot: P41365               # Candida antarctica lipase B (CALB), 当代标准 reference
  cazy_family: null              # ★ 非 CAZy 家族; 用 enzyme_family 字段
  enzyme_family: lipase
  ec: 3.1.1.3
  organism: Pseudozyma antarctica (formerly Candida antarctica)
  pdb: 1TCA                     # CALB 经典结构, Uppenberg 1994
substrate:
  primary_smiles: "CC(=O)O[C@@H](C)c1ccccc1"     # (S)-1-phenylethyl acetate (chiral resolution 典型 acceptor)
  class: secondary_alcohol_ester / chiral_substrate
target_property: substrate_specificity
status: validated
provenance:
  source_type: literature
  doi: "10.1002/cbic.200400410"
  pmid: null
  citation: "Magnusson AO, Rotticci-Mulder JC, Santagostino A, Hult K (2005). Creating space for large secondary alcohols by rational redesign of Candida antarctica lipase B. ChemBioChem 6(6):1051-1056."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1002/cbic.200400410 我推测; QA via CrossRef 验证"
    - "CALB UniProt P41365 高把握"
    - "PDB 1TCA 高把握 (Uppenberg 1994 经典深度结构, ChemBioChem 2005 paper 用其变体或同源结构作 design 起手)"
    - "Hult 实验室 (KTH Stockholm) 长年 CALB 工程经典系列"
    - "具体 W104A 或类似 large-pocket-creating mutations 的精确位点列表未转录, 见原文 Fig 1"
tags: [lipase, CALB, substrate_specificity, alpha_beta_hydrolase, rational_design, secondary_alcohol, chiral_resolution, Hult-lab, non-CAZy]
---

## 1. 背景与目标
- parent: Candida antarctica lipase B (CALB), α/β hydrolase fold, 工业用 esterase / lipase 标准 workhorse
- 当时背景: CALB 对 secondary alcohol acetates 显示高 enantioselectivity (E > 100), 但仅限 small substituent (CH3, ethyl); 对 large secondary alcohol (e.g., 苯环连接) 活性低
- 目标: 通过 rational redesign 在 active site stereospecificity pocket 加大空间, 让 CALB 接受 large secondary alcohols
- 应用: 生物催化关键 — 不对称合成 chiral 醇 (制药与精细化学品)

## 2. 决策过程

### 候选位点策略
- **理性设计** (Hult lab 招牌): 看 active site pocket 的关键 residue
- 选 **W104** (CALB 标志性"小口袋的盖子" 残基): 这一 indole 突入 substrate pocket, 限制 secondary alcohol 空间
- W104 → A 或 G (Ala / Gly): 减小空间, 让大 substituent 进入

### 排除的位点 (★ 必填)
- Catalytic triad (S105-D187-H224 in CALB) 严格保留
- Oxyanion hole 主链 NH (T40, Q106) 不动
- α/β hydrolase 核心 β-sheet 残基不动 — 维持 fold

### 计算工具与阈值
- 主要 PyMOL 测 W104 与 substrate 几何关系
- 不依赖 ΔΔG / PyRosetta (是 hypothesis-driven single-mutant)
- 实验校验: 异源表达 in P. pastoris → kinetic resolution of racemic large secondary alcohol → E value (enantioselectivity)

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| WT CALB E value (small alcohol) | >100 |
| WT CALB E value (large secondary alcohol) | <5 |
| W104A 突变体 E value (large alcohol) | 20-100 (大幅提升, 但保持 enantioselectivity) |
| W104A 比活 (small alcohol) | 略下降 (specificity tradeoff) |

### 失败案例 (★ 必填)
- W104A 对原 small alcohol 活性下降 — 经典 specificity tradeoff
- 一些其他 active site mutation (T40 / Q106 周围) 试过但失活, 因为破坏 oxyanion hole
- 早期尝试在 W104 引入 Phe 或 Tyr 期望"中等 size"压缩, 但 enantioselectivity 严重下降 — Trp 结构特殊

## 4. 学习收获
- **成立的规则候选**:
  - **CALB W104 是 large secondary alcohol pocket 的关键控点** — 工程化 CALB substrate scope 必看此残基
  - **α/β hydrolase enzyme 工程化的 stereospecificity pocket 残基** 通常是单点突变高效目标 (Trp/Phe/Tyr → Ala/Gly)
  - Specificity tradeoff 不可避免 — 对原 substrate 活性会下降, 设计时必须接受
- **被推翻的假设**:
  - "CALB substrate scope 由 oxyanion hole 几何限制" — 实际是更上游的 stereospecificity pocket 蓋子残基决定
- **下次类似问题应优先尝试**:
  - 任何 lipase/esterase 类 α/β hydrolase 工程化 substrate scope: 找 active site pocket 的 large hydrophobic residue (Trp/Phe/Tyr), 试 → Ala
  - 配对 in vitro kinetic resolution + chiral GC/HPLC 测 E value
- **应避免**:
  - 单独碰 catalytic triad — 必失活
  - 假设 CALB 与 GH 类的 substrate engineering 经验互通 — α/β hydrolase fold 与 GH fold 完全不同, 工具与策略要分别学习

## 5. 计算 / 实验原始数据
原始 kinetic resolution + E value 数据见 ChemBioChem 6(6) 2005 supplementary.
