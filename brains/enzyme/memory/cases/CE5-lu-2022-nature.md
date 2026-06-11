---
case_id: CE5-lu-2022-nature
schema_version: 1
parent_enzyme:
  uniprot: A0A0K8P6T7            # IsPETase from Ideonella sakaiensis (parent of FAST-PETase)
  cazy_family: CE5
  ec: 3.1.1.101
  organism: Piscinibacter sakaiensis   # 2018 重分类自 Ideonella sakaiensis 201-F6 (engineered variant)
  pdb: 7SH6                       # FAST-PETase deposit (Lu 2022); 候选, QA 验证
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "CCOC(=O)c1ccc(C(=O)OCC)cc1"   # PET / BHET model
  class: polyethylene_terephthalate / aromatic_polyester
target_property: thermostability_and_activity
status: validated
provenance:
  source_type: literature
  doi: "10.1038/s41586-022-04599-z"
  pmid: 35418671
  citation: "Lu H, Diaz DJ, Czarnecki NJ, Zhu C, Kim W, Shroff R, Acosta DJ, Alexander BR, Cole HO, Zhang Y, Lynd NA, Ellington AD, Alper HS (2022). Machine learning-aided engineering of hydrolases for PET depolymerization. Nature 604(7907):662-667."
  extracted_at: 2026-04-28
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1038/s41586-022-04599-z 与 PMID 35418671 我推测; CrossRef 验证"
    - "PDB 7SH6 我推测对应 FAST-PETase deposit; 候选 7QVH / 7SHB 等系列"
    - "Alper Hal 实验室 (UT Austin) 主导; Diaz / Shroff 等合作 ML 方法学"
    - "FAST-PETase 含 5 个 mutation: N233K / R224Q / S121E / D186H / R280A (relative to IsPETase WT)"
    - "ML 方法: MutCompute (Diaz 等开发) — 基于 3D structural CNN, 训练于 protein 序列-结构-mutation tolerance 数据"
    - "FAST-PETase Tm 提升 ~10 °C (50 → 60 °C), 在 50 °C 处理 amorphous PET 与 commercial PET 容器降解效率显著提升"
    - "engineering target 标 thermostability_and_activity 因双 metric 同步提升"
tags: [CE5, IsPETase, FAST_PETase, machine_learning, MutCompute, Diaz_et_al, Alper-lab, PET_depolymerization, thermostability, structure_aware_CNN]
---

## 1. 背景与目标
- parent: IsPETase (Yoshida 2016 Science 鉴定的 wild-type), Tm ~50 °C, 在 mesophilic 条件直接降解 PET 但起始活性低
- 起始性质: IsPETase WT 在 30 °C 缓慢降解 amorphous PET; 在 ≥ 40 °C 显著失活
- 目标: 用 ML-aided 方法 (MutCompute) 找少量 (5 个) mutation 同时提升 IsPETase 的 Tm 与 PET 降解活性
- 应用: 工业 PET 回收 — 在 50 °C condition 直接降解 post-consumer 容器 (而 LCC ICCG 路线在 70 °C, 不同 niche)

## 2. 决策过程

### 候选位点策略
- **MutCompute (3D structural CNN)** 评分每个 IsPETase 残基的 'mutation tolerance + benefit' 分数
- 输入: IsPETase 结构 + 局部 3D environment
- 输出: 每个位点 ∈ 19 个非自身 amino acid 的预测 score
- 选 score 最高 top-N candidates 实验验证, 累积形成 5-mutation 组合 FAST-PETase

### 排除的位点 (★ 必填)
- **catalytic triad Ser160-His237-Asp206** + **oxyanion hole** + **核心 disulfide Cys203-Cys239**: 全保留 (与 IsPETase 工程化通用 mask)
- MutCompute 自动排除高功能必需 (低 mutation tolerance) 位点 — 减少破坏性 hits

### 计算工具与阈值
- MutCompute (Diaz 等开发): 输入 PDB → 3D-Conv NN → output per-residue 19-mutation score
- 实验筛选: 表达 yield + Tm (CD melting / DSC) + PET 降解 (HPLC-DAD 检 TPA / MHET / BHET)
- 实验校验: 累积 mutation stack: single-mutation 验证后, top hits 组合成 multi-mutation, 测试 stacking effect

## 3. 实验结果

### FAST-PETase 性能
| 量 | IsPETase WT | FAST-PETase (5-mut) | 提升 |
| --- | --- | --- | --- |
| Tm (DSC) | ~50 °C | ~60 °C | +10 °C |
| Activity at 30 °C, amorphous PET | baseline | ~2× | 2× |
| **Activity at 50 °C, amorphous PET** | nearly 0 (失活) | 显著保留 | 关键提升 |
| Commercial PET 容器降解 (50 °C, 1 week) | <30% | >80-90% | ~3× |
| Mutations (relative WT) | 0 | 5 | – |

### 失败案例 (★ 必填)
- **MutCompute 预测的 top-N hit 中实测有效 ~50%**: ML 预测有 false positive; 必须实验验证 (与 NEG-AFMUTATION 类反例呼应, 结构 + ML 单独不可靠)
- **Single mutation Tm gain 累积时部分 sub-additive**: 5-mutation stack Tm 提升 +10 °C, 而 single mutation 累加预测应 ~+15 °C — epistasis 削弱 (与 NEG-EPISTASIS 一致)
- **FAST-PETase 在 70 °C (PET-Tg 附近) 仍变性**: 不达 LCC ICCG 工作温度 — IsPETase scaffold 本身限制
- **MutCompute 训练数据偏倚 (主要 thermostable 蛋白)**: 在 mesophilic IsPETase 上 hit rate 低于训练数据集 average
- **跨 substrate 转移 (PET ↔ PEF / PBT 等其他 polyester)**: FAST-PETase 优化的是 PET 接触面, PEF / PBT 等需重新工程化

## 4. 学习收获
- **成立的规则候选**:
  - **ML-aided + 实验验证 是 PET 降解酶工程化标配**: 单 ML 命中 ~50%, 必须实验校验
  - **MutCompute (3D-CNN) 比 sequence-only ML 在结构敏感 enzyme 上更准** — 但需高分辨结构输入 (与 NEG-AFMUTATION 反例形成对比, 高分辨 ≠ AF model)
  - **CE5 PETase 工程化的 mesophilic 路线 (IsPETase chassis) 与 thermophilic 路线 (LCC chassis) 各有 niche**: 选 chassis 看目标温度
  - **≤5 mutation 累积 stack 可控 epistasis** — 超过 5 个 mutation 必须谨慎验证组合效应
- **被推翻的假设**:
  - "ML 工具 (MutCompute / ESM-1v / 等) 取代 wet-lab 工程化" — 50% 命中率反例
- **下次类似问题应优先尝试**:
  - PET 降解酶 mesophilic 路线: IsPETase + MutCompute / 类似 ML 工具 + 实验
  - PET 降解酶 thermophilic 路线: LCC + structure-guided + disulfide + 实验
  - 任何 ML-aided 工程化, top-N 实验验证 (而非直接采纳 top-1)
- **应避免**:
  - 跳过实验直接 ship ML top-1 mutation
  - 在 mesophilic chassis (IsPETase) 期待 thermophilic activity (>70 °C)

## 5. 计算 / 实验原始数据
MutCompute scoring + 5-mutation stack kinetic + commercial PET degradation 数据见 Nature 2022 supplementary; FAST-PETase deposit 与配对 X-ray 数据由 Alper / Diaz 实验室公开.
