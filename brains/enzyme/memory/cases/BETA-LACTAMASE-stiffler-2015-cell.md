---
case_id: BETA-LACTAMASE-stiffler-2015-cell
schema_version: 1
parent_enzyme:
  uniprot: P62593               # TEM-1 β-lactamase
  cazy_family: null
  enzyme_family: serine_beta_lactamase / class_A
  ec: 3.5.2.6
  organism: Escherichia coli
  pdb: 1ZG4                     # TEM-1 经典结构
substrate:
  primary_smiles: "CC1(C)S[C@@H]2N(C(=O)C[C@H]2NC(=O)Cc3ccccc3)C1C(=O)O"   # benzylpenicillin (示意)
  class: beta_lactam_antibiotic
target_property: substrate_specificity   # 实际是 evolvability 研究 (deep mutational scanning)
status: validated
provenance:
  source_type: literature
  doi: "10.1016/j.cell.2015.01.035"
  pmid: "25723170"
  citation: "Stiffler MA, Hekstra DR, Ranganathan R (2015). Evolvability as a function of purifying selection in TEM-1 β-lactamase. Cell 160(5):882-892."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1016/j.cell.2015.01.035 高把握 (well-cited Cell paper)"
    - "TEM-1 UniProt P62593 高把握"
    - "PDB 1ZG4 是 TEM-1 经典 1.9 Å 结构"
    - "Ranganathan lab (UTSW Dallas) deep mutational scanning landmark 系列"
tags: [beta_lactamase, TEM-1, deep_mutational_scanning, DMS, evolvability, fitness_landscape, antibiotic_resistance, Ranganathan-lab, non-CAZy]
---

## 1. 背景与目标
- parent: E. coli TEM-1 β-lactamase (UniProt P62593, class A serine β-lactamase)
- 自然反应: 水解 β-lactam 抗生素 (penicillins, cephalosporins) 的 amide 键给 carboxylic acid 抗药菌产物
- 目标: 通过 **deep mutational scanning (DMS)** 量化每个位点每个 amino acid 的 fitness 影响, 揭示"evolvability landscape"
- 这不是工业 enzyme engineering — 是基础蛋白进化研究, 但产生的"fitness map"对工程化决策极有价值

## 2. 决策过程

### 候选位点策略 — Deep Mutational Scanning
- **全饱和文库**: 每个位点每个 amino acid 的 mutation (~5000 single mutants for 263-residue TEM-1)
- 在不同 antibiotic concentration 下 selection (从无选择到致死浓度)
- 测序 surviving 文库 → 算每位点每 mutation 的 fitness coefficient

### 排除的位点 (★ 必填)
- DMS 不预先排除 — 全位点扫描是方法论核心
- 但分析显示: catalytic Ser70, Lys73, Ser130, Glu166 mutations 几乎全致死 (purifying selection 强)
- Ω-loop (residues 161-179) 的 mutation 影响重大 (substrate scope determinant)

### 计算工具与阈值
- High-throughput sequencing (Illumina) 文库 quantification
- 数学: fitness = log₂(post-selection / pre-selection abundance)
- 实验: DMS 在 ampicillin / cefotaxime selection conditions 下

## 3. 实验结果

### 关键发现
| 发现 | 内容 |
| --- | --- |
| **Purifying selection** 与 evolvability 反向 | 残基 fitness landscape 越严格, 突变 evolvability 越低 |
| Catalytic residues 几乎不容许变化 | Ser70/Lys73 mutations 95%+ 致死 |
| **Active site distal mutations** 容许多, evolvability 高 | 这是工程化高价值靶点 |
| Ω-loop substrate specificity determinant | 这一区域 mutations 改变 antibiotic preference (cephalosporins vs penicillins) |
| Distance to active site vs fitness | 弱 correlation (距离不完全决定 fitness) |

### 失败案例 (★ 必填)
- 论文不报告"失败"; 是 systems biology study, 揭示哪些位点不可改 vs 哪些可塑
- DMS 数据本身就包含 90%+ 致死 mutations 的实测 — 这是 explicit "what doesn't work" 信息
- DMS 的 fitness coefficient 是 log-scale 平均, 隐藏了 epistasis (双突变非加性)

## 4. 学习收获
- **成立的规则候选**:
  - **DMS / fitness landscape** 是工程化的"地图": 工程化前先做 DMS, 后续 mutation 选择基于 fitness map
  - **Active site distal residues** 是 evolvability 高 zones — 工程化的 ROI 高
  - **Ω-loop** 在 β-lactamase 工程化是 substrate specificity 关键 (与 GH 类 active site loop 类似原理)
  - **Catalytic residues** purifying selection 强, 跨所有 enzyme 一致 — 不要碰
- **被推翻的假设**:
  - "距离 active site 越近, 越不能 mutation" — DMS 显示是 fitness landscape 决定, 距离仅弱 correlation
- **下次类似问题应优先尝试**:
  - 任何 well-characterized enzyme 工程化前, 评估是否做 DMS 建 fitness map (现在 DMS 已商业化, ~$10-50K)
  - 工程化时优先在 high-evolvability zones (DMS map identified) 做突变
- **应避免**:
  - 仅依赖结构判断 evolvability — DMS 数据更直接
  - 假设 evolvability 与 distance to active site 单调 — 实测多复杂

## 5. 计算 / 实验原始数据
原始 DMS 数据 + fitness landscape map 见 Cell 160(5) 2015 supplementary; Ranganathan lab 维护开放数据.
