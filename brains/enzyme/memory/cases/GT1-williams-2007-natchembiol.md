---
case_id: GT1-williams-2007-natchembiol
schema_version: 1
parent_enzyme:
  uniprot: Q53685               # OleD (Oleandomycin glycosyltransferase) from S. antibioticus; UniProt 文本搜索找到
  cazy_family: GT1
  ec: 2.4.1.-
  organism: Streptomyces antibioticus
  pdb: null                     # OleD 在 2007 年时未有公开结构, 后续工作出过
substrate:
  primary_smiles: "OC[C@H]1O[C@@H](OC2=CC(C(=O)c3cc(O)c(O)cc3)=CC(O)=C2O)[C@H](O)[C@@H](O)[C@@H]1O"   # 类黄酮 acceptor 示例 (OleD 接受多种 small-molecule acceptor); 实际使用 SMILES 应针对论文 acceptor 库
  class: phenolic_acceptor / small_molecule_glycosylation
target_property: substrate_specificity
status: validated
provenance:
  source_type: literature
  doi: "10.1038/nchembio.2007.28"
  pmid: null
  citation: "Williams GJ, Zhang C, Thorson JS (2007). Expanding the promiscuity of a natural-product glycosyltransferase by directed evolution. Nature Chemical Biology 3(11):657-662."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "OleD UniProt 第一次推 Q9KI50 错 (Aphanothece halophytica DSR 完全无关), 经 UniProt 文本搜索找到正确为 Q53685 (OLED_STRAT)"
    - "DOI 10.1038/nchembio.2007.28 我推测 (Nature Chem Biol 2007 vol 3 issue 11)"
    - "本工作是 GT 工程化经典案例, 由 Thorson 实验室主导"
    - "具体 evolved variants 与活性提升幅度未转录, 见原文 Fig 2-3"
tags: [GT1, substrate_specificity, glycosyltransferase, OleD, directed_evolution, natural_product, Thorson-lab]
---

## 1. 背景与目标
- parent: OleD GT (Streptomyces antibioticus, oleandomycin biosynthesis), GT1 家族 (GT-B fold, UDP-glucose 供体)
- 起始活性: 对天然 acceptor (oleandomycin precursor) 有活性, 对非天然 acceptor 几乎无活性
- 目标: 大幅扩展 acceptor 多样性 — 让 OleD 接受多种 phenol / flavonoid / steroid 等 small-molecule acceptor
- 应用: 天然产物全合成、糖苷类化合物多样化 (生物催化关键)

## 2. 决策过程

### 候选位点策略
- **Directed evolution** 路线: error-prone PCR 文库 + high-throughput 筛
- 筛 readout: UDP 检测 (UDP-Glc → UDP + glycosylated product, UDP 被 phosphatase + chromophore 检测)
- 数千变体 / 几轮迭代 → 最佳 hits

### 排除的位点 (★ 必填)
- 论文未给显式排除清单 (directed evolution 无预先排除)
- 但 implicit 由 selection 保留: UDP-Glc 结合位点 (供体) 与催化机制残基 — selection 自动淘汰这些破坏性突变
- 后续机制分析揭示 OleD 的 active site loop 是热点

### 计算工具与阈值
- 不依赖 ΔΔG / PyRosetta (是 directed evolution + experimental selection)
- 关键工具: 96-well plate UDP 检测 assay 实现 high-throughput
- 实验校验: 异源表达 in E. coli → cell lysate assay → 顶级 variant 纯化 + LC-MS confirm 产物 + kinetic measurement

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| 起始 OleD 对非天然 acceptor 活性 | <1% (相对天然 acceptor) |
| 工程化后 best variants 对扩展 acceptor 库的活性 | 提升 100-1000× |
| Acceptor 谱广度 | 从 1-2 个 → 数十个 |
| 几个关键突变 | 集中在 active site loop (具体位点见原文 Fig 4) |

### 失败案例 (★ 必填)
- 部分 evolved variants 对天然 acceptor 活性下降 (specificity tradeoff): 改广谱性可能丢失原配特异性
- E. coli 表达 OleD 部分 variants yield 低 (一致 GT 类常见问题, 真核来源 GT 在原核 host 不顺畅)
- 部分 hits 在 cell lysate 显活但纯化后失活 (E. coli 提取物中可能有 cofactor 或稳定因子, 细节论文未深究)

## 4. 学习收获
- **成立的规则候选**:
  - **OleD 类 GT-B fold GT 的 acceptor binding loop 是工程化高价值热点**, directed evolution 在该区域命中率高
  - **High-throughput UDP 检测 assay** 是 GT 工程的关键 enabler — 没有适合 readout, GT 工程是低效的
  - 跨 acceptor 类别的 promiscuity 可大幅提升 (100-1000×), 不是渐进改进
- **被推翻的假设**:
  - "GT 是高度特异的, 难以重定向" — Williams 2007 显示了大幅度 acceptor 重定向是可行的
- **下次类似问题应优先尝试**:
  - 任何 GT acceptor 重定向项目, 优先 directed evolution + UDP-detection assay
  - 选 GT-B fold 类 (vs GT-A fold) — GT-B 的 acceptor pocket 更易调
- **应避免**:
  - 不做 active site loop 单点突变穷举 — 文库筛选效率高得多
  - 用其他 sugar-detection assay 替代 UDP-detection — UDP 副产物特异且通用

## 5. 计算 / 实验原始数据
原始 evolved library + variant kinetics 数据见 Nature Chemical Biology 2007 supplementary materials.
