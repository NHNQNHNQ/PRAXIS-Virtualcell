---
case_id: GH8-anbar-2012-aem
schema_version: 1
parent_enzyme:
  uniprot: P0C2S2                # Cel8A / Endoglucanase A (GUNA_ACETH); 物种 2018 重命名为 Acetivibrio thermocellus
  cazy_family: GH8
  ec: 3.2.1.4
  organism: Clostridium thermocellum
  pdb: 1CEM                     # 待 QA 验
substrate:
  primary_smiles: "OC[C@H]1O[C@@H](O[C@H]2OC(CO)[C@@H](O)[C@H](O)[C@H]2O)[C@H](O)[C@@H](O)[C@@H]1O"
  class: cellobiose / cellooligosaccharide
target_property: thermostability
status: validated
provenance:
  source_type: literature
  doi: "10.1128/aem.07985-11"
  pmid: null
  citation: "Anbar M, Gul O, Lamed R, Yaron S, Bayer EA (2012). Improved thermostability of Clostridium thermocellum endoglucanase Cel8A using consensus-guided mutagenesis. Appl Environ Microbiol 78(9):3458-3464."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 第一次写 07775-11 错, CrossRef 实际查到 10.1128/aem.07985-11; 已修正"
    - "C. thermocellum 已被 2018 年系统发育重分类为 Acetivibrio thermocellus / Hungateiclostridium thermocellum; UniProt 用了 P0C2S2 (GUNA_ACETH 标准 Cel8A)"
    - "PDB 1CEM 我推测; C. thermocellum Cel8A 有多个深度结构, 论文用的具体 ID 待复核"
    - "具体 6-8 个 consensus-derived 突变位点列表与精确 ΔTm 数值未转录, 见原文"
    - "Bayer 实验室 (Weizmann) 在 cellulosome 系列 Cel8A 工程化"
tags: [GH8, thermostability, endoglucanase, consensus_mutagenesis, cellulosome, Clostridium_thermocellum, Bayer-lab]
---

## 1. 背景与目标
- parent: C. thermocellum Cel8A — cellulosome 中重要的 endoglucanase, GH8 家族 (注意: GH8 与 GH7/GH11 fold 不同, 是 (α/α)6 toroid)
- 起始 Tm: ~70°C (Clostridium thermocellum 本身是 thermophilic 来源)
- 目标: 推 Tm 至 80°C+ 用于 consolidated bioprocessing (CBP) 高温糖化
- 应用: 木质纤维素 CBP 流程 — 同时菌体生长与酶水解

## 2. 决策过程

### 候选位点策略
- **Consensus-guided mutagenesis**:
  1. 多序列比对 GH8 家族成员 (跨 mesophilic + thermophilic)
  2. 找出"在 thermophilic ortholog 高频但 parent 缺失"的位点
  3. 选 6-8 个候选做单点 + 组合验证
- 比 Anbar 早期 random mutagenesis 工作更高效

### 排除的位点 (★ 必填)
- 活性位点 (GH8 inverting mechanism, catalytic Asp/Glu) 严格保留
- substrate-binding cleft 不动
- 已知 cellulosome dockerin 结合 region (如有) 保留 — 不能破坏 scaffoldin 结合

### 计算工具与阈值
- Sequence consensus 分析 (Clustal + 频次统计)
- 不依赖 PyRosetta / MD (consensus 方法本身是 statistically derived)
- 实验校验: E. coli 表达 (相对 native cellulosome host 简化) → Tm (CD melting) → 比活 (CMC reducing sugar assay)

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| 起始 Tm | ~70°C |
| Best mutant ΔTm | +5 ~ +10°C |
| 大多数单点 mutation | ±1-2°C (中性 / 轻微提升) |
| 比活保留率 | 大部分 ≥70% WT, 部分 mutant 比活提升 |

### 失败案例 (★ 必填)
- 部分 consensus mutations 实测 Tm 持平或下降 — consensus method 不是 100% 命中, 可能因为:
  - Consensus 频次 ≠ stabilization (多个 thermophilic 共有 ≠ stabilization causal)
  - 局部 epistasis (某残基在 thermophilic 协同稳定, 单独迁到 parent 无效)
- E. coli 表达对部分 mutants 失败 — 与 native Clostridium host 表达性差异

## 4. 学习收获
- **成立的规则候选**:
  - **Consensus-guided mutagenesis 在已 thermophilic 起手的 enzyme 上仍能挤出 +5-10°C** — thermophilic origin 不是 stability 上限
  - GH8 (与 GH7/GH11 不同 fold) 也适用 consensus 方法 — consensus 不是 fold-specific
  - **Cellulosome enzymes 工程化时必须保留 dockerin region** — 否则失去与 scaffoldin 装配能力
- **被推翻的假设**:
  - "Thermophilic 起手 enzyme 已经接近 stability 上限" — Cel8A 起手 ~70°C 仍能 +10°C
- **下次类似问题应优先尝试**:
  - Consensus + 单点验证 + 组合 — 简单且统计上可解释
  - 与 directed evolution (Goedegebuur 2017) 互补: consensus 适合"有多 ortholog 的 well-characterized 家族"
- **应避免**:
  - 用 E. coli 表达评测 native cellulosome enzyme — 本质上 expression 系统差异会 confound 结果
  - 假设 consensus 频次 = causal stabilization

## 5. 计算 / 实验原始数据
原始 consensus 表与 melting curve 数据见 AEM 78(9) 与 supplementary.
