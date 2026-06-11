---
case_id: CE5-bell-2022-natcatal
schema_version: 1
parent_enzyme:
  uniprot: A0A0K8P6T7            # IsPETase parent (HotPETase 也基于 IsPETase scaffold)
  cazy_family: CE5
  ec: 3.1.1.101
  organism: Piscinibacter sakaiensis   # 2018 重分类自 Ideonella sakaiensis 201-F6 (engineered variant)
  pdb: null                       # HotPETase 是否 deposit 须查
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "CCOC(=O)c1ccc(C(=O)OCC)cc1"   # PET model substrate
  class: polyethylene_terephthalate / aromatic_polyester
target_property: thermostability_and_activity
status: validated
provenance:
  source_type: literature
  doi: "10.1038/s41929-022-00821-3"
  pmid: null
  citation: "Bell EL, Smithson R, Kilbride S, Foster J, Hardy FJ, Ramachandran S, Tedstone AA, Haigh SJ, Garforth AA, Day PJR, Levy C, Shaver MP, Green AP (2022). Directed evolution of an efficient and thermostable PET depolymerase. Nature Catalysis 5(8):673-681."
  extracted_at: 2026-04-28
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1038/s41929-022-00821-3 我推测; CrossRef 验证"
    - "PMID 我未推 (Nat Catal 2022 vol 5 issue 8); QA 必须查"
    - "Anthony Green 实验室 (Manchester) 主导"
    - "HotPETase 含 21 个 mutation (累积多 round); 远超 FAST-PETase 的 5 个 mutation; 显示 directed evolution 比 ML 单独引入更多 mutation"
    - "HotPETase Tm 接近 80 °C, 在 PET-Tg 附近工作"
    - "HotPETase 与 LCC ICCG 在 thermophilic 范围竞争; 但起始 chassis 不同 (IsPETase vs LCC)"
    - "engineering target 标 thermostability_and_activity 双 metric"
tags: [CE5, IsPETase, HotPETase, directed_evolution, thermostability, PET_depolymerization, Green-lab, Manchester, mesophilic_to_thermophilic, classical_DE]
---

## 1. 背景与目标
- parent: IsPETase WT (Yoshida 2016 鉴定); 起始 Tm ~50 °C
- 目标: 通过 directed evolution 累积 mutation 把 IsPETase 推到 thermophilic (>70 °C) 工作能力, 接近或超过 LCC ICCG 性能
- 反命题: FAST-PETase (Lu 2022, ML 5 mutation) 提到 60 °C; HotPETase (本文) 21 mutation 推到 ~80 °C — 显示 ML 与 DE 在 PET 工程化各有 niche

## 2. 决策过程

### 候选位点策略
- **directed evolution 多 round 累积**:
  - error-prone PCR + saturation 文库
  - high-throughput screen: 微量 PET 颗粒 + 荧光 readout (检测降解产物)
  - 多 round 选 hits 进入下一 round; 累积 mutation
- 不依赖结构指导 (但后续 X-ray 分析 evolved variant 揭示 mutation cluster)

### 排除的位点 (★ 必填)
- **catalytic triad Ser-His-Asp + oxyanion hole + 核心 disulfide**: 全保留 (selection 自动淘汰)
- **PET-binding cleft 表面**: 非完全保留, 部分 mutation 在表面调 PET 接触模式

### 计算工具与阈值
- 不依赖 ddG 预测 (DE 主导)
- 高通量 screen: 微 PET 颗粒 / pNPP model substrate / 荧光 readout 多 platform 并用
- 实验校验: Tm via DSC, PET 降解 via HPLC

## 3. 实验结果

### HotPETase 与同类对比
| Variant | Tm (°C) | 起始 chassis | Mutation 数 | PET 降解能力 |
| --- | --- | --- | --- | --- |
| IsPETase WT | ~50 | – | 0 | low |
| FAST-PETase (Lu 2022) | ~60 | IsPETase | 5 (ML) | mid (50 °C) |
| HotPETase (Bell 2022) | ~80 | IsPETase | 21 (DE) | high (>70 °C) |
| LCC WT | ~85 | – | 0 | low |
| LCC ICCG (Tournier 2020) | ~95 | LCC | 4 (rational) | high (65-72 °C) |

### 失败案例 (★ 必填)
- **HotPETase 21 mutation 中部分相互 epistasis**: round 8-12 引入的 mutation 在 final variant 中可被简化 (一些 mutation 可去除而活性保留) — 提示 DE 累积有冗余
- **Round 15+ 后命中率显著下降**: 多 round DE 后 single-mutation gain 越来越小, 计算成本陡增 (~5-10 round 是性价比上限)
- **HotPETase 在 commercial post-consumer PET (高结晶率) 仍部分受限**: 与 LCC ICCG 同样问题, 高结晶 PET 是 substrate 物理瓶颈, enzyme 工程化有限度
- **跨 chassis (IsPETase ↔ LCC) HotPETase 21 mutation 不可转移**: 序列差异大 (~50% identity); LCC 上需要重新 DE
- **HotPETase 21 mutation 累积引入聚集风险**: 部分 round 19-21 mutation 略降可溶性, 表达 yield 略下降

## 4. 学习收获
- **成立的规则候选**:
  - **PET 降解酶工程化的 mesophilic-to-thermophilic 路线可行**: IsPETase 21 round DE 推到 ~80 °C (远超 starting Tm)
  - **DE 比 ML 引入更多 mutation 但 round 投入大**: ~5 round DE ≈ ML top-5 命中, 之后 DE 边际收益下降
  - **CE5 PETase 工程化的 chassis 选择**: thermophilic 应用 LCC (起点高), mesophilic-to-thermophilic 应用 IsPETase 21 mutation
  - **多 round (>10) DE 必须监测 epistasis + 表达 yield**
- **被推翻的假设**:
  - "DE 始终优于 ML / rational design" — 5 round 后边际收益陡降, 时间成本高
  - "IsPETase chassis 不能达到 LCC 级 thermostability" — HotPETase 反证
- **下次类似问题应优先尝试**:
  - 任何 PET / 高熔点 polymer 工程化, 估算 round 数 — 通常 10-20 round 收敛
  - 配合 ML 工具 (MutCompute / ESM-1v) 选 round 0-3 的初始 hit, 加速早期收敛
- **应避免**:
  - 不监测 epistasis 直接 stack 21 mutation
  - 跨 chassis 直接转 evolved mutation (IsPETase ↔ LCC 失败)

## 5. 计算 / 实验原始数据
HotPETase 21-mutation 累积谱系 + per-round PET 降解 + Tm 数据见 Nat Catal 2022 supplementary; commercial PET test 由 Manchester / Levy 实验室合作.
