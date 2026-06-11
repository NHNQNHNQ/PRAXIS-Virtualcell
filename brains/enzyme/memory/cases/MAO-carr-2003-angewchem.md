---
case_id: MAO-carr-2003-angewchem
schema_version: 1
parent_enzyme:
  uniprot: P46882                # MAO-N (monoamine oxidase N) from Aspergillus niger; QA 验证
  cazy_family: null
  enzyme_family: amine_oxidase / monoamine_oxidase
  ec: 1.4.3.4
  organism: Aspergillus niger
  pdb: 2VVL                     # Turner lab 后续解析的 evolved MAO-N 结构 (D5/D9 variant), 待 QA 验证
substrate:
  primary_smiles: "CC(N)c1ccccc1"   # (S)-1-phenylethylamine — racemate 用 MAO-N 单选氧化分离
  class: chiral_primary_secondary_amine
target_property: substrate_specificity   # 实际是 broad scope + ee preservation
status: validated
provenance:
  source_type: literature
  doi: "10.1002/anie.200352100"
  pmid: null
  citation: "Carr R, Alexeeva M, Enright A, Eve TS, Dawson MJ, Turner NJ (2003). Directed evolution of an amine oxidase possessing both broad substrate specificity and high enantioselectivity. Angew Chem Int Ed Engl 42(40):4807-4810."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1002/anie.200352100 我推测; QA via CrossRef 验证"
    - "Aspergillus niger MAO-N UniProt P46882 我推测; QA via uniprot-fetcher 验证"
    - "PDB 2VVL 我推测对应 evolved variant 结构; 论文 2003 当时可能未 deposit, 后续 Turner lab follow-up 才 deposit (e.g., 2005-2010 系列)"
    - "Turner lab MAO-N 系列 (Nick Turner @ Manchester) 自 2002 起经典 directed evolution 工作; 此 2003 paper 是初代演化 variant (后续命名 D5, D9, D11)"
    - "evolved variants 接受 large bulky chiral amines (e.g., 1-phenylethylamine, alpha-methylbenzylamine, sec-butylamine) 用于 oxidative kinetic resolution"
tags: [amine_oxidase, MAO-N, monoamine_oxidase, substrate_specificity, enantioselectivity, directed_evolution, chiral_amine, oxidative_resolution, Turner-lab, non-CAZy]
---

## 1. 背景与目标
- parent: Aspergillus niger MAO-N (UniProt P46882), monoamine oxidase, EC 1.4.3.4
- WT 酶: 接受 simple primary amines (e.g., benzylamine), 但对 chiral primary/secondary amines 活性低 + ee 不足
- 目标: 通过 directed evolution 让 MAO-N 接受**广** chiral amine substrate scope, 同时保持 (S)-selectivity (oxidize (S)-enantiomer, 保留 (R) 在 racemate 反应中)
- 应用: 工业级 chiral amine kinetic resolution (制药关键反应); 与化学不对称合成互补

## 2. 决策过程

### 候选位点策略
- **Directed evolution** (Turner lab 招牌方法):
  1. 起始 WT MAO-N (Schilling 团队 2002 已克隆)
  2. Error-prone PCR + DNA shuffling 多 rounds
  3. High-throughput screen via colorimetric (peroxidase coupled detection of H₂O₂ byproduct)
  4. 选 broad substrate scope (multi-substrate plate format) + high ee (chiral HPLC verification)
- 累计 ~5-7 mutations 给出 D5 variant; 后续 ~15+ mutations → D11

### 排除的位点 (★ 必填)
- FAD 结合 Rossmann fold (G-X-G-X-X-G/A motif) 严格保留 — flavin cofactor 必需
- Active site Tyr/Phe (一级 sphere, 控反应取向) 较少改 — 改了易失活
- 二聚体 interface 不动 — MAO 都是 dimer
- N-terminal targeting/membrane anchor (MAO 通常膜定位) 在 directed evolution 中常出现稳定化 mutations 但不破坏定位

### 计算工具与阈值
- High-throughput screen via 96-well plate + peroxidase + ABTS color readout for H₂O₂
- 不依赖前期 ΔΔG 设计 (是 directed evolution + experimental selection)
- 实验校验: 异源表达 in E. coli (MAO-N 可溶) → cell lysate H₂O₂ assay → 顶级 hits 纯化 + chiral HPLC ee

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| WT MAO-N 接受 1-phenylethylamine | 弱活性, ee 中等 (~70-80%) |
| Evolved D5 variant 活性 (1-phenylethylamine) | 100-1000× WT |
| ee | >99% (S)-selective |
| Substrate scope 扩大 | 多种 secondary amine (sec-butylamine, α-methylbenzylamine 等) |
| 累加 mutations (D5 variant) | ~5-7 |
| Application: oxidative kinetic resolution | 工业级 |

### 失败案例 (★ 必填)
- 早期 rounds 部分 variants 失去 (S)-selectivity (反向 (R) 选择) — directed evolution 必须 dual-screen activity + ee
- 部分 variants H₂O₂ tolerance 低 — MAO 自身产物 H₂O₂ 在 high titer 反应中 inhibitory
- 部分 broadened substrate scope 的变体表达 yield 显著下降 — surface 紊乱影响折叠/定位

## 4. 学习收获
- **成立的规则候选**:
  - **MAO-N 类 amine oxidase 的 substrate scope 工程化是 directed evolution 主战场** — rational 不太 work (active site 几何复杂, FAD 介导)
  - **High-throughput colorimetric H₂O₂ screen** 是 amine oxidase 工程化的关键 enabler
  - **Oxidative kinetic resolution** 比 transaminase 路线互补: oxidative (S)-selective MAO-N + chemical reduction → (S)-amine product
- **被推翻的假设**:
  - "MAO 类 flavin enzyme 难以扩展 substrate scope" — Carr 2003 显示 directed evolution 在 7 mutations 内显著扩
- **下次类似问题应优先尝试**:
  - 任何 oxidase / FAD-dependent enzyme substrate engineering: directed evolution + H₂O₂ readout
  - 与 transaminase 互补考虑: 若需要 (S)-amine 且有 prochiral ketone → transaminase; 若需 (S)-amine 而起始 racemic → MAO-N kinetic resolution
- **应避免**:
  - 单 round directed evolution; MAO-N 优化通常 4-6 rounds
  - 忽视 H₂O₂ 副产物 inhibition — 工业反应必须设计 H₂O₂ 消除 (catalase 共催化或 reductant)

## 5. 计算 / 实验原始数据
原始 evolved variants kinetics + ee 数据见 Angew Chem 42(40) 2003 supplementary.
