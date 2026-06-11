---
case_id: GH7-voutilainen-2010-prot-eng
schema_version: 1
parent_enzyme:
  uniprot: Q8TFL9              # R. emersonii Cel7A (cbh1 gene); 物种 2011 年由 Talaromyces 重新分类为 Rasamsonia
  cazy_family: GH7
  ec: 3.2.1.176
  organism: Rasamsonia emersonii (formerly Talaromyces emersonii / Penicillium emersonii)
  pdb: 1Q9H                    # T. emersonii Cel7A 结构 (Grassick et al. 2004), 后续 PDB 3PFJ / 3PFX 也属同一蛋白
substrate:
  primary_smiles: "OC[C@H]1O[C@@H](O[C@H]2OC(CO)[C@@H](O)[C@H](O)[C@H]2O)[C@H](O)[C@@H](O)[C@@H]1O"
  class: cellobiose
target_property: thermostability_and_activity   # 论文同时提升 Tm 和活性
status: validated
provenance:
  source_type: literature
  doi: "10.1093/protein/gzp072"
  pmid: "19951961"
  citation: "Voutilainen SP, Murray PG, Tuohy MG, Koivula A (2010). Expression of Talaromyces emersonii cellobiohydrolase Cel7A in Saccharomyces cerevisiae and rational mutagenesis to improve its thermostability and activity. Protein Engineering, Design and Selection 23(2):69-79."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "UniProt 已修正: 原写 Q8TG26 实为 T. aurantiacus 纤维素酶, 应为 Q8TFL9 (R. emersonii cbh1)。修正过程: distill QA 的 uniprot_organism 检查发现 Q8TG26 organism 不匹配 + EC 3.2.1.4 (endoglucanase) 不是 CBH, 后通过 UniProt 文本搜索 Talaromyces emersonii cellobiohydrolase 找到正确 accession。"
    - "Q8TFL9 UniProt 标 EC 3.2.1.- (generic), 文献和 BRENDA 标准为 3.2.1.176 (reducing-end CBH); 案例保留 3.2.1.176"
    - "具体突变位点列表 (论文报告的 5-8 个 rational mutations) 与 ΔTm/Δkcat 数值未完整转录, 见原文"
    - "需要时也参考 Voutilainen et al. 2008 Biotechnol Bioeng (T. emersonii Cel7A 表征), 与本 2010 paper 同一 enzyme 不同 study"
tags: [GH7, thermostability, activity, rational_design, point_mutation, cellobiohydrolase, Talaromyces]
---

## 1. 背景与目标
- parent: R. emersonii Cel7A (历史命名 T. emersonii / TeCel7A; UniProt Q8TFL9; PDB 1Q9H), 来自 thermophilic 真菌的天然较稳定 cellobiohydrolase
- 起始 Tm: ~70°C (R. emersonii 整体偏 thermophilic 来源)
- 目标: 同时提升 Tm (~+5°C 级) 与活性 (kcat 或 specific activity)
- 应用: 在 S. cerevisiae 中表达 (consolidated bioprocessing 重要 host) + 工业糖化

## 2. 决策过程

### 候选位点策略
- **理性设计** (rational mutagenesis), 非随机突变文库
- 基础信息源:
  1. T. emersonii Cel7A 与 T. reesei Cel7A 的序列+结构比对
  2. 已发表的 GH7 thermostability 文献 (e.g., 已知有效突变的迁移)
  3. 表面残基的 RSA + 二级结构 context
- 候选数: 论文报告 5-8 个具体单点 / 双点突变 (具体数详见原文)

### 排除的位点 (★ 必填)
- 活性位点 (catalytic E and 周围 substrate-binding 残基) 严格保留
- 葡萄糖结合 subsite 残基 (-7 ~ +2 along cellulose chain) 不动
- N-glycosylation site (TeCel7A 已知有几个 N-glycosylation, 不变)

### 计算工具与阈值
- 主要靠 sequence/structure 比对与人工判断, 不依赖大型 ΔΔG 扫描
- 实验校验: 在 S. cerevisiae 异源表达 → DSF 或失活活性曲线测 Tm → 4-甲基伞形酮 (4-MUC) 或 cellobiose 活性

## 3. 实验结果

### 总体趋势 (★ 具体数值见原文 Table)
| 指标 | 趋势 |
| --- | --- |
| 单点突变 ΔTm | ±2°C 范围, 部分中性, 少数 +3-5°C 提升 |
| 组合 ΔTm | 累加部分非加性, 总体 +5°C 量级 |
| 比活变化 | 部分 mutation 同时提升活性 (论文核心发现之一) |

### 失败案例 (★ 必填)
- 论文中部分单点 mutation Tm 持平甚至下降 (即 rational design 不是 100% 命中)
- S. cerevisiae 异源表达本身就有 yield 较低问题 (相对 native Trichoderma host); 部分突变体 yield 显著下降
- 文中讨论了"在 S. cerevisiae 中超糖基化" (hyperglycosylation) 可能影响活性测量

## 4. 学习收获

- **成立的规则候选**:
  - 同家族 ortholog 之间已知有效突变可"迁移" (从 T. reesei Cel7A 文献迁到 TeCel7A) — 但命中率不是 100%
  - 单点 rational design 期望值 ~30-50% 命中, 比 saturation library 效率高但样本量小
  - Tm 提升 ≠ 活性下降 必然: 同时优化两者可行 (对 T. emersonii 来说)
- **被推翻的假设**:
  - "thermophilic enzyme 已经接近 stability 上限, 难再提升" — TeCel7A 起始 70°C 仍能再 +5°C
- **下次类似问题应优先尝试**:
  - 跨 ortholog 的 mutation transfer 作为低成本 rational starting set
  - 必带 expression yield 监测, 不能只看 Tm
- **应避免**:
  - 把 S. cerevisiae 测得的活性直接外推到 native host (糖基化差异)
  - 假设 rational design 能完全替代实验筛 — 仍需逐个验证

## 5. 计算 / 实验原始数据
原始数据见 Protein Engineering, Design and Selection 2010 paper 的 Table 1-3.
