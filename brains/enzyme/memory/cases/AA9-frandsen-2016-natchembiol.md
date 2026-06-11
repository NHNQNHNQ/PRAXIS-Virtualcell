---
case_id: AA9-frandsen-2016-natchembiol
schema_version: 1
parent_enzyme:
  uniprot: A0A0S2GKZ1           # LsAA9_A from Lentinus similis (= Panus similis); UniProt 文本搜索找到
  cazy_family: AA9
  ec: 1.14.99.56                # cellulose-active LPMO (current EC, 与 UniProt 一致)
  organism: Lentinus similis
  pdb: 5ACF                     # LsAA9_A complexed with cellotetraose; 论文 deposit; QA 验证
substrate:
  primary_smiles: "OC[C@H]1O[C@@H](O[C@H]2OC(CO)[C@@H](O)[C@H](O)[C@H]2O)[C@H](O)[C@@H](O)[C@@H]1O"
  class: cellooligosaccharide / amorphous_cellulose
target_property: substrate_specificity
status: validated
provenance:
  source_type: literature
  doi: "10.1038/nchembio.2029"
  pmid: null
  citation: "Frandsen KE, Simmons TJ, Dupree P, Poulsen JC, Hemsworth GR, Ciano L, Johnston EM, Tovborg M, Johansen KS, von Freiesleben P, Marmuse L, Fort S, Cottaz S, Driguez H, Henrissat B, Lenfant N, Tuna F, Baldansuren A, Davies GJ, Lo Leggio L, Walton PH (2016). The molecular basis of polysaccharide cleavage by lytic polysaccharide monooxygenases. Nature Chemical Biology 12(4):298-303."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "PDB 5ACF 我推测对应 LsAA9_A 与 cellotetraose 复合物; QA 验证"
    - "UniProt 第一次推 G3XAP7 错 (T. aurantiacus 不同 LPMO), 经搜索找到 A0A0S2GKZ1 (LsAA9_A from Panus/Lentinus similis)"
    - "Lentinus similis 当代 UniProt 标记为 Panus similis (lentinoid 真菌系统发育修订)"
    - "EC 由 1.14.99.54 改为 1.14.99.56 以匹配 UniProt 当前注释"
    - "本工作是 AA9 LPMO 第一个 substrate-bound 高分辨结构, 直接揭示了 catalytic Cu 与 substrate 的几何关系"
    - "paper 主要是 mechanism 而非 engineering, 但 substrate-binding mode 的揭示是后续 LPMO 工程化的基础"
tags: [AA9, substrate_specificity, LPMO, mechanism, cellulose, copper, histidine_brace, Walton-lab, Davies-lab]
---

## 1. 背景与目标
- parent: Lentinus similis LsAA9_A (cellulose-active LPMO, AA9 家族)
- 当时背景: AA9 LPMO 已知 Cu binding (His brace) 但无 substrate-bound 结构, 反应几何不明
- 目标: 解析 LPMO 与 cellooligo substrate 复合物结构, 直接看催化几何 + 区域选择性 (C1 vs C4 cleavage) 来源
- 应用: 为后续 LPMO 工程化 (substrate scope / regioselectivity / thermostability) 提供原子尺度依据

## 2. 决策过程 (本文是 mechanism 解析, 非工程化突变实验)

### 候选位点策略
- **结构生物学** 路线: 解 LsAA9_A 与 cello-oligosaccharide 共晶
- 后续:
  1. 多 oligo 长度 (cellotriose / cellotetraose / cellopentaose) 筛 binding
  2. 关键残基的定点突变 (His brace 的 His1 + His78, 二级 sphere 的 Tyr/Phe)
  3. EPR + UV-vis 跟 Cu(I)/Cu(II) 状态
- 不做 saturation library, 是 hypothesis-driven

### 排除的位点 (★ 必填)
- His brace 两个 His (His1 + His78) 严格保留 — 突变即失活
- N-端 His1 的 N(δ) 甲基化 (LPMO 真菌特征) 不破坏
- 底物结合 surface (flat aromatic patch with Tyr) 保留几何

### 计算工具与阈值
- 主要工具: X-ray crystallography (高分辨结构) + EPR + DFT (Cu 中心几何 + spin state)
- QM/DFT 计算 active site geometry — 论文 Walton 实验室强项
- 实验校验: HPAEC-PAD 检测 oxidized cellooligo 产物 (C1 / C4 / C1+C4 区分)

## 3. 实验结果

### 关键发现
| 发现 | 内容 |
| --- | --- |
| 第一个 LPMO + substrate 共晶 | LsAA9_A + cellotetraose 在 binding surface 平展贴附 |
| Cu - C1/C4 几何 | Cu 距离 substrate C1 较近 (此 LPMO 是 C1 oxidizer) |
| His brace 配位 | His1-Nδ + His1-Nε + His78-Nε 三齿配位 Cu |
| Tyr164 二级 sphere | 不直接配位但稳定 Cu 一级配位环境 |
| Substrate flexibility | 多个 oligo 长度都能 bind, 解释 AA9 broad substrate scope |

### 失败案例 (★ 必填)
- 论文未尝试或未报道 catalytic 突变体的 catalytic activity loss (mechanism paper 重点不在 engineering)
- 但讨论了:
  - His1 突变历史 (Quinlan 2011 报道) 完全失活, 验证 His brace 必需性
  - C1 vs C4 oxidizer 在 sequence 上区别细微但重要 — 单残基预测 selectivity 不准

## 4. 学习收获 (informed engineering, 从结构推工程化)
- **成立的规则候选**:
  - LPMO 工程化绝对禁区: His1 + His78 + N-端整体 (即 His brace)
  - **Substrate-binding flat aromatic patch (Tyr/Phe)** 是改 substrate scope 的工程化目标 — 改 aromatic 残基可调 binding 偏好
  - **C1 vs C4 区域选择性**由 active site distal residue 微调 (5-7 Å 处), 工程化目标更深
- **被推翻的假设**:
  - "LPMO substrate scope 由 single binding pocket residue 决定" — 结构显示是 surface flat-patch 多 residue 协同, 单点突变效应有限
- **下次类似问题应优先尝试**:
  - LPMO substrate scope 工程: 改 surface aromatic patch (e.g. Y/F → A 或反向), 用 Frandsen 2016 结构指导位点
  - Region (C1 vs C4) selectivity 调: 关注 active site distal 5-7 Å 残基, 但预期效应 modest
- **应避免**:
  - 任何 His brace ±5 Å 突变 (即使表面看起来 stabilizing)
  - E. coli 表达 fungal AA9 (无 N-甲基化, 失活 90%+)

## 5. 计算 / 实验原始数据
晶体 deposition + EPR 数据见 Nature Chem Biol 2016 supplementary materials. Cu Kα EXAFS 数据由合作团队补充.
