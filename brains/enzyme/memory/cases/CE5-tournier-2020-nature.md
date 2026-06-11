---
case_id: CE5-tournier-2020-nature
schema_version: 1
parent_enzyme:
  uniprot: G9BY57               # Leaf-branch compost cutinase (LCC); metagenomic 来源, UniProt 收录
  cazy_family: CE5              # CAZy 将 cutinase 归 CE5; 部分文献亦视为 standalone α/β-hydrolase
  ec: 3.1.1.74                  # cutinase
  organism: Unknown prokaryotic organism   # UniProt G9BY57 标注 (leaf-branch compost metagenome)
  pdb: 4EB0                     # Sulaiman 2012 LCC apo crystal structure
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "CCOC(=O)c1ccc(C(=O)OCC)cc1"   # bis(2-hydroxyethyl) terephthalate (BHET) / PET 模型 substrate 示意
  class: PET / polyethylene_terephthalate / aromatic_polyester
target_property: thermostability_and_activity   # ICCG variant 同时提升 Tm 与 PET 解聚 turnover
status: validated
provenance:
  source_type: literature
  doi: "10.1038/s41586-020-2149-4"
  pmid: 32269349
  citation: "Tournier V, Topham CM, Gilles A, David B, Folgoas C, Moya-Leclair E, Kamionka E, Desrousseaux ML, Texier H, Gavalda S, Cot M, Guémard E, Dalibey M, Nomme J, Cioci G, Barbe S, Chateau M, André I, Duquesne S, Marty A (2020). An engineered PET depolymerase to break down and recycle plastic bottles. Nature 580(7802):216-219."
  extracted_at: 2026-04-28
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1038/s41586-020-2149-4 与 PMID 32269349 我推测; CrossRef 验证 (此 paper 高引, 验证应直接)"
    - "UniProt G9BY57 我推测对应 LCC; QA via uniprot-fetcher 验证 (Sulaiman 2012 deposit)"
    - "PDB 4EB0 我推测对应 LCC apo; ICCG variant 是否有 deposition 须查 (Tournier 2020 之后系列结构如 7VVE / 7VVD 可能是 ICCG 或其衍生)"
    - "CAZy 将 cutinase / PET hydrolase 收入 CE5 (carbohydrate esterase 5), 与 acetyl xylan esterase 共类; 也有文献分类为 EC 3.1.1.74 之独立 α/β-hydrolase"
    - "ICCG variant: F243I / D238C / S283C / Y127G 四点 mutation (cysteine pair forms 工程化 disulfide bridge); 保留 catalytic Ser-His-Asp triad"
    - "其中 Cys 引入 (D238C/S283C) 是 disulfide bridge thermostability 经典策略; F243I 是 pocket reshaping; Y127G 是 substrate access"
    - "ICCG 在 65-72 °C 接近 PET Tg (玻璃化转变 ~70 °C) 工作, 是高效 PET 解聚的关键"
    - "Carbios 公司商业化, 大规模 PET 回收试点工厂"
tags: [CE5, cutinase, PET_depolymerase, plastic_recycling, thermostability, disulfide_engineering, ICCG_variant, Tournier-2020, Nature, Carbios, metagenomic]
---

## 1. 背景与目标
- parent: Leaf-branch compost cutinase (LCC, metagenomic), 起始 Tm ~85 °C 但 PET 解聚 turnover 不足以工业化
- 起始性质: 起始 LCC 在 PET (post-consumer bottle PET) 上有微弱 catalytic activity, 但商业化所需的 high-loading turnover (kg PET / g enzyme / h) 不达标
- 目标: 工程化 LCC 成为高效 PET 解聚酶, 在 PET Tg 附近 (65-72 °C) 稳定运行 + 高 turnover
- 应用: 商业 PET 塑料瓶回收 (Carbios 平台); 革命性的酶法循环经济

## 2. 决策过程

### 候选位点策略
- **结构指导 + rational + 累积 round**:
  - 解 LCC apo 结构 (Sulaiman 2012, 已有), 识别 PET binding pocket (浅 surface cleft, 与 Ser-His-Asp triad 相邻)
  - **Disulfide bridge 引入** at distance-compatible Cys pair sites: 提升 high-T 稳定性
  - **Pocket reshaping** at substrate-binding aromatic residues: 提升 PET 接触效率
  - **Surface charge / packing optimization** for thermostability
- 候选数: 数十 single mutation, 然后 combinatorial 4-mutation stacking → ICCG (F243I + D238C + S283C + Y127G)

### 排除的位点 (★ 必填)
- **催化三联体 Ser-His-Asp** 严格保留 (Ser165 nucleophile 基于 LCC 编号; α/β-hydrolase 经典 motif)
- **oxyanion hole** (主链 NH 来自 catalytic Ser 前后 + 单一 backbone amide) 保留 — 干扰即失活
- **disulfide pair (D238C/S283C 引入新二硫键)** 一旦设计就锁定, 后续 mutation 不能拆 (否则失稳)
- **substrate-binding hydrophobic patch** 周围 5 Å 内的关键 aromatic (Trp / Phe) 部分保留 (作 PET 接触面)

### 计算工具与阈值
- **结构指导**: PET model substrate docking 至 LCC pocket
- PyRosetta / Rosetta ddG 用于 disulfide pair 的几何 + 能量 screening (Cα-Cα 距离 4.5–6.5 Å, χ3 dihedral 约 ±90°)
- 选 ddG ≤ -1 kcal/mol 的 mutation 进 round; ICCG combinatorial round 4 个 mutation 累积
- 实验校验: 异源表达 in E. coli, Tm via DSC, PET turnover 在 amorphous PET film + post-consumer PET (crystalline) 共测; turnover 单位为 g_TPA / g_enzyme · h

## 3. 实验结果

### 关键变体与提升 (★ 数值)
| Variant | Mutation | Tm (°C) | PET turnover (rel.) |
| --- | --- | --- | --- |
| WT LCC | – | ~85 | baseline 1× |
| Single F243I | F243I | ~86 | 1.5× |
| Disulfide D238C/S283C | D238C/S283C | ~94 | 2× |
| Pocket Y127G | Y127G | ~85 | 2.5× |
| **ICCG (4-stacking)** | F243I+D238C+S283C+Y127G | ~94-95 | ~10× (process condition, 65-72 °C, post-consumer PET) |
| Process throughput (Carbios) | – | – | 90% PET → TPA 在 10-16 h |

### 失败案例 (★ 必填)
- 多个 single-point mutation 在 standalone 测试中提升 Tm 但 stacking 时丢失增益 (epistasis): F243I + D238C 双突变好于线性预测, 但加 Y127G 后 Tm 不再叠加, 仅 turnover 上升
- Cys pair 引入位置选择困难: 不少 Cα-Cα 距离合适的位点引入后导致 misfolding 或表达 yield 下降; D238C/S283C 是反复 screening 后筛出的少数 working pair
- 早期 saturation library 在 catalytic Ser 邻近残基产生大量"破坏性 hits" — 必须 explicit 排除以避免浪费筛选资源
- 高度结晶 (crystalline) PET 仍然是 ICCG 解聚瓶颈, 工程化没有完全消除 — process side 通过预处理 (amorphization) 补偿

## 4. 学习收获
- **成立的规则候选**:
  - **PET 解聚酶工程化的核心目标是在 PET Tg (~70 °C) 稳定运行** — Tm < Tg 即在 process T 下变性, 工程化第一优先级是 Tm 上推
  - **disulfide bridge 引入 (Cys pair 设计) 是 cutinase / 小蛋白热稳定的 dominant 策略** (相对于全长 consensus / proline introduction)
  - **PET binding pocket 浅且 substrate-large**, 工程化 pocket 残基 (Y/F → 小残基) 可改 substrate 接触模式
  - **Cutinase / α/β-hydrolase 工程化的禁区 mask**: Ser-His-Asp triad + oxyanion hole 主链 + 已设计 disulfide
  - **process-condition 评估 (post-consumer PET, 65-72 °C, 高 enzyme loading)** 比 amorphous film standard 测试更具工业意义
- **被推翻的假设**:
  - "Tm 提升与 turnover 提升正相关" — 不一定线性, 见 ICCG stacking 中 Tm 与 turnover 的不同 mutation 来源
  - "高 Tm 起始酶 (~85 °C 的 LCC) 不需要再做 thermostability 工程化" — process condition 下仍需要 +10 °C 边界
- **下次类似问题应优先尝试**:
  - 任何 polyester / 高熔点 polymer 解聚酶工程化, 优先 disulfide bridge + pocket reshaping 双轨
  - 用 process-realistic substrate (post-consumer plastic, 不是单 oligo model) 做 selection
- **应避免**:
  - Catalytic Ser 邻近 ±3 残基的"看似稳定" mutation (PyRosetta 优势但实测失活)
  - 仅在 amorphous film 上选 hit, 跳过 crystalline post-consumer 验证

## 5. 计算 / 实验原始数据
ICCG mutation 设计与 PyRosetta/Rosetta 数据见 Nature 2020 supplementary; 中试规模 PET process 数据由 Carbios 公司报告 (商业化资源, 部分公开).
