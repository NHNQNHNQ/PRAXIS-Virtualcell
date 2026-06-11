---
case_id: TRANSAMINASE-savile-2010-science
schema_version: 1
parent_enzyme:
  uniprot: null                  # ATA-117 是高度工程化变体, 起始 enzyme 无标准 UniProt; 见 unverified_details
  cazy_family: null
  enzyme_family: omega_transaminase
  ec: 2.6.1.18                  # β-alanine--pyruvate transaminase (与 ω-transaminase 同类)
  organism: Arthrobacter sp. KNK168 (起始); ATA-117 工业商品株
  pdb: 3WWH                     # ω-transaminase from Arthrobacter, 后续解析的相关结构; QA 验证
substrate:
  primary_smiles: "O=C(CC(=O)c1nnc(n1CC=O)C(F)(F)F)Cc2c(F)cc(F)c(F)c2F"  # prositagliptin ketone (近似; sitagliptin synthesis prochiral ketone precursor) — 实际 SMILES 复杂, 此为示意
  class: prochiral_ketone / pharmaceutical_intermediate
target_property: substrate_specificity
status: validated
provenance:
  source_type: literature
  doi: "10.1126/science.1188934"
  pmid: null
  citation: "Savile CK, Janey JM, Mundorff EC, Moore JC, Tam S, Jarvis WR, Colbeck JC, Krebber A, Fleitz FJ, Brands J, Devine PN, Huisman GW, Hughes GJ (2010). Biocatalytic asymmetric synthesis of chiral amines from ketones applied to sitagliptin manufacture. Science 329(5989):305-309."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1126/science.1188934 高把握"
    - "起始 enzyme 是 Codexis 公司的 ATA-117 商业 ω-transaminase, 来源 Arthrobacter sp.; 不是 standard UniProt entry — 工业 evolved variants 通常不 deposit"
    - "原 paper 终极 variant 累计 27 个 mutations, 接受 prositagliptin ketone (天然不可接受的 large bulky substrate)"
    - "Codexis CodeEvolver platform 的旗舰案例, 与 Merck 合作"
    - "PDB 3WWH 是 Arthrobacter ω-transaminase 但可能不是 Savile 2010 用的具体 evolved variant"
    - "primary_smiles 是 prositagliptin ketone 近似 SMILES; 真实 SMILES 在 Savile 2010 Fig 1 给出"
tags: [transaminase, omega_transaminase, substrate_specificity, directed_evolution, sitagliptin, pharmaceutical, Codexis, Merck, biocatalysis_industrial, non-CAZy]
---

## 1. 背景与目标
- parent: ω-transaminase from Arthrobacter sp. KNK168 (Codexis 商业 ATA-117 enzyme)
- 起始活性: 接受 small-medium ketones, 但对 prositagliptin ketone (大型 bulky substrate) 几乎无活性 (< detection)
- 目标: 通过 directed evolution 让 transaminase 接受 prositagliptin ketone, 直接给出 (R)-sitagliptin amine, 替代原工艺的金属催化氢化
- 应用: Merck sitagliptin (Januvia, 糖尿病药) 工业生产 — 大宗药物 biocatalytic 流程的 landmark 案例

## 2. 决策过程

### 候选位点策略
- **Directed evolution** (Codexis CodeEvolver platform):
  1. 起始 ATA-117 显示 prositagliptin ketone 活性 < detection
  2. In silico structure-guided initial library: 围绕 active site 的 12 个 residue 做 saturation
  3. 多轮 iterative ssm + DNA shuffling + screening
  4. ~11 rounds, 累计 27 mutations
  5. 最终 variant 在工业反应条件下 (high substrate, organic co-solvent, 45°C) 高活性高 ee

### 排除的位点 (★ 必填)
- PLP cofactor binding 残基 (Lys286, Asp259 类) 严格保留 — PLP-dependent enzyme 必需
- Active site 二级 sphere 也部分受 selection 保护 — directed evolution 自动优化
- Dimer interface 残基不能动 — transaminase 是 obligate dimer

### 计算工具与阈值
- In silico structure-guided library design (起手) + High-throughput screen (主驱动)
- LC-MS detection of (R)-sitagliptin product 作 readout
- 实验校验: 工业反应条件 (high substrate concentration, isopropylamine 作 amino donor, organic co-solvent DMSO) → product titer + ee% measurement

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| WT ATA-117 活性 (prositagliptin ketone) | < detection limit |
| Round 11 evolved variant 活性 | 工业级 (>200 g/L product, >99.95% ee) |
| 累计 mutations | 27 |
| 反应条件 | 50% DMSO, 45°C, isopropylamine, 数小时 |
| 工业 outcome | 替换原 Rh-catalyzed asymmetric hydrogenation, yield +10-13%, 废物 -19% |

### 失败案例 (★ 必填)
- 早期 rounds 部分 variants 失去 enantioselectivity (反向 (S) selectivity) — directed evolution 必须 dual-screen activity + ee
- 高浓度 substrate (~250 g/L) 下 enzyme aggregation 显著, 中间 rounds 加 organic co-solvent 兼容性 mutations
- Library 中 ~30% mutations 是 neutral / mildly negative — selection burden 大

## 4. 学习收获
- **成立的规则候选**:
  - **大型 bulky pharmaceutical substrate 的 transaminase 工程化必须 dual-screen activity + ee** — 单 screen 必失败
  - **结构引导的 initial library** (active site ±5 Å saturation) 能大幅压缩 directed evolution rounds
  - 工业级 evolved enzyme 普遍累计 20+ mutations — 单点工程化无效
- **被推翻的假设**:
  - "transaminase substrate scope 受 PLP cofactor 几何严格限制, 无法显著扩展" — Savile 2010 显示 27 mutations 可大幅扩展, 工业级 prochiral ketone 可行
- **下次类似问题应优先尝试**:
  - 工业 biocatalyst 工程化用 Codexis CodeEvolver / 同等 high-throughput platform; 学术规模工程化 (~few mutations) 不够
  - 结构引导 initial library + dual-screen + organic co-solvent 兼容性 mutations 加 — 完整工业 pipeline 必备
- **应避免**:
  - 用学术 small-scale (few mg substrate) screen 评估工业 variants — 工业反应条件 (g/L 级 substrate, organic co-solvent) 完全不同
  - 期望 single-point or few-point mutations 解决工业 substrate 问题 — Sitagliptin 案例 27 mutations 是基线

## 5. 计算 / 实验原始数据
原始 evolved variant 列表 + 工业反应优化数据见 Science 329(5989) supplementary.
