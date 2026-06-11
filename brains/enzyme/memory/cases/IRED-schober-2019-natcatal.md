---
case_id: IRED-schober-2019-natcatal
schema_version: 1
parent_enzyme:
  uniprot: null                  # Codexis evolved IRED variant; 起始来源 Streptomyces 类 IRED, 商业化未公开 standalone UniProt
  cazy_family: null
  enzyme_family: imine_reductase / IRED
  ec: 1.5.1.-                   # imine reductase, NADPH-dependent
  organism: Codexis evolved variant; parent from Streptomyces sp.
  pdb: null                     # evolved variant 不公开 PDB; 同家族 reference 结构 4D3F (Streptomyces sp. GF3546 IRED)
substrate:
  primary_smiles: "O=C1CCN(CC1)c2ccccc2"    # cyclohexanone-derived imine substrate (示意; LSD1 inhibitor GSK2879552 prochiral imine 实际复杂)
  class: prochiral_imine / pharmaceutical_intermediate
target_property: substrate_specificity   # bulky pharmaceutical substrate scope
status: validated
provenance:
  source_type: literature
  doi: "10.1038/s41929-019-0341-4"
  pmid: null
  citation: "Schober M, MacDermaid C, Ollis AA, Chang S, Khan D, Hosford J, Latham J, Ihnken LAF, Brown MJB, Fuerst D, Sanganee MJ, Roiban GD (2019). Chiral synthesis of LSD1 inhibitor GSK2879552 enabled by directed evolution of an imine reductase. Nat Catal 2(10):909-915."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1038/s41929-019-0341-4 高把握 (Codexis × GSK 旗舰 paper)"
    - "起始 IRED 来源: Streptomyces 类 (Codexis IRED-44 类), 不公开具体 UniProt"
    - "Codexis CodeEvolver platform; 与 sitagliptin TA / atorvastatin KRED 同 platform"
    - "本案例是 IRED 工业化 landmark — 之前 IRED 主要学术规模, 此后大宗药级"
    - "GSK2879552: histone demethylase LSD1 inhibitor, oncology drug candidate"
tags: [imine_reductase, IRED, NADPH_dependent, substrate_specificity, directed_evolution, pharmaceutical, GSK_LSD1_inhibitor, Codexis, GSK, biocatalysis_industrial, non-CAZy]
---

## 1. 背景与目标
- parent: Codexis Streptomyces-derived IRED variant (NADPH-dependent imine reductase)
- 起始: WT 接受 small/medium imines, 但对 GSK2879552 prochiral imine (large bulky pharmaceutical) 无活性
- 目标: 工业级 (g/L 级 substrate, organic co-solvent) 立体选择还原 imine → (R) 或 (S) chiral amine
- 应用: GSK2879552 (LSD1 inhibitor, oncology Phase I clinical) 工业生产 — 替代化学不对称 H₂ 还原

## 2. 决策过程 (Codexis CodeEvolver platform)

### 候选位点策略
- **Directed evolution + Structure-guided initial library** (Codexis 标准 platform):
  1. 起始 IRED 序列库 (~24 商业 IRED panel, Codexis IRED kit)
  2. Structure-guided saturation library on substrate-binding pocket residues
  3. ~10 rounds iterative selection
  4. 累加 ~20+ mutations
  5. 工业反应条件 (high substrate, IPA cofactor recycle, organic co-solvent) selection
- 与 KRED-ma / TRANSAMINASE-savile 同范式

### 排除的位点 (★ 必填)
- NADPH 结合 Rossmann fold (G-X-X-X-G-X-G motif) 严格保留
- Catalytic Tyr (proton donor) + 保留位点 — IRED 类 SDR-style mechanism
- Dimer interface (IRED 多为 obligate dimer)
- 在 Codexis CodeEvolver 中: directed evolution + dual-screen 自动保护 catalytic 残基

### 计算工具与阈值
- Structure-guided library + 工业 high-throughput screen (LC-MS based product detection)
- 实验校验: 重组表达 in E. coli → 工业反应模拟 (g/L imine, IPA + GDH cofactor recycle, 25-35°C) → product titer + ee + chiral HPLC

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| WT IRED 活性 (GSK2879552 imine) | < detection |
| Round 10 evolved variant 活性 | 工业级 (>200 g/L product, >99.9% ee) |
| 累加 mutations | ~20 |
| 工业反应 | 高浓度 substrate + IPA + GDH cofactor recycle |
| 工业 outcome | GSK2879552 临床用 chiral amine, 替代 Rh-catalyzed 不对称 H₂ 还原 |

### 失败案例 (★ 必填)
- 早期 rounds 部分 variants ee 反向 — directed evolution 必须 dual-screen activity + ee
- 高 substrate concentration (>250 g/L) imine 在 aqueous 中部分水解为 ketone — 工艺设计加 buffer 控水解
- Cofactor recycling efficiency: NADPH cost 是工业 cascade gating cost; GDH 共催化 enabler
- Codexis 商业化的 evolved variant 序列不公开, 学术 group 难以复现 detail

## 4. 学习收获
- **成立的规则候选**:
  - **IRED 工程化是 transaminase 之外另一条 chiral amine 工业路线** — 选哪条取决于 substrate 形式 (TA: prochiral ketone; IRED: prochiral imine)
  - **Codexis CodeEvolver platform** 在 IRED + TA + KRED 反复验证: ~20-30 mutations + ~10 rounds + 工业反应条件 dual-screen 可达大宗药级
  - 工业 IRED 必备 cofactor recycle (GDH 类) — NADPH cost 决定 process economics
- **被推翻的假设**:
  - "IRED 是学术规模 enzyme, 不能工业化" — Schober 2019 LSD1 inhibitor 案例显式推翻
- **下次类似问题应优先尝试**:
  - 对 chiral amine 合成: 先评估 substrate 形式 (ketone → TA, imine → IRED), 再选 platform
  - 工业 chiral pharmaceutical 工程化: 必走 Codexis 类 platform; 学术规模工程化 (~few mutations) 不够
- **应避免**:
  - 期望 single-point + few-mutation 解决 GSK2879552 类 bulky pharmaceutical substrate
  - 忽视 cofactor recycling cost — NADPH 工业反应 economics gating

## 5. 计算 / 实验原始数据
原始 evolved IRED 性能数据 + 工业反应优化见 Nat Catal 2(10) 2019 supplementary; Codexis 商业化细节部分专利化.
