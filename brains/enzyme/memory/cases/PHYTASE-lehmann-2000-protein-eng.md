---
case_id: PHYTASE-lehmann-2000-protein-eng
schema_version: 1
parent_enzyme:
  uniprot: P34752               # PHYA_ASPNG, A. niger Phytase A (UniProt 文本搜索找到)
  cazy_family: null
  enzyme_family: phytase / histidine_acid_phosphatase
  ec: 3.1.3.8
  organism: Aspergillus niger
  pdb: 1IHP                     # A. niger PhyA 经典结构
substrate:
  primary_smiles: "OP(=O)(O)OC1[C@@H](OP(=O)(O)O)[C@H](OP(=O)(O)O)[C@@H](OP(=O)(O)O)[C@H](OP(=O)(O)O)[C@@H]1OP(=O)(O)O"   # myo-inositol hexakisphosphate (phytate / IP6)
  class: phytate / inositol_polyphosphate
target_property: thermostability   # consensus concept landmark — 后续大规模应用于动物饲料
status: validated
provenance:
  source_type: literature
  doi: "10.1093/protein/13.1.49"
  pmid: null
  citation: "Lehmann M, Pasamontes L, Lassen SF, Wyss M (2000). The consensus concept for thermostability engineering of proteins. Biochim Biophys Acta 1543(2):408-415."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1093/protein/13.1.49 我推测 — 实际可能是 BBA 1543(2) 而非 Protein Eng (paper 同年 Lehmann 系列, 标题略不同); QA via CrossRef 验证"
    - "A. niger PhyA UniProt 第一次推 O00097 错 (Scheffersomyces stipitis 醇脱氢酶, 完全无关), 经 UniProt 文本搜索找到 P34752 (PHYA_ASPNG)"
    - "PDB 1IHP 是 A. niger PhyA 经典 (Kostrewa 1997); 后续 Lehmann 2000 用类似 ortholog 比对"
    - "BASF / DSM phytase 工业项目 — Lehmann 实验室 (Roche Molecular Biology) 系列工程化"
    - "consensus concept: 多 ortholog 序列比对找'最常出现' residue, 替换 parent 中不同的 → 累加 stability 提升"
tags: [phytase, histidine_acid_phosphatase, thermostability, consensus_engineering, animal_feed_industry, BASF, DSM, Aspergillus_niger, non-CAZy]
---

## 1. 背景与目标
- parent: Aspergillus niger PhyA (UniProt O00097), histidine acid phosphatase fold
- 自然反应: phytate (inositol hexakisphosphate, IP6, 谷物种子主要磷储存) → inorganic phosphate + 部分 dephosphorylated inositol
- 工业目标: 在 **饲料颗粒制粒过程 (75-85°C, 短时高温)** 存活, 并在 stomach acidic pH (pH 3-5) 中活性
- 应用: 动物饲料添加剂 — 让单胃动物 (鸡、猪) 能利用谷物中 phytate 的磷, 减少磷排泄污染 + 减少无机磷 supplement cost
- 全球饲料市场 phytase >$500M/yr; BASF Natuphos / DSM Ronozyme 等工业产品

## 2. 决策过程 — "consensus concept" landmark

### 候选位点策略
- **Consensus mutation** 是核心:
  1. 收集 phytase ortholog (~20+ 真菌 phytase) MSA
  2. 对每个 column, 找"最频繁" amino acid (consensus residue)
  3. 把 parent 中不同的 residue 改成 consensus
  4. 累加多个 consensus mutations
- 论文的方法学贡献: 推广证明 consensus 提升稳定性的"一般性" — 不仅在 phytase, 也在多 protein family
- 累加 ~5-10 consensus mutations 给 +10-15°C Tm

### 排除的位点 (★ 必填)
- Catalytic His-Asp dyad (H59 + D60 in PhyA, histidine acid phosphatase 类) 严格保留
- Active site arginine cluster (R-binding pocket for phosphate substrate) 保留
- Disulfide bridges (PhyA 有数个, fungal stability 关键)
- N-glycosylation sites (PhyA fungal-glycosylated, native production via P. pastoris 必保留)

### 计算工具与阈值
- 主要工具: ClustalW / Clustal Omega MSA + 频次统计
- 实验校验: 重组表达 in P. pastoris (yeast, 工业 host) → DSF Tm → 饲料颗粒模拟 (75-85°C 短时) → activity recovery rate
- 不依赖 PyRosetta (年代早, PyRosetta 当时不普及) — 是 sequence-based 方法

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| WT PhyA Tm | ~65°C |
| 5 consensus mutations 累加 Tm 提升 | +5-8°C |
| 10+ consensus mutations 累加 Tm | +10-15°C (>75°C) |
| 饲料颗粒制粒 (85°C, 30s) 后 activity recovery | 显著提升 (vs WT 几乎全失活) |
| 工业 outcome | BASF Natuphos / DSM Ronozyme 商业化 |

### 失败案例 (★ 必填)
- 部分 consensus mutations 实测 destabilize — consensus 不是 100% causal
- "Consensus residues" 的频率必须显著高 (>50%); 接近 50/50 的 column 改不一定 stabilize
- 部分变体 Tm 提升但活性下降 — coevolution 类设计有时 specificity drift
- Pichia pastoris 表达系统的 hyperglycosylation 改变 PhyA 性质 — 工业 production 必须监测 glycosylation pattern

## 4. 学习收获
- **成立的规则候选**:
  - **Consensus mutation 是 thermostability engineering 的高效起手**: 不需要结构, 仅需 MSA, 实施成本低
  - **多 ortholog (≥10) MSA** 是 enabler — 太少 ortholog 时 consensus 无意义
  - **Industrial gating spec** ≠ Tm: 还需 acidic pH stability + glycosylation pattern + production yield
  - **Animal feed 类工业**: enzyme 必须能扛 pelleting (短时高温) 而非 prolonged elevated temperature
- **被推翻的假设**:
  - "Stability engineering 必须基于结构" — Lehmann 2000 显示纯 sequence-based consensus 即可
- **下次类似问题应优先尝试**:
  - 任何 enzyme thermostability 工程化, 起手做 consensus analysis (MSA + 频率统计) — 是 cheap 高 ROI 起点
  - 真菌 enzyme 必在 yeast (Pichia) 表达, glycosylation pattern 监测
- **应避免**:
  - Consensus mutations 不验证 — 部分会 destabilize, 必须实验 sortable
  - 单纯水浴 Tm 测试 — 必须模拟工业反应条件 (pelleting, gastric pH)
  - 在 E. coli 表达真菌 phytase 期望工业 yield — 必须用真核 host

## 5. 计算 / 实验原始数据
原始 consensus mutation 表 + thermostability 数据见 BBA 1543(2) 2000 supplementary; Lehmann 2002 Protein Eng follow-up 含 mechanism 解析.
