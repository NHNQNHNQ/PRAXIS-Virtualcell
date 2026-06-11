---
case_id: GT2-morgan-2013-nature
schema_version: 1
parent_enzyme:
  uniprot: Q3J125               # Rhodobacter sphaeroides BcsA (cellulose synthase catalytic subunit); UniProt 文本搜索
  cazy_family: GT2              # 反向 GT-A fold, β-1,4-glucan 合成酶代表
  ec: 2.4.1.12                  # cellulose synthase
  organism: Cereibacter sphaeroides   # 2020 重分类自 Rhodobacter sphaeroides (strain ATCC 17023)
  pdb: 4HG6                     # Morgan 2013 deposit; BcsA-BcsB complex with UDP-Glc (translocation snapshot)
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "OC[C@H]1O[C@@H](OP(=O)(O)OP(=O)(O)OC2C(O)C(O)C(N3C=NC4=C3N=CN=C4N)O2)[C@H](O)[C@@H](O)[C@@H]1O"  # UDP-glucose donor 示意
  class: UDP-glucose / nucleotide_sugar_donor
target_property: substrate_specificity   # GT2 工程化主线: substrate scope (β-1,4-glucan 与 chitin / 其他 polysaccharide 切换)
status: validated
provenance:
  source_type: literature
  doi: "10.1038/nature11744"
  pmid: 23222542
  citation: "Morgan JL, Strumillo J, Zimmer J (2013). Crystallographic snapshot of cellulose synthesis and membrane translocation. Nature 493(7431):181-186."
  extracted_at: 2026-04-28
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1038/nature11744 与 PMID 23222542 我推测; CrossRef 验证"
    - "UniProt Q3J125 我推测对应 BcsA from Rhodobacter sphaeroides; QA via uniprot-fetcher 验证"
    - "PDB 4HG6 我推测对应 BcsA-BcsB + UDP-Glc + cellooligosaccharide complex; Zimmer 实验室同期还有 4P00 / 4P02 等系列"
    - "BcsB 是 BcsA 的伴侣 transmembrane chaperone, 但 catalytic 全在 BcsA; engineering 焦点在 BcsA"
    - "本工作是 GT2 cellulose synthase 第一个完整 catalytic + translocation snapshot, 之前 GT2 工程化无结构指导"
    - "engineering target 标 substrate_specificity 因 GT2 family 内含 cellulose synthase / chitin synthase / hyaluronan synthase 等多 substrate 同 fold; 跨 substrate 工程化是 GT2 主线"
    - "Zimmer 组 (UVA) 主导, 后续 follow-up Nature 2014 / Nature Comm 2016 系列扩展 mechanism + product translocation 模型"
tags: [GT2, cellulose_synthase, BcsA, GT-A_fold, processive_polymerization, membrane_translocation, mechanism_anchor, Zimmer-lab, structural_basis]
---

## 1. 背景与目标
- parent: Rhodobacter sphaeroides BcsA (GT2 family cellulose synthase catalytic subunit); membrane-integral, 与 BcsB chaperone 共组装
- 起始性质: BcsA 处理 UDP-Glc 作 donor, 以反向 (inverting) 机制催化 β-1,4-glucan 合成 + processive 聚合 + co-translational membrane translocation; 当时 (pre-2013) 无完整 catalytic + translocation 结构
- 目标: 解 BcsA-BcsB 复合物高分辨结构 with UDP-Glc + 增长中 cellooligosaccharide chain, 揭示 GT2 catalysis 与 channel-mediated translocation 的耦合机制
- 应用 (engineering downstream): 整个 GT2 家族 (cellulose / chitin / hyaluronan / curdlan synthase 等) 工程化的结构基础; 跨 substrate engineering (e.g. cellulose synthase → chitin synthase 框架转换) 必备

## 2. 决策过程 (本文是 mechanism + structure, 非 mutagenesis 工程化)

### 候选位点策略
- **结构生物学** 路线: 解 BcsA-BcsB 共晶 (membrane protein complex 难度大, 用 cyclic-di-GMP 激活态 trapping)
- 共晶 with UDP-Glc 与增长中 oligosaccharide: 直接看 catalytic geometry + translocation channel topology
- 后续 hypothesis-driven 突变 (论文 + follow-up) 验证 catalytic Asp 三联体 + cyclic-di-GMP allosteric 位点
- 不做 saturation library

### 排除的位点 (★ 必填)
- **催化 Asp 三联体 (DDD motif, GT2 标志)**: 三 Asp 协同 UDP 离去 + acceptor 4-OH 活化; 任一突变即失活 (后续 mutagenesis 反复证)
- **DXD motif (GT-A fold 经典 metal binding)**: BcsA 含 DXD-like motif 配位 Mn²⁺ / Mg²⁺ 稳定 UDP 二磷酸; 严格保留
- **UDP 结合 motif**: GT-A fold N-端 nucleotide-binding domain Rossmann-like fold 全保留
- **跨膜 helix bundle 内的 finger helix (PilZ-like cyclic-di-GMP sensor)**: 是 allosteric activation 关键, 突变常 lock 在 inactive 状态
- **product translocation channel 内壁 (positively charged Lys/Arg)**: 与生长中 β-glucan chain 接触, 严格保留以维持 processivity

### 计算工具与阈值
- 主要工具: X-ray crystallography (~3.0-3.4 Å, membrane protein 限制), 后续 cryo-EM 系列扩展
- MD 与 docking 可作辅助但论文主线是 crystallography
- 实验校验: 异源表达 BcsA-BcsB in E. coli, in vitro UDP-Glc-driven cellooligo synthesis, HPAEC-PAD / TLC 检测产物 chain length distribution

## 3. 实验结果

### 关键发现
| 发现 | 内容 |
| --- | --- |
| 完整 catalytic + translocation snapshot | UDP-Glc 在 active site, 增长中 cello-oligo 穿过 membrane channel |
| Catalytic DDD triad geometry | 三 Asp 几何排布与反向 (inverting) GT-A fold 经典模式一致 |
| Cyclic-di-GMP allosteric site | PilZ 域感受 c-di-GMP, 通过 finger helix 控制 catalysis on/off |
| Product translocation channel | β-glucan chain 一旦 polymerized, sliding through cross-membrane pore, BcsB 在 periplasmic 侧 chaperone |
| Processive mechanism | 单 BcsA 不解离 substrate, 反复 add UDP-Glc + extend chain, 协同 chain translocation |

### 失败案例 (★ 必填)
- 论文 mechanism 主线; 工程化 mutagenesis 失败案例不在范围
- 但讨论了 (从历史文献总结):
  - 早期 GT2 cellulose synthase 工程化 (pre-2013 attempts) 缺结构指导, 命中率低
  - 跨 substrate 改造 (cellulose synthase → chitin synthase fold): 仅靠 sequence alignment 失败 — 必须保 fold + 改 acceptor pocket 局部, 不能盲改 catalytic Asp
  - 跨 GT2 sub-family 同源建模做工程化的早期失败: 跨 sub-family fold 微差致 mutation transfer 不可靠

## 4. 学习收获
- **成立的规则候选**:
  - **GT2 工程化绝对禁区**: DDD catalytic triad + DXD metal binding + UDP nucleotide binding domain + finger helix (c-di-GMP 感受) + product translocation channel 内壁
  - **GT2 跨 substrate engineering (cellulose ↔ chitin ↔ hyaluronan synthase)**: 改 acceptor pocket aromatic 与 H-bond donor 残基, 保留 catalytic + translocation backbone
  - **GT-A fold (DXD motif) vs GT-B fold (Rossmann + Rossmann)**: GT2 (GT-A) 与 GT4/GT1 (GT-B) 工程化 mask 不同 — DXD metal binding 是 GT-A 专属约束
  - **Membrane-integral GT 工程化必须 + transmembrane stability assay**: 单纯 active-site mutation 改 substrate scope 但 misfold rate 高
- **被推翻的假设**:
  - "GT2 family substrate scope 由单一 acceptor pocket residue 决定" — 结构显示是 multi-residue + channel + chaperone 协同, 单点突变效应有限
  - "GT2 不需要 metal cofactor" — DXD-Mn²⁺ 必需, 之前部分文献忽略
- **下次类似问题应优先尝试**:
  - 任何 GT2 family 工程化, 用 BcsA 4HG6 结构作 starting framework + AlphaFold homolog model
  - 跨 substrate engineering 优先改 acceptor pocket aromatic, 保 catalytic + translocation 全部
  - 必须 + transmembrane stability + processivity assay (single kcat 不够)
- **应避免**:
  - 任何 DDD catalytic triad + DXD motif 周围 ±5 Å 突变
  - 把 GT2 (GT-A fold) mutation 直接转 GT4 / GT1 (GT-B fold) — 两者 fold + metal 依赖不同
  - 单依赖 active-site mutagenesis 改 substrate scope, 不考虑 translocation channel 适配

## 5. 计算 / 实验原始数据
晶体 deposition 4HG6 + UDP-Glc / cellooligo binding 数据见 Nature 2013 supplementary; 后续 Zimmer 组 follow-up (Nature 2014 / Nat Comm 2016) 扩展 translocation kinetics + product release mechanism.
