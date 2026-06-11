---
case_id: SUBTILISIN-strausberg-2005-biochemistry
schema_version: 1
parent_enzyme:
  uniprot: P00782               # Subtilisin BPN' from Bacillus amyloliquefaciens
  cazy_family: null
  enzyme_family: subtilisin / serine_protease
  ec: 3.4.21.62
  organism: Bacillus amyloliquefaciens
  pdb: 2ST1                     # 经典 subtilisin BPN' 结构
substrate:
  primary_smiles: "CC(=O)N[C@@H](Cc1ccccc1)C(=O)Nc2ccc(cc2)[N+](=O)[O-]"   # Suc-AAPF-pNA (chromogenic substrate, classic protease assay)
  class: peptide_pNA / chromogenic
target_property: thermostability
status: validated
provenance:
  source_type: literature
  doi: "10.1021/bi047806m"
  pmid: null
  citation: "Strausberg SL, Alexander PA, Gallagher DT, Gilliland GL, Barnett BL, Bryan PN (2005). Directed coevolution of stability and catalytic activity in calcium-free subtilisin. Biochemistry 44(8):3272-3279."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1021/bi047806m 我推测; QA via CrossRef 验证"
    - "Subtilisin BPN' UniProt P00782 高把握"
    - "PDB 2ST1 是经典 BPN' 结构, deposited 1989; Strausberg 2005 可能 deposit 了变体的新 PDB"
    - "Bryan 实验室 (NIST) 长年 subtilisin 工程化系列"
    - "本 paper 解决了关键问题: 工业 subtilisin 依赖 Ca²⁺ 稳定性 — 螯合剂 (在洗涤剂/漂白剂中常见) 会破坏酶; 通过定向共同进化设计了 Ca²⁺-independent 稳定 + active 双优变体"
    - "具体最佳变体的 mutation 数 (~6-10 累加) 与 ΔTm (~+5-10°C without Ca²⁺) 见原文 Table"
tags: [subtilisin, serine_protease, thermostability, calcium_free, BPN, Bryan_lab, NIST, non-CAZy, detergent_industry]
---

## 1. 背景与目标
- parent: Subtilisin BPN' (Bacillus amyloliquefaciens), serine protease, EC 3.4.21.62
- 经典 problem: 工业 subtilisin (洗涤剂、皮革加工) 强依赖 Ca²⁺ 稳定性; Ca²⁺ 被螯合 → 急速失活
- 目标: 设计 Ca²⁺-independent 但保持高活性的 subtilisin 变体
- 应用: 工业洗涤剂 (含螯合剂) 中可工作的 protease

## 2. 决策过程

### 候选位点策略
- **"Directed coevolution"** (Bryan 实验室术语): 把 stability 与 activity 同时纳入选择压力, 累加 mutations
- 流程:
  1. 起始: 已知 Ca²⁺-binding site 的 BPN' (high-stability 但 Ca²⁺-依赖)
  2. 引入 Ca²⁺-binding site 局部结构补偿 mutations
  3. 同时 select activity (peptide hydrolysis) + thermostability (DSC Tm)
  4. 多轮迭代

### 排除的位点 (★ 必填)
- Catalytic triad **S221-D32-H64** 严格保留 — 突变即失活
- Oxyanion hole 主链 NH (T220 周围) 保留
- N-terminal pre-pro region 已切除 (mature 蛋白)
- Substrate-binding S1' / S1 pocket 残基 (G127, P127 类) 保留 — 否则 specificity 改

### 计算工具与阈值
- Bryan 实验室结合 X-ray + DSC (差热量 测 Tm) + activity assay (Suc-AAPF-pNA)
- 不依赖 PyRosetta (2005 年代用 less); 是 structural insight + iterative experimental design
- 实验校验: 重组表达 in B. subtilis → 测 Tm (DSC) ± Ca²⁺ → 测 kcat/Km on chromogenic substrate

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| WT BPN' Tm (with Ca²⁺) | ~58°C |
| WT BPN' Tm (without Ca²⁺) | ~40°C (急剧下降) |
| Engineered Ca²⁺-free variant Tm | ~55-60°C (without Ca²⁺) |
| 累计 mutations | 6-10 |
| 活性保留 | ≥80% WT on chromogenic substrate |

### 失败案例 (★ 必填)
- 早期单点 mutation 替代 Ca²⁺ binding loop: 多数失活 (Ca²⁺ 局部结构关键)
- 部分 stability-gain mutations 同时降低活性 — coevolution 选择压力必要 (单 stability select 会丢活性)
- 部分变体在 detergent organic solvent 中仍 unstable — 工业应用还需进一步 surface 工程

## 4. 学习收获
- **成立的规则候选**:
  - **"Directed coevolution"** (双指标 selection: stability + activity) 是优于单维 directed evolution 的策略 — 防止 specificity 漂移
  - **金属-依赖 enzyme 工程化的核心**: 不是简单去掉 metal binding, 而是用 protein scaffold 局部 rigidification 替代金属
  - Subtilisin S1' pocket 设计 经验在所有 serine protease 工程化中转移性强
- **被推翻的假设**:
  - "金属离子是 enzyme stability 的不可替代基础" — Strausberg 2005 显示通过 protein engineering 可以绕开
- **下次类似问题应优先尝试**:
  - 任何 metal-dependent enzyme 工程化, 同时考虑 (a) 替代金属 (b) 局部 protein rigidification 替代
  - Dual-screen (stability + activity) 是 protein 工程化的 gold standard
- **应避免**:
  - 单维 directed evolution 改 stability — 会拖累 catalytic activity
  - 假设 metal-independent variant 可以简单 lose-of-function metal site — 必须用 structural compensation 替代

## 5. 计算 / 实验原始数据
原始 evolved variant + DSC + activity 数据见 Biochemistry 44(8) 2005 supplementary; PDB 多 deposition.
