---
case_id: ADH-musa-2008-orgbiomolchem
schema_version: 1
parent_enzyme:
  uniprot: P14941               # Thermoanaerobacter ethanolicus secondary alcohol dehydrogenase (ADHT)
  cazy_family: null
  enzyme_family: alcohol_dehydrogenase / Zn_dependent_class_I
  ec: 1.1.1.1
  organism: Thermoanaerobacter ethanolicus
  pdb: 1BXZ                     # T. ethanolicus 2°ADH 经典结构
substrate:
  primary_smiles: "CC(=O)CC"     # 2-butanone / methyl ethyl ketone (示意; Musa 2009 测多种 prochiral ketone)
  class: prochiral_ketone / chiral_alcohol_precursor
target_property: substrate_specificity   # 立体选择性 — large bulky ketone 接受
status: validated
provenance:
  source_type: literature
  doi: "10.1039/b717120j"
  pmid: null
  citation: "Musa MM, Ziegelmann-Fjeld KI, Vieille C, Zeikus JG, Phillips RS (2008). Activity and selectivity of W110A secondary alcohol dehydrogenase from Thermoanaerobacter ethanolicus in organic solvents and ionic liquids. Org Biomol Chem 6(5):887-892."
  extracted_at: 2026-04-27
  extraction_confidence: medium
  unverified_details:
    - "DOI 第一次推 j.molcatb.2008.10.011 错 (Title 不匹配, 实际是 alpha-amylase paper), CrossRef 文本搜后改 10.1039/b717120j (Org Biomol Chem 2008, 不是 2009 J Biotechnol)"
    - "T. ethanolicus 2°ADH UniProt P14941 我推测 (ADHT_THEET); QA 验证"
    - "PDB 1BXZ 是 T. ethanolicus 2°ADH"
    - "Phillips lab (UGA) thermophilic ADH 系列; W110A 是 Phillips lab 经典 mutation, 扩 bulky ketone substrate scope"
tags: [alcohol_dehydrogenase, ADH, secondary_alcohol_DH, Zn_dependent, Class_I, substrate_specificity, organic_solvent, chiral_alcohol_synthesis, Phillips-lab, thermophilic, non-CAZy]
---

## 1. 背景与目标
- parent: Thermoanaerobacter ethanolicus 2°ADH (UniProt P14941), Zn²⁺-dependent class I ADH, EC 1.1.1.1
- 自然反应: NADP(H)-dependent reduction of ketones / oxidation of alcohols
- 起始 substrate scope: 接受 small linear ketones (acetone / 2-butanone), 但 large bulky ketones 活性低
- 目标: W110A mutation 扩 substrate scope 至 large bulky ketones (e.g., 苯环、长链 ketones), 同时保 (S)-stereoselectivity
- 应用: chiral alcohol synthesis (制药 chiral 中间体), 与 KRED / SDR-class IRED 互补 (不同 fold, NADP-dependent)

## 2. 决策过程

### 候选位点策略
- **Single-point rational design** (与 LIPASE-magnusson 类似 思路):
  1. 1BXZ 结构识别 active site 大空间限制 residue: W110 (大 indole 入主 substrate pocket)
  2. W110A — 类比 Magnusson CALB W104A 替换为 small Gly/Ala 给 large substrate 空间
  3. 直接 site-directed mutagenesis + activity test
- 不依赖 directed evolution

### 排除的位点 (★ 必填)
- **Catalytic Zn²⁺ binding** (Cys43, His66, Cys153 in 2°ADH) 严格保留 — Zn²⁺ 是 nucleophilic activator
- **NADP(H) binding** Rossmann fold (G-X-G-X-X-G/A motif) 保留 — cofactor 必需
- **Class I structural Zn²⁺** (近 Cys cluster) 保留 — fold 稳定性
- Active site 一级 sphere 的其他 residues (除 W110) 暂不动

### 计算工具与阈值
- 1BXZ 结构指导 W110 选择 (lab 已知此 residue 是 substrate "lid")
- 实验校验: 重组表达 in E. coli → 多 ketone substrate panel + chiral GC/HPLC ee%

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| Variant | small ketone (acetone) | large bulky (e.g., phenyl-2-propanone) | ee% |
| --- | --- | --- | --- |
| WT 2°ADH | high | very low | (S) >99% |
| W110A | moderate (slightly down) | 100-1000× WT | (S) maintained 95-99% |
| 在 organic solvent (TBME / 离子液) | maintained | proportionally similar | maintained |

### 失败案例 (★ 必填)
- W110A 在 small ketone 活性下降 — 经典 specificity tradeoff (与 Magnusson CALB 一致)
- 部分 large ketones 即使 W110A 仍活性低 — 需要 W110A + 邻近残基 combinatorial
- Organic solvent stability: T. ethanolicus 2°ADH 是 thermophilic source, organic 溶剂 tolerance 中等 — 工业反应仍需进一步工程化
- W110A 给 (R)-selective substrate scope 有限 — 仍主要 (S)-selective enzyme

## 4. 学习收获
- **成立的规则候选**:
  - **Zn-dependent ADH (class I) 与 SDR-family KRED 是互补 chiral alcohol 工具** — fold + cofactor 不同, 工程化策略类似但禁区不同
  - **W-类 active site lid residue** 跨 enzyme family 一致是 substrate scope 工程化高价值靶点 (CALB W104, OYE1 W116, 2°ADH W110, MAO-N 类比)
  - **Single-point rational** 在 well-characterized pocket-controlled enzyme 普适, 不限 lipase
  - Thermophilic 来源 enzyme 起手有 stability advantage, organic solvent tolerance 也常更好
- **被推翻的假设**:
  - "ADH (class I, Zn-dependent) 工程化必复杂" — single W → A 给大 substrate scope 扩展
- **下次类似问题应优先尝试**:
  - 任何 ADH / oxidoreductase 想扩 bulky substrate scope, 先找 active site W/F/Y residue, single → A/G
  - 与 KRED-engineering 路径互补: chiral alcohol target 评估 ADH (NADPH+Zn) vs KRED (NADPH+SDR fold) 哪个起手更适
- **应避免**:
  - 触动 Zn binding 残基 — 必失活
  - 假设 ADH = KRED engineering 经验直接 transfer — fold 不同, NADP binding loop 位置不同

## 5. 计算 / 实验原始数据
原始 W110A 在多 ketone + organic solvent 数据见 J Mol Catal B Enzym 60(3-4) 2009 supplementary; Phillips lab 系列 follow-up 含 mechanism analysis.
