---
case_id: DERA-greenberg-2004-pnas
schema_version: 1
parent_enzyme:
  uniprot: P0A6L0               # E. coli DERA (deoxyribose-5-phosphate aldolase)
  cazy_family: null
  enzyme_family: aldolase / DERA_class_I
  ec: 4.1.2.4
  organism: Escherichia coli
  pdb: 1JCJ                     # E. coli DERA 经典结构 (Heine et al. 2001)
substrate:
  primary_smiles: "C(C=O)Cl"     # chloroacetaldehyde (atorvastatin sequential aldol substrate)
  class: aldehyde / pharmaceutical_intermediate
target_property: substrate_specificity
status: validated
provenance:
  source_type: literature
  doi: "10.1073/pnas.0307563101"
  pmid: null
  citation: "Greenberg WA, Varvak A, Hanson SR, Wong K, Huang H, Chen P, Burk MJ (2004). Development of an efficient, scalable, aldolase-catalyzed process for enantioselective synthesis of statin intermediates. PNAS 101(16):5788-5793."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1073/pnas.0307563101 高把握 (well-cited Diversa paper)"
    - "E. coli DERA UniProt P0A6L0 高把握"
    - "PDB 1JCJ 高把握 (Heine 2001 crystal structure)"
    - "Diversa Corp (后被 Verenium 收购) 与 Burk 团队工作; 后续 Pfizer commercialization"
    - "本工作核心: DERA 自然 substrate 是 acetaldehyde + dihydroxyacetone phosphate, 但工业用作 DOUBLE aldol on chloroacetaldehyde 给 statin 侧链; 设计的是高 substrate 浓度耐受 + double aldol selectivity"
    - "具体 evolved variants 与 mutation 数 (paper 报道 ~5-7 mutations) 见原文 Table"
tags: [aldolase, DERA, deoxyribose_phosphate_aldolase, substrate_specificity, atorvastatin, statin_intermediate, double_aldol, Diversa, non-CAZy, pharmaceutical_industry]
---

## 1. 背景与目标
- parent: E. coli DERA (deoxyribose-5-phosphate aldolase, EC 4.1.2.4, class I aldolase, Schiff base mechanism)
- 天然 reaction: acetaldehyde + glyceraldehyde-3-phosphate → 2-deoxy-D-ribose-5-phosphate
- 工业目标 reaction: chloroacetaldehyde 自反应 (sequential double aldol) 形成 (3R,5S)-6-chloro-2,4,6-trideoxyhexose, 这正是 atorvastatin 侧链前体
- 关键挑战: chloroacetaldehyde 高浓度对 enzyme 毒性 + 单一 enzyme 实现 double aldol 罕见
- 应用: Atorvastatin 工业生产 — 替代多步化学合成

## 2. 决策过程

### 候选位点策略
- **Diversa metagenomic library + directed evolution** 路线:
  1. 起始: E. coli DERA 已知, 天然有部分 promiscuous double aldol 活性
  2. Metagenomic library screen 找 DERA orthologs with 更高 chloroacetaldehyde tolerance
  3. Selected DERA variants 做 directed evolution 进一步提升:
     - High substrate concentration tolerance (chloroacetaldehyde 对 DERA 是 inhibitor)
     - Double aldol selectivity (vs single aldol)
- 累加 ~5-7 mutations

### 排除的位点 (★ 必填)
- Catalytic Lys (Schiff base lysine, K167 in E. coli DERA) 严格保留 — class I aldolase 必需
- TIM barrel 内部 fold-conserved residues 不动
- Substrate-binding aldehyde-acceptor pocket 关键 Asp/Glu (acid-base catalysis) 保留

### 计算工具与阈值
- Structure-guided + metagenomic exploration (Diversa 招牌)
- High-throughput screen: chiral HPLC 测 (3R,5S)-product yield + ee
- 实验校验: 重组表达 in E. coli → 高浓度 chloroacetaldehyde (>0.4 M) 反应 → 实时 HPLC 跟踪 mono- vs di-aldol product

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| WT E. coli DERA chloroacetaldehyde tolerance | 低 (<0.1 M 显著抑制) |
| Engineered DERA tolerance | >0.4 M chloroacetaldehyde |
| Double aldol selectivity | 高 (主要 di-aldol product) |
| (3R,5S) ee | >99% |
| 产品 isolation yield | >85% |
| 工业 conditions | 室温, water/organic biphasic |

### 失败案例 (★ 必填)
- 早期 random mutations 大多 destabilize 或 lose activity — DERA TIM barrel fold 对 mutation 较敏感
- 部分高 tolerance variants 失去 selectivity (mono-aldol 占多) — directed evolution 双指标必要
- Substrate inhibition 即使 in evolved variants 仍存在; high-titer reaction 需要 substrate feed-batch (而不是 batch)

## 4. 学习收获
- **成立的规则候选**:
  - **Aldolase 自然 substrate promiscuity 是工程化起点的金矿** — DERA 类 class I aldolase 天然有 mild promiscuity, 工程化主要是放大 + 优化 selectivity
  - **Sequential / cascade reaction (double aldol)** 用单 enzyme 实现是高 ROI engineering target — 减少 enzyme 数和 process step
  - **Metagenomic ortholog exploration** 是 directed evolution 起手的强 enabler — 找到 inherently better starting point
- **被推翻的假设**:
  - "Aldolase 是高度 specificity, 难做 substrate scope 工程化" — Greenberg 2004 显示 class I aldolase substrate scope 大幅可扩
  - "工业 cascade 必须用多 enzyme" — DERA 单 enzyme 可做 double aldol, 简化流程
- **下次类似问题应优先尝试**:
  - 任何 aldolase 工程化前, 先 metagenomic screen 找 ortholog with 更适合 starting profile
  - High substrate tolerance 是工业 aldolase 工程化 gating spec, 必须 explicitly select for
- **应避免**:
  - 假设 aldolase 工程化只能维持原 specificity — 忽视 cascade reaction 设计可能性
  - 在低 substrate concentration 下评估 — 工业 condition 必须模拟 (high titer + feed strategy)

## 5. 计算 / 实验原始数据
原始 evolved DERA variants + 工业 process 数据见 PNAS 101(16) 2004 supplementary.
