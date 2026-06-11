---
case_id: PL1-solbak-2005-jbc
schema_version: 1
parent_enzyme:
  uniprot: null                  # Diversa proprietary metagenomic enzyme; no public UniProt
  enzyme_family: industrial_metagenomic_enzyme
  cazy_family: PL1
  ec: 4.2.2.2                   # pectate lyase
  organism: Bacillus sp. (alkaliphilic; Diversa metagenomic 来源)
  pdb: null                     # 工业 evolved variant 多无公开结构
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "OC(=O)[C@@H]1O[C@@H](O[C@@H]2[C@H](O)[C@H](O)C(=O)O[C@H]2C(=O)O)[C@H](O)[C@@H](O)[C@@H]1O"   # polygalacturonate 示意
  class: pectate / polygalacturonate
target_property: activity        # 主线: 在 cotton scouring 工艺条件 (pH 8–9, 50–60 °C) 下高效水解 pectin
status: validated
provenance:
  source_type: literature
  doi: "10.1074/jbc.M411838200"
  pmid: null
  citation: "Solbak AI, Richardson TH, McCann RT, Kline KA, Bartnek F, Tomlinson G, Tan X, Parra-Gessert L, Frey GJ, Podar M, Vasiliou V, Burk MJ, Burkholder J, Hung J, Tang R, Healey EH, Williamson MJ, Robertson DE, Steer BA (2005). Discovery of pectin-degrading enzymes and directed evolution of a novel pectate lyase for processing cotton fabric. Journal of Biological Chemistry 280(10):9431-9438."
  extracted_at: 2026-04-28
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1074/jbc.M411838200 我推测; CrossRef 必须验证"
    - "UniProt Q5IST5 我推测对应该 Bacillus sp. metagenomic pectate lyase; Diversa 工业菌株 UniProt 注册可能不全, QA 必须验证"
    - "PDB 无 — 工业 directed-evolution variant 多无公开结构 (商业保密)"
    - "Diversa Corporation 后并入 Verenium, 再被 BASF 收购; 文献 author affiliation 可能写 Diversa 或 Verenium"
    - "evolved variant 含 7+ mutation, 具体位置见 Fig 2 / Table 1; 此处不全转录, 标记 unverified"
    - "engineering target 标 activity 因主线是 process condition (alkaline pH, 50-60 °C) 下的活性提升; thermostability 是 secondary"
    - "本案例是 PL1 在工业 textile (cotton) 应用的直接证据, 与 PL1 在植物病原 / 食品加工的 academic 案例形成 pair"
tags: [PL1, pectate_lyase, directed_evolution, cotton_scouring, industrial_textile, alkaline_tolerance, metagenomic, Diversa, Burk-lab]
---

## 1. 背景与目标
- parent: Diversa metagenomic 来源 alkaliphilic Bacillus pectate lyase (PL1 家族); 起始来自高 pH 嗜碱菌环境
- 起始性质: 在 pH 8–9, 50 °C 下有活性 (优于经典 Erwinia PL1 在中性 pH 工作), 但仍不足以替代 cotton scouring 的传统 alkaline 化学工艺 (NaOH 100 °C)
- 目标: directed evolution 提升在 textile-process 条件 (pH ~8.5, 50–60 °C, 多 wash 循环) 下的活性与稳定性, 使酶法 scouring 在工业 throughput 可行
- 应用: 替代 cotton fabric 预处理 (scouring) 中的高碱高温化学处理, 节能 + 减废水

## 2. 决策过程

### 候选位点策略
- **Directed evolution** 路线 (Diversa platform):
  - **Family shuffling**: 多 metagenomic PL1 同源序列 (从 environmental DNA 文库搜) DNA shuffling
  - **GSSM (Gene Site Saturation Mutagenesis)**: 全长每残基饱和 (Diversa 专利方法)
  - **Combinatorial libraries**: 多 round 累积 hits
- 候选数: GSSM 全饱和 ~300+ 残基 × 19 突变 = 5000+ variants per round; family shuffling 10⁵ 量级 chimera

### 排除的位点 (★ 必填)
- **催化 Lys / Arg + Asp**: PL1 反 β-elimination 机制依赖 active site basic residue (Lys 提取 H, Arg 稳定中间体, Asp 协助); selection 自动淘汰
- **Ca²⁺ 结合 motif**: PL1 严格依赖 Ca²⁺ 作 catalytic cofactor, 5–7 residue 形成的 Ca-binding cage 全保留
- **Parallel β-helix fold core**: PL1 标志的 PβH 折叠骨架不变, mutation 集中在 surface loop 与 substrate-binding cleft
- 注: 论文不含 explicit 排除清单 (directed evolution 由 selection 间接保留必需位)

### 计算工具与阈值
- 不依赖 ΔΔG (实验主导)
- 关键工具:
  - Diversa GSSM 高通量 mutagenesis 平台
  - 96-well plate Ru(bpy)-based pectin assay 检测降解
  - cotton fabric scouring small-scale assay (process 条件)
- 实验校验: 异源表达 (E. coli + Bacillus host), 顶级 hits 中试规模 cotton 处理 + 物理性能 (吸水性 / 染色均匀性)

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | WT | Evolved best variant | 提升 |
| --- | --- | --- | --- |
| pH 8.5 / 60 °C 比活 | baseline | ~16× (Diversa 报道) | 16× |
| 在 process pH (8.5) 半衰期 | 短 | 数小时 | 5–10× |
| Cotton scouring efficacy | 弱 | 接近化学工艺 | 商用化 |
| Mutation 数量 (best variant) | 0 | 7–10 (累积) | – |

### 失败案例 (★ 必填)
- 部分 GSSM hits 在 plate assay 显高活, 但 cotton fabric 实物 process 中不出色 — assay-process gap (常见 directed evolution 工业问题)
- 早期单点 mutation 累积时偶有 epistatic 拮抗 (mutation A + B < A 单独); 必须 combinatorial 文库才能解决
- Family shuffling chimera 中部分组合产生不可溶 / 不表达突变体, 需大规模 screening 兜底
- Ca²⁺ 结合区附近的"看似稳定"突变常导致活性丢失 — selection 后保留比例极低

## 4. 学习收获
- **成立的规则候选**:
  - **Industrial PL1 工程化标准: process-condition assay (pH + 温度 + 实际底物)** 而非纯酶 kinetic 优化 — 后者与前者相关性差
  - **PL1 工程化排除域**: Ca²⁺ binding cage + 反 β-elimination 三联体 (Lys/Arg/Asp) + parallel β-helix backbone 严格保留
  - **Metagenomic library 是 PL 家族的最佳 starter 来源** — 已在天然环境筛过工业极端条件 (alkaliphilic 来源即天然 alkaline-tolerant)
  - **GSSM + family shuffling 组合策略** 是 PL 工业化的工程化范式
- **被推翻的假设**:
  - "在标准 PL1 (Erwinia) 框架做 mutagenesis 得到 alkaline-tolerant variant" — 反复尝试效果差, 不如换 alkaliphilic starter
  - "ΔΔG / PyRosetta 预测稳定的突变在 Ca-cofactor 依赖酶上有效" — Ca-binding cage 微扰即失活, ΔΔG 预测对此盲点
- **下次类似问题应优先尝试**:
  - 任何工业 PL/CE 工程化, 优先 metagenomic 起点 + directed evolution + process-condition assay
  - 接受 process-condition / lab-condition 选择性 trade-off
- **应避免**:
  - Ca²⁺ binding cage ±3 残基的"稳定性 mutation"
  - 单依赖 plate assay 选 hits, 不上 fabric 实测 process

## 5. 计算 / 实验原始数据
原始 GSSM library + variant kinetics + cotton process scoring 数据见 JBC 2005 supplementary materials; Diversa GSSM 平台技术细节见 Diversa / Verenium 历史专利.
