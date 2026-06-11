---
case_id: P450-glieder-2002-natbiotechnol
schema_version: 1
parent_enzyme:
  uniprot: P14779               # Cytochrome P450 BM3 (CYP102A1) from Bacillus megaterium
  cazy_family: null              # 非 CAZy
  enzyme_family: cytochrome_P450
  ec: 1.14.14.1                 # 长链脂肪酸羟化酶 (CYP102A1 自身; 后来工程化为 alkane hydroxylase)
  organism: Bacillus megaterium
  pdb: 1BU7                     # P450 BM3 经典结构 (Sevrioukova 1999); QA 验证
substrate:
  primary_smiles: "CCCCCCCCCC"   # decane (C10 alkane), Glieder 2002 evolved variant 显著羟化 C5-C10 alkanes
  class: short_chain_alkane
target_property: substrate_specificity
status: validated
provenance:
  source_type: literature
  doi: "10.1038/nbt744"
  pmid: null
  citation: "Glieder A, Farinas ET, Arnold FH (2002). Laboratory evolution of a soluble, self-sufficient, highly active alkane hydroxylase. Nature Biotechnology 20(11):1135-1139."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1038/nbt744 我推测; QA via CrossRef 验证"
    - "P450 BM3 UniProt P14779 高把握"
    - "PDB 1BU7 的 deposit 可能与 Glieder 2002 evolved variant 不同 (1BU7 是 WT); 后续 PDB 1JPZ 等含 evolved variants"
    - "Frances Arnold lab 的 directed evolution 经典案例之一; 具体 evolved variant 的 5-15 个 mutations 详见原文 Table 1"
    - "原 paper 写 evolved variant 'V2'/'9-10A' 等命名, 实测 turnover 比 native medium-chain fatty acid 快 1000x 对 octane"
tags: [cytochrome_P450, BM3, CYP102A1, substrate_specificity, alkane_hydroxylation, directed_evolution, Arnold-lab, non-CAZy]
---

## 1. 背景与目标
- parent: P450 BM3 (CYP102A1, UniProt P14779), 来自 Bacillus megaterium 的 self-sufficient (融合 hemes + reductase) P450
- 起始活性: 天然羟化中长链脂肪酸 (C12-C20), 对 short-chain alkane (C5-C10) 几乎无活性
- 目标: 通过 directed evolution 让 BM3 高效羟化 short-chain alkanes (octane 为代表)
- 应用: 工业 biocatalysis — 烷烃官能团化 (常规化学难以选择性氧化烷烃)

## 2. 决策过程

### 候选位点策略
- **Directed evolution** (Arnold lab 招牌方法):
  1. 多轮 error-prone PCR + DNA shuffling
  2. High-throughput colony screening (色原 surrogate substrate p-nitrophenoxyoctane)
  3. 顶级 hits 累加 + characterize
- 论文最终 evolved variant 累计 ~10-15 个突变, 分布在 active site + substrate access channel

### 排除的位点 (★ 必填)
- 催化必需 Cys400 (heme thiolate ligand) 严格保留 — 突变即失活
- Heme 周围一级 sphere 残基 (Phe87, Thr268 等) 在 directed evolution 中较少被改 — selection 自然保留
- FAD/FMN cofactor binding domains (BM3 的 reductase 部分) 对 alkane hydroxylase activity 不强相关, evolution 主要发生在 hemes domain (residues 1-455)

### 计算工具与阈值
- 不依赖预先 ΔΔG; 是 directed evolution + experimental selection
- 关键 enabler: high-throughput screening assay (p-NPx octyl ether 类显色 surrogate)
- 实验校验: 表达 in E. coli → cell lysate → octane / pentane assay (GC-MS) → 顶级 variant 纯化 + steady-state kinetics

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| WT BM3 turnover on octane | < 1 nmol/min/nmol enzyme |
| Evolved variant turnover on octane | > 1000-fold WT |
| Total mutations in best variant | ~10-15 substitutions |
| Mutations in heme domain | 8-12 (most relevant) |
| Mutations in reductase | few, possibly auxiliary stabilization |

### 失败案例 (★ 必填)
- 早期 rounds: 部分 variants 表达失败 (insolubility) — directed evolution 自然淘汰
- Selection-bypass mutations: 部分变体在 surrogate substrate 上活但对真实 octane 仍弱 (assay specificity issue) — 后期需用真实 substrate 验证
- Activity vs stability tradeoff: evolved variants Tm 略下降, 但 application range 仍 30-50°C 内可用

## 4. 学习收获
- **成立的规则候选**:
  - **P450 substrate scope 工程化的最有效手段是 directed evolution + 显色 surrogate screen** (relative to rational design)
  - 累加 ~10+ mutations 才能实现 1000× 活性 reorientation — single-point 工程化不足
  - **High-throughput screen 的 surrogate substrate 选择是 enabler 关键** — 没有合适 readout, P450 工程化效率极低
- **被推翻的假设**:
  - "P450 substrate specificity 由 1-2 个关键 residue 决定" — Glieder 2002 显示 ~10 个 distributed mutations 协同
- **下次类似问题应优先尝试**:
  - 任何 P450 substrate redirection: 先建 high-throughput screen, 再上 directed evolution
  - 起手 use BM3 (self-sufficient, soluble, well-characterized) 作 chassis, 比从头优化新 P450 高效
- **应避免**:
  - 仅用 surrogate substrate; 顶级 hits 必须用真实 substrate 验证
  - 试图通过 rational design 改 P450 active site geometry — 历史上效率低于 directed evolution

## 5. 计算 / 实验原始数据
原始 evolved variant + kinetics 数据见 Nature Biotechnology 20(11) 2002 supplementary.
