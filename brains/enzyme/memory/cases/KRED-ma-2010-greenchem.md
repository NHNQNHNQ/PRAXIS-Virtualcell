---
case_id: KRED-ma-2010-greenchem
schema_version: 1
parent_enzyme:
  uniprot: null                  # Codexis KRED-101/KRED-130 类 evolved variants 是工业商品酶, 无 standalone UniProt
  cazy_family: null
  enzyme_family: ketoreductase / SDR_family
  ec: 1.1.1.184                 # carbonyl reductase (NADPH-dependent)
  organism: Codexis evolved variant; 起始 SDR superfamily 短链 dehydrogenase/reductase
  pdb: null                     # evolved variant 不公开 PDB
substrate:
  primary_smiles: "ClCC(=O)CC(=O)OCC"   # ethyl 4-chloroacetoacetate (atorvastatin 关键 chiral hydroxyl 中间体前体)
  class: chiral_pharmaceutical_intermediate / β-ketoester
target_property: substrate_specificity
status: validated
provenance:
  source_type: literature
  doi: "10.1039/b919115c"
  pmid: null
  citation: "Ma SK, Gruber J, Davis C, Newman L, Gray D, Wang A, Grate J, Huisman GW, Sheldon RA (2010). A green-by-design biocatalytic process for atorvastatin intermediate. Green Chemistry 12(1):81-86."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1039/b919115c 我推测; QA via CrossRef 验证"
    - "Codexis KRED 系列是商业 evolved variants, 起始 enzyme 来源未在 paper 明确; 不公开 UniProt"
    - "primary_smiles 是 ethyl 4-chloroacetoacetate, atorvastatin chiral 侧链关键中间体"
    - "Codexis CodeEvolver platform 与 Pfizer 合作; 工业 5000 ton/yr 级"
    - "本工作覆盖 KRED + halohydrin dehalogenase (HHDH) + glucose dehydrogenase (GDH cofactor recycle) 三酶 cascade 整体优化, 此 case 主要标记 KRED 工程化部分"
tags: [ketoreductase, KRED, SDR_superfamily, substrate_specificity, atorvastatin, green_chemistry, Codexis, Pfizer, pharmaceutical_industry, non-CAZy]
---

## 1. 背景与目标
- parent: Codexis KRED-101 / KRED-130 类 evolved variants (SDR superfamily, NADPH-dependent ketoreductase)
- 起始: 天然酶对工业 substrate (ethyl 4-chloroacetoacetate, ECAA) 活性低 + ee 不足
- 目标: 工业级 (g/L 级 substrate, organic co-solvent) 立体选择还原 ECAA 给 (S)-ethyl 4-chloro-3-hydroxybutyrate (atorvastatin chiral 侧链前体)
- 应用: Atorvastatin (Lipitor, Pfizer 抗 cholesterol 大宗药) 工业生产 — 全球 5000 ton/yr

## 2. 决策过程

### 候选位点策略
- **Codexis CodeEvolver platform** (与 Savile 2010 sitagliptin 同 platform):
  1. 起始 KRED 库 (商业 KRED panel, ~24 enzyme variants)
  2. Iterative saturation mutagenesis on substrate-binding pocket residues
  3. 多 rounds, 累加 ~10-20 mutations
  4. 工业反应条件 (high substrate, organic co-solvent, 25-35°C) selection
- 同步优化:
  - HHDH (halohydrin dehalogenase) 转 (S)-3-hydroxybutyrate → (R)-3-cyano-3-hydroxybutyrate
  - GDH (glucose dehydrogenase) NADPH 循环

### 排除的位点 (★ 必填)
- NADPH 结合 Rossmann fold (G-X-X-X-G-X-G nucleotide binding motif) 严格保留
- Catalytic Tyr-Lys-Ser triad (SDR 家族特征) 不动
- Substrate carbonyl 接触的 Asn (typically) 保留
- Dimer / tetramer interface 不动 (SDR 通常多体)

### 计算工具与阈值
- Structure-guided initial library: SDR family known structure 用作模板
- High-throughput screen: NADPH 消耗速率 + chiral HPLC ee%
- 实验校验: 重组表达 in E. coli → 工业反应模拟 (g/L substrate, IPA 共溶剂 cofactor recycle) → product titer + ee + diastereomer ratio

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| WT KRED 活性 (ECAA) | 中等 (g/L 转化但 ee 不足) |
| Engineered KRED ee (S)-product | >99.9% |
| Engineered KRED 工业 productivity | g substrate / g enzyme / day 工业级 |
| Cascade overall yield (3 enzyme) | >90% theoretical |
| E-factor (kg waste / kg product) | <10 (vs 化学路线 >50) |

### 失败案例 (★ 必填)
- 早期 KRED variants ee 漂移 — directed evolution 必须 dual-screen (activity + ee)
- 部分 mutations 提升 KRED 活性但 destabilize protein — 工业反应条件下 quick inactivation
- HHDH 与 KRED 的 cascade interaction: 起初 by-product 累积 — 需要 simultaneous engineering
- Cofactor (NADPH) cost 一直是 cascade 的隐藏门槛, GDH 设计是 enabler

## 4. 学习收获
- **成立的规则候选**:
  - **多酶 cascade 的工程化必须 simultaneous, 不能串行优化** — 单酶最优 ≠ cascade 最优
  - **Codexis 工业 directed evolution platform** (CodeEvolver) 可在 ~10 rounds 内将工业 enzyme 推到 production-grade
  - SDR 家族 ketoreductase 的工程化 toolkit: structure-guided library + dual-screen + 工业反应条件 final 验证
- **被推翻的假设**:
  - "化学不对称还原 (Noyori 类 catalysts) 是工业 chiral alcohol 唯一 viable" — Codexis 显示 enzyme cascade 可在 atorvastatin 这种大宗药上击败化学路线
- **下次类似问题应优先尝试**:
  - 任何 chiral pharmaceutical intermediate 工程化: 评估 multi-enzyme cascade 而不是单酶, 同步 KRED + cofactor recycle
  - Cofactor recycle 的 GDH (glucose dehydrogenase) 是工业 cascade 的"隐藏支柱"
- **应避免**:
  - 单 KRED 工程化忽视 cofactor cost — 大宗药级反应 NADPH cost 致命
  - 用学术规模 (mg substrate) 评估工业 KRED — 工业反应条件 (g/L substrate + organic co-solvent) 完全不同

## 5. 计算 / 实验原始数据
原始 cascade kinetics + 工业流程数据见 Green Chemistry 12(1) 2010; Codexis 平台技术细节部分专利化.
