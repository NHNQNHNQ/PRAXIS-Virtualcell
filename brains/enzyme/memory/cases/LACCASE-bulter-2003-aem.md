---
case_id: LACCASE-bulter-2003-aem
schema_version: 1
parent_enzyme:
  uniprot: Q12717               # Trametes versicolor laccase 1 (Lcc1)
  cazy_family: null
  enzyme_family: laccase / multicopper_oxidase
  ec: 1.10.3.2
  organism: Trametes versicolor
  pdb: 1KYA                     # T. versicolor laccase
substrate:
  primary_smiles: "Oc1ccccc1"    # phenol (示意; laccase 接受 broad phenolic substrate panel)
  class: phenolic_compound / lignin_model
target_property: activity        # heterologous expression efficiency + activity in S. cerevisiae
status: validated
provenance:
  source_type: literature
  doi: "10.1128/aem.69.2.987-995.2003"
  pmid: null
  citation: "Bulter T, Alcalde M, Sieber V, Meinhold P, Schlachtbauer C, Arnold FH (2003). Functional expression of a fungal laccase in Saccharomyces cerevisiae by directed evolution. Appl Environ Microbiol 69(2):987-995."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1128/aem.69.2.987-995.2003 高把握 (Frances Arnold lab classic)"
    - "T. versicolor Lcc1 UniProt Q12717 我推测; QA 验证"
    - "PDB 1KYA 是 T. versicolor 类 laccase 结构; 论文用其变体"
    - "Arnold lab + Sieber 经典 directed evolution 论文 — laccase 在 yeast 表达 170× 提升"
tags: [laccase, multicopper_oxidase, fungal_enzyme, directed_evolution, heterologous_expression, S_cerevisiae, pulp_bleaching, dye_decoloration, Arnold-lab, non-CAZy]
---

## 1. 背景与目标
- parent: Trametes versicolor laccase Lcc1 (UniProt Q12717), multicopper oxidase, EC 1.10.3.2
- 自然反应: 氧化 phenolic / aromatic 化合物, 同时 reduce O₂ → H₂O (4-electron transfer)
- 工业用: pulp bleaching, 染料 decoloration, lignin 修饰, biosensors
- 当时 problem: 真菌 laccase 在 S. cerevisiae 表达不可溶 / yield 极低; 工业生产难
- 目标: 通过 directed evolution 让 laccase 在 yeast 高 yield 表达 + 活性维持

## 2. 决策过程

### 候选位点策略
- **Directed evolution** (Arnold lab 招牌):
  1. 起始 Lcc1 在 S. cerevisiae 几乎无活性
  2. Error-prone PCR 文库 + GAL1 promoter
  3. ABTS-based colorimetric activity screen (96-well plate)
  4. ~10 rounds, 累积 ~10 mutations
  5. 最终 variant 比 WT 表达 ~170× 提升

### 排除的位点 (★ 必填)
- **4 Cu sites** (T1, T2, T3α, T3β) 的配位 His + Cys 严格保留 — multicopper center 核心
- Cysteine bridge (T1 site Cys) 不动
- Substrate-binding "T1 pocket" 不主动改 (会改 substrate scope)
- Glycosylation sites (laccase 多 N-glycosylation, S. cerevisiae 表达常 hyperglycosylate)

### 计算工具与阈值
- High-throughput screen: ABTS oxidation in 96-well plate
- 不依赖前期结构指导 — 直接 random mutagenesis + selection
- 实验校验: yeast 表达 → 培养基 supernatant 测 activity → 顶级 hits 纯化 + sequence

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| WT Lcc1 yeast yield | 几乎不可检测 |
| Evolved variants yield | 170× WT (yeast supernatant ABTS activity) |
| 累加 mutations | ~10 |
| Mutations 分布 | mostly surface + signal peptide 区, 不在 Cu-binding 1° sphere |
| Catalytic activity (per enzyme) | 维持 |

### 失败案例 (★ 必填)
- Multiple rounds 早期 rounds yield 改善但 specific activity 下降 — 必须 dual-screen
- Hyperglycosylation 部分变体: yeast 给 laccase 过量糖基化, 反而降低活性
- 部分高 yield variants 在 buffer 中聚集 — surface 工程化的副作用
- 同源 laccase (其他 Trametes / Pleurotus) 用同方法表达不一定 transfer — yeast host 偏好高度 sequence-dependent

## 4. 学习收获
- **成立的规则候选**:
  - **真菌 enzyme 在 yeast (P. pastoris / S. cerevisiae) 异源表达** 是工程化关键瓶颈, directed evolution 在 yeast host context 内做最有效
  - Multicopper oxidase (laccase / ascorbate oxidase / bilirubin oxidase 等) 共有 Cu site 严格保留原则
  - **Surface mutations + signal peptide 工程化** 是 yeast 表达提升的主要 zone (避开 Cu sites + active site)
  - "Evolution in the host" 范式: 表达 host 改变 → 工程化必须在该 host 内重做
- **被推翻的假设**:
  - "WT enzyme should express in any host" — yeast vs native fungal host 表达差距 100×+ 是常态
- **下次类似问题应优先尝试**:
  - 任何 fungal enzyme 工业化, 评估目标 host 表达 yield, 必要时 directed evolution
  - High-throughput colorimetric assay (ABTS / DMP / syringaldazine for oxidases) 是 enabler
- **应避免**:
  - 改 Cu site 配位残基 — 必失活
  - 假设 yeast 表达 yield 与 native fungal host 等价

## 5. 计算 / 实验原始数据
原始 evolved variants + yeast expression 数据见 Appl Environ Microbiol 69(2) 2003 supplementary.
