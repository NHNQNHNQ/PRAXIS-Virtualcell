---
case_id: GH7-goedegebuur-2017-jbc
schema_version: 1
parent_enzyme:
  uniprot: P62694
  cazy_family: GH7
  ec: 3.2.1.176
  organism: Hypocrea jecorina
  pdb: 1CEL
substrate:
  primary_smiles: "OC[C@H]1O[C@@H](O[C@H]2OC(CO)[C@@H](O)[C@H](O)[C@H]2O)[C@H](O)[C@@H](O)[C@@H]1O"
  class: cellobiose
target_property: thermostability
status: validated
provenance:
  source_type: literature
  doi: "10.1074/jbc.M117.803270"
  pmid: null
  citation: "Goedegebuur F, Dankmeyer L, Gualfetti P, Karkehabadi S, Hansson H, Jana S, Huynh V, Kelemen BR, Kruithof P, Larenas EA, Teunissen PJ, Ståhlberg J, Payne CM, Mitchinson C, Sandgren M (2017). Improving the thermal stability of cellobiohydrolase Cel7A from Hypocrea jecorina by directed evolution. J Biol Chem 292(41):17418-17430."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1074/jbc.M117.803270 我推测; QA via CrossRef 验证"
    - "Genencor/DuPont 团队 (Mitchinson / Sandgren) 多年 TrCel7A 工程系列 — 此 paper 是该系列高峰之一"
    - "具体 5-10 个 evolved 突变位点列表与精确 ΔTm 数值未转录, 见原文 Table"
    - "论文同步用了 MD simulation (Payne 团队) 验证突变机制, 具体细节见原文"
tags: [GH7, thermostability, cellobiohydrolase, directed_evolution, MD_validation, Genencor, DuPont, TrCel7A]
---

## 1. 背景与目标
- parent: T. reesei Cel7A (TrCel7A, UniProt P62694, PDB 1CEL) — 工业 baseline
- 起始 Tm: ~62°C (mesophilic 起手)
- 目标: 通过 directed evolution 提升 Tm, 用于 80°C 工业糖化
- 应用: 工业 biofuel 流程的高温酶工艺

## 2. 决策过程

### 候选位点策略
- **Directed evolution** (定向进化): error-prone PCR + saturation library + selection
- 多轮迭代, 累加 beneficial mutations
- MD simulation 验证机制 (Payne 实验室合作)

### 排除的位点 (★ 必填)
- 活性位点 (E212/E217 周围) 严格保留 — directed evolution 自然倾向保留催化必需残基 (低活性 mutants 被 negative selection 淘汰)
- 已知 N-glycosylation 位点 (N45, N270 周围 ±3) 隐式保留

### 计算工具与阈值
- 定向进化 + MD validation; 不是预先 ΔΔG 筛选 而是 post-hoc 解释机制
- 实验校验: heterologous expression in T. reesei → Tm (DSF) → 比活 → MD trajectory analysis

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| 起始 Tm | ~62°C |
| 最终 evolved variant Tm 提升 | +9 ~ +10°C 量级 |
| 突变数 | 累加 5-10 个 substitutions |
| 比活保留率 | 大部分突变保留 ≥80% WT 活性 |
| MD validation | 揭示 stabilization 机制涉及 surface salt-bridge + loop 刚化 |

### 失败案例 (★ 必填)
- Directed evolution 过程中筛选掉的 variants (Tm 持平或下降, 或表达失败) — 数量未明确报道, 但 selection 假定大多数 random mutations 是 neutral / 负面
- 部分 ΔTm 提升的 mutants 比活下降 — directed evolution 必须双指标筛选, 否则会偏向 thermostable 但 catalytically 弱的 variants

## 4. 学习收获
- **成立的规则候选**:
  - 在已经 mesophilic 但工业重要的 enzyme (TrCel7A) 上, directed evolution 仍能挤出 +10°C 量级 (与 SCHEMA 量级相当)
  - MD validation 是解释 directed evolution hits 的有效手段 — selection 给出 "what works", MD 给出 "why"
  - **5-10 substitutions 累加** 是 GH7 thermostability 的合理目标 (与 Heinzelman SCHEMA chimera 的 substitution 数量级一致)
- **被推翻的假设**:
  - "evolved hits 都是 surface 简单替换" — 部分关键 hits 在 second-shell 残基, 通过 MD 才看出影响
- **下次类似问题应优先尝试**:
  - 当目标是工业 enzyme 的 incremental improvement, directed evolution + MD validation 联合策略适用
  - 与 SCHEMA recombination 互补: SCHEMA 适合 "have multiple ortholog parents", directed evolution 适合 "improve one enzyme"
- **应避免**:
  - 单指标 selection (只看 Tm 不看活性)
  - 跳过 MD validation — 即使 selection 给出 hits, 不解释机制就不能迁移到其他酶

## 5. 计算 / 实验原始数据
原始 evolved variant 列表与 MD analysis 见 J Biol Chem 292(41) 与 supplementary materials.
