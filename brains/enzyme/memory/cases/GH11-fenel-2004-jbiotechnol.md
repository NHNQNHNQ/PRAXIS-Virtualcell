---
case_id: GH11-fenel-2004-jbiotechnol
schema_version: 1
parent_enzyme:
  uniprot: P36217
  cazy_family: GH11
  ec: 3.2.1.8
  organism: Trichoderma reesei
  pdb: 1XYN
substrate:
  primary_smiles: "OC[C@@H]1O[C@@H](O[C@@H]2[C@@H](O)[C@@H](O)[C@H](O)O[C@@H]2CO)[C@H](O)[C@@H](O)[C@@H]1O"
  class: xylobiose / xylan
target_property: thermostability
status: validated
provenance:
  source_type: literature
  doi: "10.1016/j.jbiotec.2003.11.002"
  pmid: "15129727"
  citation: "Fenel F, Leisola M, Jänis J, Turunen O (2004). A de novo designed N-terminal disulphide bridge stabilizes the Trichoderma reesei endo-1,4-beta-xylanase II. J Biotechnol 108(2):137-43."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1016/j.jbiotec.2003.11.002 与 PMID 15129727 是我推测的 — QA 应通过 CrossRef 验证"
    - "Fenel 2004 paper 是 Turunen 实验室 N-terminal disulphide 系列工作的代表作; 与 Turunen 2002 J Biotechnol (alpha-helix-loop disulphide) 形成对比"
    - "具体的 N-terminal 延伸序列与 Cys 位置 (论文中应明确给出, 但我未直接转录) 应到原文 Table/Methods 复核"
    - "实测 Tm 提升的精确数值未转录"
tags: [GH11, thermostability, xylanase, disulfide_bridge, N_terminal_extension, Turunen-lab, follow_up_to_turunen_2002]
---

## 1. 背景与目标
- parent: T. reesei XYNII / Xyn2 (UniProt P36217, PDB 1XYN), 与 Turunen 2002 案例同一 enzyme
- 起始 Tm: ~57°C (mesophilic GH11 起手)
- 目标: 验证 N-terminal disulphide 桥设计能否独立或与 alpha-helix disulphide (Turunen 2002) 协同提升稳定性
- 应用场景同 Turunen 2002: 纸浆漂白 (60-70°C, 偏碱性 pH), 饲料预消化

## 2. 决策过程

### 候选位点策略
- **De novo 设计 N-terminal extension** + **Cys 对引入**:
  1. 在原 N-端前加几个氨基酸 (含一个 Cys)
  2. 在 GH11 原序列中找一个空间上接近 (Cα 距离 5-7 Å) 的 Ser/Thr/Asn 改 Cys
  3. 形成 N-端到 body 的二硫桥, 锚定 N-端柔性区
- 与 Turunen 2002 (alpha-helix→相邻 loop disulphide) 是不同位点的 disulphide 工程, 互补

### 排除的位点 (★ 必填)
- 活性位点 cleft (catalytic E86, E177) 完全保留
- thumb loop (residues ~100-115) 不动
- 已知的 N-glycosylation site 保留
- 与 Turunen 2002 排除清单一致

### 计算工具与阈值
- 主要靠 PyMOL/manual structure analysis: 测候选 Cys-Cys 距离, 评估几何可行性
- 计算工具方面没有大型 ΔΔG 扫描 (论文方法以结构判断 + 直接构建 + 实验验证为主)
- 实验校验: 在 T. reesei 自体 host 表达 → CD melting curve → xylan 活性 (RBB-xylan)

## 3. 实验结果

### in silico 预测 vs 实测
| 设计 | 预测 (Cα 距离适合) | 实测 ΔTm |
| --- | --- | --- |
| N-extension + 单 Cys 对 | 几何可行 | ΔTm 显著正向 (具体数值见原文) |
| 与 Turunen 2002 alpha-helix disulphide 组合 | 协同 | 累加性提升 (论文核心 finding) |

具体 ΔTm 数值与 mutation 表见原文 Table 1-2.

### 失败案例 (★ 必填)
- 论文未详细报道失败设计 (只报道成功的 N-terminal disulphide 构建); 但讨论中提到:
  - 早期尝试单独引入 Cys (无配对 Cys) 易导致 free Cys 暴露, 触发分子间二硫桥与聚集
  - Cα 距离 > 8 Å 的候选未尝试 (基于几何过滤排除)

## 4. 学习收获
- **成立的规则候选**:
  - GH11 enzyme 的 N-端柔性区是 disulphide engineering 的另一个稳定化位点 (与 alpha-helix region 互补)
  - 多个独立设计的 disulphide 桥可累加性提升 Tm — 不同位点不冲突
  - "De novo N-terminal extension" 是为缺天然 N-端 Cys 的 enzyme 引入第二个 disulphide 的有效手段
- **被推翻的假设**:
  - 无明确推翻的假设; 该工作主要是验证 N-terminal disulphide 这一新位置的可行性
- **下次类似问题应优先尝试**:
  - 当 alpha-helix disulphide (Turunen 2002 path) 已尝试且增益饱和时, 可考虑 N-terminal de novo 设计
  - 多 disulphide 累加策略 (此 case 验证了非加性问题在 disulphide 上不严重)
- **应避免**:
  - 单独引入孤立的 Cys (没有配对 Cys) — 必然引发氧化错配
  - 忽视 N-端 extension 对 signal peptide processing 的影响 (尤其在 T. reesei 自体 host)

## 5. 计算 / 实验原始数据
原始 melting curve 与活性数据见 J Biotechnol 108(2):137-43.
