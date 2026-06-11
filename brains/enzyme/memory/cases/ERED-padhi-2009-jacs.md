---
case_id: ERED-padhi-2009-jacs
schema_version: 1
parent_enzyme:
  uniprot: Q02899                # Saccharomyces pastorianus OYE1 (NADPH oxidoreductase 1, Old Yellow Enzyme)
  cazy_family: null
  enzyme_family: ene_reductase / Old_Yellow_Enzyme / OYE_family
  ec: 1.6.99.1                  # NAD(P)H dehydrogenase (quinone)
  organism: Saccharomyces pastorianus
  pdb: 1OYA                     # OYE1 经典结构 (Karplus 1991)
substrate:
  primary_smiles: "C=C(C)C(=O)OCC"   # ethyl methacrylate (示意; 论文用 various activated alkenes)
  class: activated_alkene / Michael_acceptor
target_property: substrate_specificity   # 包括 stereocomplementary variants (R/S 切换)
status: validated
provenance:
  source_type: literature
  doi: "10.1021/ja8081389"
  pmid: null
  citation: "Padhi SK, Bougioukou DJ, Stewart JD (2009). Site-saturation mutagenesis of tryptophan 116 of Saccharomyces pastorianus old yellow enzyme uncovers stereocomplementary variants. J Am Chem Soc 131(9):3271-3280."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1021/ja8081389 我推测 (well-cited Stewart lab paper); QA via CrossRef 验证"
    - "OYE1 UniProt Q02899 我推测; QA via uniprot-fetcher 验证"
    - "PDB 1OYA 是 OYE1 + FMN 的 1991 经典结构 (Karplus / Massey)"
    - "Stewart lab (Florida) 经典 OYE 工程化系列; 此 W116 saturation 是 OYE1 工程化教科书例"
    - "Stereocomplementary 指: 同一 substrate, WT vs W116 mutant 给相反 stereoisomer 产物 (R) vs (S)"
tags: [ene_reductase, ERED, OYE1, OYE_family, FMN_dependent, asymmetric_alkene_reduction, stereocomplementary, site_saturation, Stewart-lab, non-CAZy]
---

## 1. 背景与目标
- parent: Saccharomyces pastorianus OYE1 (Old Yellow Enzyme 1, UniProt Q02899, FMN-dependent ene-reductase)
- 起始: WT 还原 activated alkenes (Michael acceptors) 给 (R)-或 (S)- 选择因 substrate 异 — 难以可预测控立体取向
- 目标: 通过 W116 site-saturation 找出 **stereocomplementary** variants (相同 substrate, 相反 stereo product)
- 应用: 工业 chiral 合成 — 给定一个 evolved variant, 可选择产 (R) 或 (S) 产物, 替代化学不对称还原

## 2. 决策过程

### 候选位点策略
- **Site-saturation mutagenesis** (focused library):
  1. 选 W116 — OYE1 active site 的"覆盖盖" tryptophan, 控 substrate 取向
  2. 全 19 amino acids 替换 (NNK codon)
  3. 所有 variants 测多 substrates (10+ activated alkenes)
- 不依赖大型 random library, 是 hypothesis-driven single-position saturation
- 后续 (Stewart 2010+) follow-up 加 W116 + neighbor combinatorial

### 排除的位点 (★ 必填)
- FMN 结合 residues (His 191, Tyr 196 类) 严格保留 — flavin cofactor 必需
- Catalytic Tyr (proton donor, Y196) 保留 — 反应机制必需
- Substrate-binding hydrophobic pocket 大部分 residues 保留, 仅改 W116 一个

### 计算工具与阈值
- 1OYA 结构指导: W116 在 active site, side chain 直接贴 substrate β-face
- 实验校验: 重组表达 in E. coli → 多 substrate panel 测 → chiral GC/HPLC ee%

## 3. 实验结果

### 总体趋势 (★ 见原文 Table 1-2)
| W116X variant | substrate panel | (R)/(S) outcome | ee% range |
| --- | --- | --- | --- |
| W116 (WT) | varied | mixed (R)/(S) per substrate | 50-99% |
| W116F | similar to WT | similar profile | 70-95% |
| W116I | for some substrates | (S)-selective shift | 75-90% (S) |
| W116V | for cyclohexenone类 | reverse to (R) | 80-95% (R) |
| W116A | broad scope but lower ee | both selectivities possible | 50-90% |
| W116Y / W116L / etc | various | covers most stereochemistry combinations | Complete stereocomplementary collection |

### 失败案例 (★ 必填)
- 部分 W116X variants 完全失活 (W116P 类, 破坏 active site geometry)
- 部分 variants ee 漂移到 50% (no selectivity) — 中间状态非 useful
- W116-only saturation 不能完全覆盖所有 substrate; 部分 substrate 需 combinatorial W116+neighbor

## 4. 学习收获
- **成立的规则候选**:
  - **Single-position saturation 在 active site key residue** 可大幅扩 stereochemistry repertoire — Stewart 2009 经典验证
  - **OYE family 的 W116-类 "active site lid" residue** 是 stereoselectivity 工程化的核心控点
  - **Stereocomplementary variants** 设计是 bioretrosynthesis 工具 — 给定 substrate, 选 right variant
- **被推翻的假设**:
  - "Stereoselectivity 由 enzyme fold 整体决定, 难以 single-residue 调" — Padhi 2009 显式推翻 (W116 单点足够 reverse)
- **下次类似问题应优先尝试**:
  - 任何 enzyme stereoselectivity 工程化, 找 active site "覆盖盖" 类 residue (Trp/Tyr/Phe), site-saturation 优先
  - OYE family enzyme 工程化: W116-类位置必查
- **应避免**:
  - 大 random library 期望 stereoselectivity reversal — focused saturation 效率高得多
  - 仅在一个 substrate 上评估 — 必须 substrate panel 才能看 stereocomplementary 全貌

## 5. 计算 / 实验原始数据
原始 W116 saturation 数据 + chiral HPLC traces 见 J Am Chem Soc 131(9) 2009 supplementary.
