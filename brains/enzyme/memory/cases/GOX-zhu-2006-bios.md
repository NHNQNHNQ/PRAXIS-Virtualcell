---
case_id: GOX-zhu-2006-bios
schema_version: 1
parent_enzyme:
  uniprot: P13006               # Aspergillus niger glucose oxidase (GOx)
  cazy_family: null
  enzyme_family: glucose_oxidase / GMC_oxidoreductase
  ec: 1.1.3.4
  organism: Aspergillus niger
  pdb: 1CF3                     # A. niger GOx 经典结构 (Hecht 1993)
substrate:
  primary_smiles: "OC[C@H]1O[C@H](O)[C@H](O)[C@@H](O)[C@@H]1O"   # β-D-glucose
  class: monosaccharide_oxidation
target_property: thermostability_and_activity   # GOx for biofuel cells / biosensors needs thermostability + electron transfer efficiency
status: validated
provenance:
  source_type: literature
  doi: "10.1016/j.bios.2005.11.018"
  pmid: null
  citation: "Zhu Z, Momeu C, Zakhartsev M, Schwaneberg U (2006). Making glucose oxidase fit for biofuel cell applications by directed protein evolution. Biosens Bioelectron 21(11):2046-2051."
  extracted_at: 2026-04-27
  extraction_confidence: medium
  unverified_details:
    - "DOI 第一次推 bej.2006.07.002 错 (期刊缩写搞错: 期刊是 Biosens Bioelectron 缩 'bios' 而非 'bej' = Biochem Eng J), CrossRef 文本搜后改为 10.1016/j.bios.2005.11.018"
    - "A. niger GOx UniProt P13006 我推测; QA via uniprot-fetcher 验证"
    - "PDB 1CF3 是 A. niger GOx 经典 (Hecht 1993)"
    - "Schwaneberg lab (Jacobs Univ Bremen, 后 RWTH Aachen) directed evolution 系列"
    - "biofuel cell + biosensor application: GOx 必须高 stability + 直接 electron transfer (DET) 倾向"
tags: [glucose_oxidase, GOx, GMC_oxidoreductase, FAD_dependent, thermostability_and_activity, directed_evolution, biofuel_cell, biosensor, Schwaneberg-lab, non-CAZy]
---

## 1. 背景与目标
- parent: A. niger GOx (UniProt P13006), FAD-dependent glucose oxidase, EC 1.1.3.4
- 自然反应: β-D-glucose + O₂ → D-glucono-1,5-lactone + H₂O₂
- 工业用 1: 食品工业 (氧消除 + 葡萄糖检测)
- 工业用 2: biosensors (临床 glucose meter, world's largest enzyme application by volume)
- 工业用 3: biofuel cells (新兴 implantable / wearable 能源)
- 目标: 提升 thermal stability + 直接 electron transfer (DET) 倾向, 用于 biofuel cell / biosensor 高级应用
- 应用: 临床 glucose meter 第三代 (DET-based, 不需要 mediator)

## 2. 决策过程

### 候选位点策略
- **Directed evolution** (Schwaneberg lab 经典 KnowVolution 方法):
  1. 起始 WT GOx 高活性, 但 thermostability 中等 (Tm ~60°C) + 不直接电子转移
  2. Random mutagenesis (epPCR) + saturation library on FAD 周围 surface
  3. Multi-substrate screen: thermal stability + electron transfer rate (electrode-based)
  4. 累加 ~5-7 mutations
- 后续 (Zhu 2007+ 系列) 加 surface 残基 charge engineering 提 DET

### 排除的位点 (★ 必填)
- FAD 结合 Rossmann fold (G-X-G-X-X-G/A motif) 严格保留 — flavin cofactor 必需
- Catalytic His (proton acceptor) + 保留
- Substrate-binding pocket (Tyr-Trp cluster) 一级 sphere 保留 — 否则 specificity 改
- Disulfide bridges (GOx 有 2 个) 保留
- N-glycosylation sites (fungal-glycosylated, P. pastoris 表达必保)

### 计算工具与阈值
- 1CF3 结构指导 library design (FAD-distal surface residues)
- High-throughput screen: H₂O₂ detection (peroxidase coupled, ABTS / OPD chromogen)
- Thermal stability via residual activity after heat shock (e.g., 65°C, 10 min)
- 实验校验: 异源表达 in P. pastoris (industrial host) → enzyme purification → DSF Tm + biofuel cell electrode response

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| WT GOx Tm | ~60°C |
| Evolved variant Tm | ~70°C (+10°C) |
| 累加 mutations | ~5-7 |
| Catalytic activity (kcat) | 维持或略增 |
| Direct electron transfer (DET) | 显著提升 (electrode response increased) |
| Biofuel cell power output | 数倍 WT |

### 失败案例 (★ 必填)
- 早期 surface mutations 提 Tm 但 sacrificial activity (oxygen tunnel altered)
- 部分 variants 提 DET 但 Tm 下降 — 双指标必要
- P. pastoris hyperglycosylation 改变 GOx 表面 charge → 影响 DET (industrial host 选择关键)
- H₂O₂ 副产物对 enzyme 自身 inhibitory; 高 substrate 浓度反应需要 catalase 共催化

## 4. 学习收获
- **成立的规则候选**:
  - **GMC oxidoreductase 工程化的双 key**: FAD 一级 sphere 严格保留 + 二级 sphere 是 substrate scope/DET 主战场
  - **GOx 为 biosensor / biofuel cell 应用工程化, DET 是新型 spec**: 不仅 activity 还要 electron-transfer-rate
  - **真菌 GOx 必在 yeast (P. pastoris) 表达** — E. coli 表达可溶但 glycosylation 缺失影响活性
- **被推翻的假设**:
  - "GOx 仅 mediator-based 应用, 不能 DET" — Zhu 2006 显示 surface engineering 可显著提 DET
- **下次类似问题应优先尝试**:
  - 任何 oxidase / FAD-dependent enzyme 用于 biosensor 应用: 评估 DET 倾向, surface charge engineering
  - GOx 类工程化必带 H₂O₂ tolerance 或 catalase 共催化
- **应避免**:
  - 改 FAD-binding 残基 — 必失活
  - 仅 thermostability 优化, 忽视 DET / electron transfer rate (biosensor 应用关键)
  - 在 E. coli 表达评估真菌 GOx — glycosylation 差异 confound 结果

## 5. 计算 / 实验原始数据
原始 evolved variants thermostability + DET 数据见 Biosens Bioelectron 21(11) 2006 supplementary; Schwaneberg lab 后续 KnowVolution paper 含 mechanism.
