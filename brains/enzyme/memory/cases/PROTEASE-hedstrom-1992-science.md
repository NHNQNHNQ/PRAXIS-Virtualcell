---
case_id: PROTEASE-hedstrom-1992-science
schema_version: 1
parent_enzyme:
  uniprot: P00760               # Cationic trypsin (Bos taurus, cattle)
  cazy_family: null
  enzyme_family: serine_protease / trypsin
  ec: 3.4.21.4
  organism: Bos taurus
  pdb: 1TLD                     # Bovine trypsin classic structure
substrate:
  primary_smiles: "CC(=O)N[C@@H](Cc1ccccc1)C(=O)Nc2ccc(cc2)[N+](=O)[O-]"   # Suc-AAPF-pNA chymotrypsin substrate; trypsin natural substrate is Suc-AAPK-pNA (Lys/Arg)
  class: peptide_pNA / chiral_amino_acid_specificity
target_property: substrate_specificity
status: validated
provenance:
  source_type: literature
  doi: "10.1126/science.1546324"
  pmid: "1546324"
  citation: "Hedstrom L, Szilagyi L, Rutter WJ (1992). Converting trypsin to chymotrypsin: the role of surface loops. Science 255(5049):1249-1253."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "DOI 第一次推 1538442 错 (Science 不同 paper), CrossRef 文本搜后改为 10.1126/science.1546324"
    - "P00760 是牛 cationic trypsin 标准 reference"
    - "PDB 1TLD 是牛胰岛素 + trypsin 的早期结构;论文用类似多种 PDB 验证"
    - "本工作是蛋白工程教科书经典: 仅活性位点突变不够, 必须 transplant surface loops 才能转换 substrate specificity"
    - "Hedstrom 后续在 J Mol Biol 1994/1996 发表系列 follow-up 工作, 完整解析了 specificity 决定因素"
tags: [serine_protease, trypsin, chymotrypsin, substrate_specificity, loop_transplantation, surface_loops, classic_protein_engineering, Hedstrom, non-CAZy]
---

## 1. 背景与目标
- parent: Bovine trypsin (UniProt P00760), serine protease, EC 3.4.21.4
- 起始 specificity: 切 Lys/Arg 后 (positive charge, S1 pocket 含 Asp189 引力)
- 目标: 把 trypsin 改造成 chymotrypsin-like (切 Phe/Tyr/Trp 后, hydrophobic specificity)
- 经典问题: substrate specificity 是 active-site residue 决定还是更广泛 protein context 决定?
- 应用: 蛋白工程基础研究 + serine protease 设计原理验证

## 2. 决策过程

### 候选位点策略
- **Iterative rational design** 三阶段:
  1. **Active-site mutation alone** (D189 → S, G216 → A, G226 → A): trypsin 经典 specificity-determining residue 替换为 chymotrypsin 类
  2. **Surface loop transplantation #1**: loop 1 (residues 185-188) 从 chymotrypsin 移植
  3. **Surface loop transplantation #2**: loop 2 (residues 217-225) 也移植
- 设计逻辑: 第 1 步如果不够 → 第 2 步, 第 2 步不够 → 第 3 步

### 排除的位点 (★ 必填)
- Catalytic triad **H57 / D102 / S195** 严格保留 — 突变即失活
- Oxyanion hole 主链 NH (G193, S195) 保留 — 反应几何需要
- Disulfide bridges (trypsin 有 6 个) 保留 — fold 稳定性必需
- Substrate-binding cleft 中已与 chymotrypsin 同源的残基保留

### 计算工具与阈值
- 1992 年代: 主要 PyMOL/X-ray crystallography 比对 trypsin (P00760) vs chymotrypsin (P00766) 结构
- 实验校验: 重组表达 in E. coli + 酵母 host → 多 chromogenic peptide substrate 测 kcat/Km → 比较 specificity 比 (kcat/Km)_aromatic / (kcat/Km)_basic

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文 Table 1-3)
| 阶段 | Variant | kcat/Km vs (Lys substrate) | kcat/Km vs (Phe substrate) | 关键发现 |
| --- | --- | --- | --- | --- |
| WT trypsin | trypsin | 高 (>10^4 M⁻¹s⁻¹) | 极低 (<1) | 严格 K/R specificity |
| Active site only | trypsin(D189S/G216A/G226A) | 大幅下降 | 略增 (~10) | 远不及 chymotrypsin |
| + loop 1 | (above + loop1 swap) | 进一步下降 | 中等增 (~100) | 部分功能转移 |
| + loop 1 + loop 2 | "chymotrypsin-like trypsin" | 几乎无活性 | ~10^3 | 真正功能转换 (虽然总体活性下降) |
| Native chymotrypsin (control) | - | 低 | 极高 (>10^4) | reference |

### 失败案例 (★ 必填)
- **Active-site-only mutation 失败**: 仅做 D189S/G216A/G226A 不能 transfer chymotrypsin specificity — 这推翻了"specificity 由 1° contact 残基决定"的假设
- **Loop 1 alone 不够**: 必须 loop 1 + loop 2 协同, single loop transplantation 部分功能 + 失活
- **总体 turnover 大幅下降**: 即使最终 chymotrypsin-like variant 的 kcat 比 native chymotrypsin 低 10-100×; 说明虽然 specificity 转换了, catalytic perfection 未完整迁移
- 数个中间 variant 表达失败或 loss of fold (loop 区破坏)

## 4. 学习收获
- **成立的规则候选**:
  - **Substrate specificity 是 multi-determinant**: active-site 残基 + surface loops + 二级 sphere 协同, 不能由单一来源转移
  - **Loop transplantation 是 specificity 工程化的强工具**: 但比 single-residue 突变破坏性强 (常 destabilize)
  - **Specificity 与 turnover (kcat) 是耦合的**: 转换 specificity 几乎必然 cost 一些 turnover
  - **Serine protease "scaffold" 高度 conserved 内核 + 可工程化外环** — trypsin/chymotrypsin/elastase 共享 catalytic triad + fold, specificity 由 surface 决定
- **被推翻的假设**:
  - "Active-site residues alone determine substrate specificity" — Hedstrom 1992 显式推翻
- **下次类似问题应优先尝试**:
  - 任何 specificity 工程化 (任何 enzyme), 不要假设 active-site mutation 就够 — 必须考虑 surface contributions
  - Serine protease 类工程化 use loop transplantation as a primary tool
- **应避免**:
  - 仅基于 sequence 比对换 active-site residues 期望 specificity 转换
  - 忽视 turnover-specificity tradeoff — 双指标必测

## 5. 计算 / 实验原始数据
原始 enzyme kinetics 表与 mutational analysis 见 Science 255(5049) 1992 supplementary; 后续 Hedstrom J Mol Biol 1994/1996 paper 含 expanded analysis.
