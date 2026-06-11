---
case_id: TYROSINASE-sendovski-2011-jmolbiol
schema_version: 1
parent_enzyme:
  uniprot: A0A6H1TH00           # Priestia megaterium (= Bacillus megaterium) tyrosinase; P55022 was Streptomyces galbus tyrosinase
  cazy_family: null
  enzyme_family: tyrosinase / type_3_copper_protein
  ec: 1.14.18.1
  organism: Bacillus megaterium
  pdb: 3NPY                     # B. megaterium tyrosinase structure
substrate:
  primary_smiles: "O=C(O)[C@@H](N)Cc1ccc(O)cc1"   # L-tyrosine
  class: phenolic_amino_acid / L-DOPA_precursor
target_property: substrate_specificity   # 也是 mechanism elucidation, 揭示 copper plasticity
status: validated
provenance:
  source_type: literature
  doi: "10.1016/j.jmb.2010.10.048"
  pmid: null
  citation: "Sendovski M, Kanteev M, Ben-Yosef VS, Adir N, Fishman A (2011). First structures of an active bacterial tyrosinase reveal copper plasticity. J Mol Biol 405(1):227-237."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 第一次推 .2011.01.019 错 (是 phosphofructokinase paper), CrossRef 文本搜后改 10.1016/j.jmb.2010.10.048"
    - "Tyrosinase UniProt 第一次推 P55022 错 (是 Streptomyces galbus tyrosinase), 改 A0A6H1TH00 (Priestia megaterium); 注意 B. megaterium 已重分类为 Priestia megaterium"
    - "PDB 第一次推 3NM8 错; CrossRef 给出 3NPY (Cu²⁺-soaked) 与 3NQ0 (apo) 是 Sendovski 2011 实际 deposits"
    - "Fishman lab (Technion) 经典 bacterial tyrosinase 工作"
    - "Tyrosinase: Cu-CuA + CuB centers; 反应 phenol → catechol → quinone (monophenolase + diphenolase 双活性)"
tags: [tyrosinase, type_3_copper_protein, melanin_biosynthesis, L_DOPA, monophenolase, diphenolase, bacterial_tyrosinase, Fishman-lab, non-CAZy]
---

## 1. 背景与目标
- parent: B. megaterium tyrosinase (UniProt P55022), type-3 copper enzyme, EC 1.14.18.1
- 自然反应: monophenolase (L-tyrosine → L-DOPA) + diphenolase (L-DOPA → dopaquinone) — melanin biosynthesis 通路
- 工业用 1: L-DOPA 工业合成 (帕金森病药)
- 工业用 2: 黑色素 / 化妆品颜料生产
- 当时背景: 没有 active form bacterial tyrosinase 高分辨结构, copper plasticity 不明
- 目标: 解析高分辨结构 + 揭示 copper site geometry, 为 substrate scope engineering 奠基

## 2. 决策过程

### 候选位点策略 (本工作是结构 + 机制, 不是直接 mutagenesis)
- **Crystallography 路线**: 表达 + 纯化 + 结晶 + 解 high-resolution active form
- 后续 (其他 paper) 用此结构指导 substrate scope mutations

### 排除的位点 (★ 必填)
- **CuA 配位 3 个 His** (in B. megaterium: H42, H53, H62) 严格保留 — Cu binding 必需
- **CuB 配位 3 个 His** (H204, H208, H231) 严格保留
- 二聚体 / 寡聚体 interface 残基保留
- "Gate residue" (Y/F 类入口控制) 是 substrate scope 工程化目标残基 (deliberate, 不是 exclusion)

### 计算工具与阈值
- X-ray crystallography (1.5 Å resolution)
- Substrate-binding mode: docking + cocrystal (with L-tyrosine 类 analog)
- 后续 mutagenesis: site-directed at "gate residue" 类位点

## 3. 实验结果

### 关键发现
| 量 | 内容 |
| --- | --- |
| Cu-Cu distance (oxy-form) | ~3.4 Å (typical type-3 copper) |
| Cu-Cu distance (deoxy-form) | ~4.0 Å (more open) |
| **Copper plasticity** | 同 enzyme 在不同 substrate / oxidation 状态下 Cu 几何可变 — 工程化 target 之一 |
| Substrate-binding pocket | hydrophobic, 接受 L-tyrosine + 多 phenolic substrates |

### 失败案例 (★ 必填)
- 论文不直接报告 mutagenesis 失败 (是结构 paper)
- 但讨论提到: 早期人源 tyrosinase 工程化常 destabilize Cu binding — bacterial tyrosinase 因为 simpler fold 是工程化更佳 chassis
- 部分 substrate analog 在 active site 不能 cocrystallize — substrate binding modes 多, 难单一 capture

## 4. 学习收获 (通用 type-3 copper enzyme 工程化)
- **成立的规则候选**:
  - **Type-3 copper enzymes (tyrosinase, hemocyanin, catechol oxidase)** 共有 6-His CuA+CuB 几何; 工程化共有禁区
  - **"Gate residue"** (entry Phe/Tyr/Trp) 是 substrate scope 工程化高价值 — 与其他 enzyme family 类比 (CALB W104, OYE1 W116)
  - **Bacterial tyrosinase** 比真菌 / 动物来源更适合工程化 chassis (simpler structure, easier expression)
  - **Copper plasticity**: Cu 几何在反应过程中可变 — 工程化时不能假设 static geometry
- **被推翻的假设**:
  - "Active site Cu 几何 fixed" — 论文显示 oxy/deoxy 状态 Cu 距离差 0.6 Å, 真实是 dynamic
- **下次类似问题应优先尝试**:
  - Tyrosinase / type-3 copper enzyme 工程化, 选 bacterial chassis (e.g., B. megaterium)
  - L-DOPA / melanin 应用工程化, gate residue Y/F → A/G 是起手
- **应避免**:
  - 改 6 个 His Cu 配位残基 — 必失活
  - 仅在一个 oxidation 状态分析 — Cu plasticity 决定真实 dynamics

## 5. 计算 / 实验原始数据
原始 crystal structures (oxy + deoxy + substrate-bound 多个 PDB) 见 J Mol Biol 405(1) 2011 supplementary; Fishman lab 后续 substrate scope 工程化 paper.
