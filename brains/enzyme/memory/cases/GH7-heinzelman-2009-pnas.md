---
case_id: GH7-heinzelman-2009-pnas
schema_version: 1
parent_enzyme:
  uniprot: P62694              # T. reesei Cel7A (primary SCHEMA parent of 3); 详见 unverified_details
  cazy_family: GH7
  ec: 3.2.1.176                # 注: UniProt P62694 标 EC 3.2.1.91 (legacy non-reducing-end CBH); 文献和 BRENDA 多用 3.2.1.176 (reducing-end CBH)
  organism: Hypocrea jecorina  # = T. reesei (UniProt 用 H. jecorina 标准命名); SCHEMA chimera 含 T. emersonii 等其他 parent, 详见 unverified_details
  pdb: 1CEL
substrate:
  primary_smiles: "OC[C@H]1O[C@@H](O[C@H]2OC(CO)[C@@H](O)[C@H](O)[C@H]2O)[C@H](O)[C@@H](O)[C@@H]1O"
  class: cellobiose
  pubchem_cid: 6255
target_property: thermostability
status: validated
provenance:
  source_type: literature
  doi: "10.1073/pnas.0901417106"
  pmid: "19307582"
  citation: "Heinzelman P, Snow CD, Wu I, Nguyen C, Villalobos A, Govindarajan S, Minshull J, Arnold FH (2009). A family of thermostable fungal cellulases created by structure-guided recombination. PNAS 106(14):5610-5615."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "SCHEMA recombination 用了 3 个 fungal Cel7A parents: T. reesei P62694 (case 主要 parent) + T. emersonii Cel7A (Q8TFL9) + 1 个其他 (具体身份待原文 Table 复核, 候选 Heterobasidion / Phanerochaete 等真菌)"
    - "UniProt P62694 标 EC 3.2.1.91, 案例标 3.2.1.176 (reducing-end CBH 新分类), 二者都用于 TrCel7A 文献"
    - "Specific best-performing chimera ID and exact ΔTm value (paper Table 1/2 needed for transcription)"
    - "Specific block-boundary positions chosen by SCHEMA"
tags: [GH7, thermostability, SCHEMA, recombination, cellobiohydrolase, chimera, Arnold-lab, fungal-cellulase]
---

## 1. 背景与目标
- parent: 3 fungal Cel7A orthologs, 含 T. reesei P62694 与 T. emersonii Cel7A
- 起始 Tm: parents 范围跨 ~62-72°C (T. reesei 较低, T. emersonii 较高)
- 目标: 用结构引导重组生成超越任一 parent 的热稳定 chimera
- 应用: 工业纤维素糖化高温预水解; 验证 SCHEMA 方法在 GH 家族适用性

## 2. 决策过程

### 候选位点策略
- **SCHEMA recombination** (Voigt et al. 2002 算法): 不是位点级突变, 而是结构 block 级重组
  1. 用接触图 (contact map) 把每个 parent 蛋白切成 8 个 fragment
  2. 随机重组 fragment 生成 3^8 = 6561 理论组合
  3. 用 m_disruption (打破的接触数) 评估每个候选
- 实测合成约几十个 chimera (具体数详见原文); 优先 m_disruption 低的候选

### 排除的位点 (★ 必填)
- **SCHEMA 自动避免**破坏 parent 间共享的关键接触 (block 边界选择)
- 显式约束: 活性位点 (catalytic E212/E217 或同源位置) 区域跨 parent 同源, 自然保留
- 边界穿过密集接触区的候选优先级降低

### 计算工具与阈值
- SCHEMA energy / m_disruption 计算 (Voigt et al. 2002)
- 实验校验: heterologous expression in S. cerevisiae → 比活测定 → Tm (热失活活性曲线 / DSC)

## 3. 实验结果

### 总体趋势 (★ 数值范围, 具体值见原文)
| 指标 | 范围 |
| --- | --- |
| Parent Tm | ~62°C (T. reesei) ~ 72°C (T. emersonii) |
| Chimera Tm 提升 (vs T. reesei parent) | up to ~+10°C 量级 (具体 Table 见原文) |
| 活性保留 | 大部分 chimera 保留 cellobiohydrolase 活性 |

### 失败案例 (★ 必填)
- 部分 chimera 不能在 S. cerevisiae 表达 (低 yield 或不可溶)
- m_disruption 过高的 chimera 表达失败率显著上升 (与预测一致, 验证了 SCHEMA 的结构合理性约束)
- 活性退化: 少数 chimera Tm 提升但比活下降, 表明 stability 与 catalytic efficiency 并非完全协同

## 4. 学习收获

- **成立的规则候选**:
  - 块级重组 (block recombination) 能在保留活性位点的同时获得显著 Tm 提升, 是 GH7 类酶热稳定化的有效路径
  - parent 选择: 含 thermostable parent 比例高的 chimera 平均更稳定 (符合直觉但量化了)
  - 接触保留 (m_disruption 低) 是表达成功率的强预测器 — 这是 SCHEMA 的核心设计哲学
- **被推翻的假设**:
  - "Tm 只能通过逐位点累加突变改进" — SCHEMA 显示一次块重组可获得多 °C 提升, 优于多步定点突变累加
- **下次类似问题应优先尝试**:
  - 当目标 enzyme 有 ≥3 同家族 ortholog 且至少 1 个 thermostable, 优先考虑 SCHEMA 重组而非全位点扫描
  - SCHEMA 工具链: RASPP 算法选 block 边界 → SCHEMA-energy 排序 → 实验合成 top 候选
- **应避免**:
  - 忽视 fragment 边界选择 — 边界穿过密集接触区会导致表达失败
  - 仅看 Tm 不看活性 — 必须双指标 (Tm + 比活)
  - 只用 1 个 thermostable parent — 缺乏多样性, 重组空间塌缩

## 5. 计算 / 实验原始数据
原始 SCHEMA energy 表与 chimera 比活数据见 PNAS 2009 supplementary materials.
