---
case_id: CE7-vincent-2003-jmolbiol
schema_version: 1
parent_enzyme:
  uniprot: P94388                # B. subtilis acetyl xylan esterase / cephalosporin C deacetylase; QA 验证
  cazy_family: CE7
  ec: 3.1.1.72                  # acetylxylan esterase (与 cephalosporin C deacetylase 双活性)
  organism: Bacillus subtilis
  pdb: 1ODS                     # Vincent 2003 deposition; QA 验证
substrate:
  primary_smiles: "CC(=O)O[C@H]1[C@H](O)[C@@H](O[C@H]2OC(CO)[C@@H](O)[C@H](O)[C@H]2O)O[C@@H](CO)[C@@H]1O"   # 2-O-acetyl-xylobiose (示意; CE7 实际接受 acetyl-substituted xylan oligosaccharides)
  class: acetyl_xylooligosaccharide / cephalosporin_C
target_property: substrate_specificity
status: validated
provenance:
  source_type: literature
  doi: "10.1016/s0022-2836(03)00632-6"
  pmid: null
  citation: "Vincent F, Charnock SJ, Verschueren KH, Turkenburg JP, Scott DJ, Offen WA, Roberts S, Pell G, Gilbert HJ, Davies GJ, Brannigan JA (2003). Multifunctional xylooligosaccharide/cephalosporin C deacetylase revealed by the hexameric structure of the Bacillus subtilis enzyme at 1.9 Å resolution. J Mol Biol 330(3):593-606."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 第一次推 00876-1 错, CrossRef 文本搜索后改为 10.1016/s0022-2836(03)00632-6"
    - "B. subtilis Bxe 类酶 UniProt P94388 我推测; 候选还有 P94459 / O68930; QA via uniprot-fetcher 验证"
    - "PDB 1ODS 我推测; CE7 hexamer 结构论文 deposition"
    - "本工作是 CE7 关键结构论文, 揭示 hexameric 装配 + active site 与 acetyl xylan / cephalosporin C 双底物的几何"
    - "Brannigan / Davies 实验室合作 (York structural biology)"
tags: [CE7, substrate_specificity, acetyl_xylan_esterase, cephalosporin_deacetylase, structural_basis, hexamer, Davies-lab, Brannigan-lab]
---

## 1. 背景与目标
- parent: B. subtilis CE7 family acetyl xylan esterase (AXE), 兼有 cephalosporin C deacetylase 活性
- 当时背景: CE7 已知 substrate 谱广 (acetyl xylan + cephalosporin), 但分子基础不明
- 目标: 解析 hexameric 高分辨结构, 解释 dual-substrate specificity 来源
- 应用: 木聚糖深度水解 (与 GH10/11 协同) + 抗生素中间体加工 (cephalosporin 7-aminocephalosporanic acid 生成)

## 2. 决策过程

### 候选位点策略
- **结构生物学** 路线: 解 hexameric assembly + active site characterization
- 后续 mutagenesis 验证 catalytic triad (Ser-His-Asp) 与 substrate-binding pocket residues

### 排除的位点 (★ 必填)
- α/β hydrolase fold catalytic Ser-His-Asp/Glu 严格保留 — 突变即失活 (Ser → Ala 是常见 catalytically dead control)
- Oxyanion hole 主链 NH (Ser 周围两个残基) 不能动
- Hexamer interface 残基 — 破坏会导致 monomer 失活 (CE7 hexameric assembly 是 active form)

### 计算工具与阈值
- 主要工具: X-ray crystallography (1.9 Å resolution) + 序列比对
- 实验校验: 重组表达 in E. coli → 多底物 activity assay (acetyl-xylan, p-nitrophenyl acetate 一般底物, cephalosporin C 抗生素底物)

## 3. 实验结果

### 关键发现
| 发现 | 内容 |
| --- | --- |
| Hexameric 装配 | 2 三聚体堆叠, 每个 monomer ~37 kDa |
| Catalytic triad | Ser-His-Asp (典型 α/β hydrolase) |
| Active site | Open access, 适合多种 substrate; 没有 narrow tunnel 强制 specificity |
| Acetyl-binding pocket | hydrophobic, 适合 acetyl 与 small acyl group |
| Substrate diversity | 同一 active site 接受 acetyl-xylan + cephalosporin C 不同底物 |

### 失败案例 (★ 必填)
- 论文未报道失败的 mutation 设计 (是结构论文)
- 但提到:
  - Hexamer 装配在 E. coli 表达时不完美 (部分 monomer / dimer); 真实 oligomeric state 由 solution 与 crystal 共同 supports

## 4. 学习收获
- **成立的规则候选**:
  - CE7 工程化禁区: catalytic Ser-His-Asp triad + oxyanion hole + hexamer interface (3 个 zone, 全保留)
  - **Open active site 设计** 解释了 CE7 broad substrate scope: 工程化可以利用这一开放性进一步扩 substrate
  - α/β hydrolase fold 的 lipase/esterase 工程经验 (Bornscheuer 等) 适用于 CE7 — 跨 fold 的工程化知识转移
- **被推翻的假设**:
  - "Multi-substrate enzyme 必有不同的 substrate-binding mode" — CE7 显示同一 active site 接受多种 substrate 是可能的
- **下次类似问题应优先尝试**:
  - CE 工程化前必须先看 fold (是 α/β hydrolase 还是 SGNH 还是金属蛋白) — fold 决定可借鉴策略
  - 与 GH10/11 协同 assay 必须同步做 — CE 单酶活性提升不等于联合提升
- **应避免**:
  - 假设 CE7 与 lipase 完全相同 — 虽然 fold 类似, 但 active site openness 与 substrate diversity 远超典型 lipase

## 5. 计算 / 实验原始数据
晶体 deposition (PDB) + multi-substrate kinetics 数据见 J Mol Biol 330(3) supplementary.
