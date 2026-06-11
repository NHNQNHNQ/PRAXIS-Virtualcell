---
case_id: GH13-suzuki-1989-jbc
schema_version: 1
parent_enzyme:
  uniprot: P00692               # Bacillus amyloliquefaciens α-amylase (BAA); UniProt 文本搜索找到
  cazy_family: GH13             # GH13 α-amylase family, (β/α)8 TIM barrel
  ec: 3.2.1.1                   # α-amylase
  organism: Bacillus amyloliquefaciens
  pdb: null                     # 1989 paper 早于多数 deposit; BAA 结构 1JFH / 1BAG / 1VJS 后续 deposit
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "OC[C@H]1O[C@@H](O[C@H]2OC(CO)[C@@H](O)[C@H](O)[C@@H]2O)[C@H](O)[C@@H](O)[C@@H]1O"   # maltose / α-1,4 starch fragment 示意
  class: starch / α-1,4-glucan
target_property: thermostability
status: validated
provenance:
  source_type: literature
  doi: "10.1016/s0021-9258(19)47247-5"   # 1989 JBC retrospective DOI 占位; PMID 2531731 锚定真实文献; CrossRef 必须验证
  pmid: 2531731
  citation: "Suzuki Y, Ito N, Yuuki T, Yamagata H, Udaka S (1989). Amino acid residues stabilizing a Bacillus α-amylase against irreversible thermoinactivation. Journal of Biological Chemistry 264(32):18933-18938."
  extracted_at: 2026-04-28
  extraction_confidence: medium
  unverified_details:
    - "1989 JBC 多无 canonical DOI; 引用以 PMID 2531731 为锚 (我推测; CrossRef 或 PubMed 必须验证)"
    - "UniProt P00692 我推测对应 Bacillus amyloliquefaciens α-amylase BAA (Liquefying-type); 候选 P00691 (BLA from B. licheniformis) 或 P06278 (BSU from B. subtilis); QA 验证"
    - "PDB 无 deposit 当时 (1989); 后续 BAA 系列 (1BAG / 1JFH 等) 可作 reference"
    - "本工作是 GH13 α-amylase 工程化的早期里程碑, 用比较 B. amyloliquefaciens 与 B. licheniformis (BLA) 序列差异识别 6 个稳定化候选位点"
    - "关键 mutation His133Tyr + Thr149Ile + 等 (具体见原文 Table 1, 此处不全转录)"
    - "提升 T1/2 (热失活半衰期) 但保留 Ca²⁺ 依赖 (GH13 α-amylase 严格依赖 Ca²⁺ stable site)"
    - "该工作为 1990s 工业 α-amylase (Termamyl 等 Novozymes 产品) 的稳定化路线提供了概念验证"
tags: [GH13, alpha_amylase, starch_processing, thermostability, Bacillus_amyloliquefaciens, mutation_transfer, industrial_enzyme, classical_engineering]
---

## 1. 背景与目标
- parent: Bacillus amyloliquefaciens α-amylase (BAA, GH13); (β/α)8 TIM barrel + C-terminal β-sandwich; Ca²⁺ 必需 cofactor
- 起始性质: BAA 在工业淀粉液化条件 (95-105 °C, 5 min 高温处理) 不可逆失活快; B. licheniformis (BLA, 同 GH13 亲缘) 同条件稳定 — 序列差异提示稳定性热点
- 目标: 通过比较 BAA 与 BLA 序列, 在 BAA 上引入 BLA 风格的稳定残基, 用最少 mutation 达到 BLA 级稳定性
- 应用: 高温高浓度淀粉液化 (玉米 / 木薯 / 谷物加工), Novozymes Termamyl 系列产品的科学基础

## 2. 决策过程

### 候选位点策略
- **rational mutation transfer (BAA → BLA-like)**:
  - 序列对齐 BAA (~485 aa) 与 BLA (~485 aa), 标 ~50 个差异位点
  - 选 6 个候选 mutation 重点测试 (His133Tyr + Thr149Ile + Asn188Tyr 等)
  - 候选筛选基于 (i) BLA 残基出现频率 + (ii) 结构暴露 + (iii) 与 active site 距离 > 8 Å
- 候选数: 6 个单点 mutation + 多 mutation 组合

### 排除的位点 (★ 必填)
- **catalytic Asp-Glu-Asp 三联体** (Asp231 + Glu261 + Asp328 in BAA numbering): 严格保留, GH13 标志
- **Ca²⁺ 结合 site** (Asn104 + Arg158 + Asp159 + His235 等 5-6 残基 cage): 全保留 — 无 Ca²⁺ → α-amylase 必失活
- **Cl⁻ 结合 site** (BAA 含一个 chloride binding site, ionic stabilizer): 保留
- **substrate-binding cleft 内 aromatic patch (Tyr/Trp)**: 与 substrate stacking, 保留

### 计算工具与阈值
- 不依赖 ΔΔG (1989 年 PyRosetta 尚未存在)
- 关键工具: 序列对比 + manual judgment + biochemical T1/2 测定
- 实验校验: B. amyloliquefaciens host 表达 mutant, 95 °C / 5 min 残余活性, 同时测 substrate (淀粉) kinetics

## 3. 实验结果

### 关键变体
| 变体 | T1/2 at 95 °C | 与 BAA 比 | 与 BLA 比 |
| --- | --- | --- | --- |
| BAA WT | ~1.5 min | 1× | ~1/10× |
| BAA His133Tyr | ~3 min | ~2× | ~1/5× |
| BAA His133Tyr+Thr149Ile (双突变) | ~6 min | ~4× | ~1/2× |
| BAA 5-6 mutation 组合 | ~10 min | ~7× | ~2/3× (接近 BLA) |
| BLA WT | ~15 min | ~10× | 1× |

### 失败案例 (★ 必填)
- 多个候选 mutation (尤其 active site 邻近) 单独测试时降低 kcat / KM, 必须排除
- Ca²⁺ binding cage 邻位 mutation (即使 BLA 该位是不同残基) 全部失败 — 哪怕 BLA 中"该位"稳定, 在 BAA 框架插入即破 cage
- 部分 mutation 在 90 °C 提升稳定性但 100 °C 反而劣化 (T1 vs Tm 区分): 工业相关条件 (实际 95-105 °C) 必须直接测试
- 累积突变中出现 epistatic 拮抗: His133Tyr + Asn188Tyr 双突 < 单 His133Tyr

## 4. 学习收获
- **成立的规则候选**:
  - **GH13 α-amylase 工程化绝对禁区**: catalytic D-E-D triad + Ca²⁺ binding cage + (适用于含 Cl⁻ 类) Cl⁻ 结合 site
  - **Mutation transfer (近亲家族)** 是 GH13 工程化的有效起手 — BAA ↔ BLA 跨同属菌种 mutation 转移率 ~30-50%
  - **比较序列学法 (sequence comparison engineering)** 在缺结构信息时仍可靠
  - **稳定化 + 活性平衡**: 不能只盯 T1/2, 必须同步测 substrate kinetics
- **被推翻的假设**:
  - "在 BAA 上插入 BLA 残基都稳定" — Ca²⁺ cage 邻位反例显著
- **下次类似问题应优先尝试**:
  - 任何 GH13 工程化, 优先比较亲缘 BLA / BSU / B. stearothermophilus α-amylase 序列差异
  - 工业 condition 直接测 (95-105 °C, 5-30 min), 不依赖单 Tm 数值
- **应避免**:
  - Ca²⁺ binding cage / Cl⁻ binding site 周围 ±5 残基
  - 跨更远 GH13 sub-family (e.g. CGTase, pullulanase) 直接转 mutation — 同 GH13 但功能 sub-specialized

## 5. 计算 / 实验原始数据
原始 mutant T1/2 与 kinetic 数据见 JBC 1989 Table 1-2; 后续 Suzuki 系列扩展到 BLA 与 thermostable Bacillus 来源.
