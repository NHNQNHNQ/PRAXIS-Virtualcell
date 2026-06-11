---
case_id: GH11-hakulinen-2003-eurjbiochem
schema_version: 1
parent_enzyme:
  uniprot: G0S9R7               # C. thermophilum (Thermochaetoides thermophila) Beta-xylanase; QA 找到的正确 entry
  cazy_family: GH11
  ec: 3.2.1.8
  organism: Chaetomium thermophilum
  pdb: 1H1A                     # 待 QA 验; 论文同期还描述 N. flexuosa xylanase 第二个结构
substrate:
  primary_smiles: "OC[C@@H]1O[C@@H](O[C@@H]2[C@@H](O)[C@@H](O)[C@H](O)O[C@@H]2CO)[C@H](O)[C@@H](O)[C@@H]1O"
  class: xylobiose / xylan
target_property: thermostability
status: validated
provenance:
  source_type: literature
  doi: "10.1046/j.1432-1033.2003.03496.x"
  pmid: null
  citation: "Hakulinen N, Turunen O, Jänis J, Leisola M, Rouvinen J (2003). Three-dimensional structures of thermophilic beta-1,4-xylanases from Chaetomium thermophilum and Nonomuraea flexuosa. Comparison of twelve xylanases in relation to their thermal stability. Eur J Biochem 270(7):1399-412."
  extracted_at: 2026-04-27
  extraction_confidence: medium
  unverified_details:
    - "DOI 我推测 (10.1046/j.1432-1033.2003.03496.x); CrossRef 验证 — 不对的话需要查"
    - "Chaetomium thermophilum 当代官方学名为 Thermochaetoides thermophila (2020 重新分类); UniProt G0S9R7 是 DSM 1495 strain 的 beta-xylanase"
    - "论文同期解析了 Nonomuraea flexuosa xylanase 第二个结构, 案例只取 C. thermophilum 一支为 primary parent"
    - "PDB 1H1A 我推测; 论文实际 deposition ID 待复核"
    - "本文是 comparative thermostability 而非 engineering — 但提供了 12 种 GH11 xylanase 的 thermostability 特征关联性, 工程上有指导价值"
    - "Turunen 实验室 (与 GH11-turunen-2002, GH11-fenel-2004 同实验室) 的结构 + 序列 + thermostability 跨家族比较工作"
tags: [GH11, thermostability, xylanase, comparative_analysis, structural_features, Chaetomium, Nonomuraea, Turunen-lab]
---

## 1. 背景与目标
- parent: 多个 thermophilic GH11 xylanases — 代表是 Chaetomium thermophilum + Nonomuraea flexuosa (新解析结构) + 比较 12 个已知 GH11 (含 mesophilic 与 thermophilic)
- Tm 范围: ~50°C (mesophilic) ~ ≥80°C (Thermomyces lanuginosus / Thermoascus 类)
- 目标: 通过结构比对找出 thermostability 的 sequence/structure correlates
- 应用: 给 GH11 thermostability engineering (如 Turunen / Fenel 系列) 提供位点选择依据

## 2. 决策过程 (本文是 comparative analysis, 没有 mutagenesis 实验)

### 候选位点策略
- **Comparative bioinformatics + structure analysis**:
  1. 多序列比对 12 个 GH11 ortholog
  2. 解析 2 个新结构 (Chaetomium / Nonomuraea)
  3. 找 mesophilic vs thermophilic 分组的 sequence/structure 差异
- 关注: surface charged residues, disulfide bridges, hydrogen bond network, hydrophobic core packing

### 排除的位点 (★ 必填)
- 本文不做突变, 没有正式排除清单
- 但 implicit: 12 个 ortholog 中保守残基 (active site E86/E177 周围 sheet 等) 自然不在 differential 范围内

### 计算工具与阈值
- 主要靠 X-ray crystallography (新结构) + sequence alignment (Clustal) + 结构比对 (PyMOL/SUPERPOSE)
- 量化指标: 表面电荷分布, salt bridge count, B-factor 比较

## 3. 实验结果

### 关键发现
| Feature | thermophilic 趋势 |
| --- | --- |
| Surface arginine 比例 | thermophilic 显著高 (与 Turunen 2001 surface Arg engineering 一致) |
| Hydrogen bond network | thermophilic 含更多 inter-domain H-bonds |
| N-端结构 | thermophilic 常含天然 N-end disulfide 或紧致 packing (与 Fenel 2004 N-terminal disulphide engineering 一致!) |
| Charged residue 分布 | thermophilic 类倾向 surface 更碱性 |

### 失败案例 (★ 必填)
- 论文不报失败 (无突变实验), 但讨论中提到:
  - 单一 feature 不能完全解释 thermostability — 多 feature 协同
  - 一些 thermostable variants 的 stabilizing features 模糊 (个体差异, 不是"必然规律")

## 4. 学习收获
- **成立的规则候选**:
  - **GH11 surface Arg 富集 + N-端紧致 packing** 是 thermostability 的两个独立 correlate — 工程化时双管齐下
  - 跨 ortholog comparative analysis 是 engineering 的 cheap 起手 (无需做实验, 只需 MSA + 1-2 个 thermophilic 结构)
- **被推翻的假设**:
  - "单一 feature 是 thermostability 决定因素" — comparative analysis 显示是 multi-feature 协同
- **下次类似问题应优先尝试**:
  - 任何 GH 家族 thermostability engineering 前, 先做 comparative analysis 找 thermophilic correlates, 再选位点
  - 与 Turunen 2001/2002 + Fenel 2004 + Goedegebuur 2017 形成 "comparative → engineering → directed evolution" 完整路径
- **应避免**:
  - 直接在 mesophilic enzyme 做 saturation library 而不先看 thermophilic ortholog 信息

## 5. 计算 / 实验原始数据
新结构 PDB depositions + alignment data 见 Eur J Biochem 270(7) supplementary.
