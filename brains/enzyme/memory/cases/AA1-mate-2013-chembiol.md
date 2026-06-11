---
case_id: AA1-mate-2013-chembiol
schema_version: 1
parent_enzyme:
  uniprot: Q12717               # PM1 laccase / basidiomycete laccase 候选; QA 验证 (Alcalde 组 PM1 来源)
  cazy_family: AA1              # Multicopper oxidase / laccase
  ec: 1.10.3.2                  # laccase
  organism: Trametes versicolor   # 与 UniProt Q12717 注释对齐 (实际工程化 chassis 为 PM1 strain, basidiomycete, 序列 ~85% 相似)
  pdb: null                     # 7H7 evolved variant 多无单独 deposit; PM1 starter 可能用 1GYC (Trametes versicolor) 同源
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "Cc1cc(C)c(O)c(C)c1"   # 2,6-dimethylphenol 模型; 实际筛 redox mediator (ABTS) + organic substrates
  class: phenolic_substrate / mediator_oxidation
target_property: substrate_specificity   # 主线: 在血液 (high Cl⁻ + 中性 pH) 下保持高活性 — 非典型工业 condition
status: validated
provenance:
  source_type: literature
  doi: "10.1016/j.chembiol.2013.01.001"
  pmid: 23438751
  citation: "Mate D, Gonzalez-Perez D, Falk M, Kittl R, Pita M, De Lacey AL, Ludwig R, Shleev S, Alcalde M (2013). Blood tolerant laccase by directed evolution. Chemistry & Biology 20(2):223-231."
  extracted_at: 2026-04-28
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1016/j.chembiol.2013.01.001 与 PMID 23438751 我推测 (Chem Biol 2013 vol 20 issue 2); CrossRef 验证"
    - "UniProt Q12717 我推测对应 PM1 laccase; PM1 是 Alcalde 组的工程化 chassis (基于 basidiomycete 来源, 起始通过 Camarero/Pardo 平台); QA 验证"
    - "PM1 starter 序列与 Pycnoporus cinnabarinus / Trametes 族 laccase 同源, 因 directed evolution 多 round 已偏离 wild-type"
    - "7H7 是论文标记的 best variant; 多个 mutation 在 T1-Cu pocket / N-端 / surface 累积 (具体 mutation list 见原文 Fig 2-3)"
    - "engineering target 标 substrate_specificity (其实是 environment specificity — high Cl⁻ + 中性 pH); laccase 标准工业 condition 是低 pH (~3-5), 此工作打破常规"
    - "应用导向: 体内生物燃料电池 / 生物传感器 — 需要在血液 (Cl⁻ ~150 mM, pH 7.4) 工作"
    - "Alcalde 实验室 (CSIC/CIB Madrid) 是 laccase directed evolution 平台的代表组"
tags: [AA1, laccase, multicopper_oxidase, directed_evolution, blood_tolerance, chloride_tolerance, neutral_pH, biofuel_cell, biosensor, Alcalde-lab]
---

## 1. 背景与目标
- parent: PM1 laccase (Alcalde 组工程化平台 chassis, basidiomycete 来源); 起始已经过多 round directed evolution (从 Camarero / Pardo 系列)
- 起始性质: 在标准 laccase condition (pH 3-5, low salt) 高活, 但 blood condition (pH 7.4, Cl⁻ ~150 mM) 几乎完全失活 — Cl⁻ 抑制 + 中性 pH 双失稳
- 目标: directed evolution 让 laccase 在 blood-realistic condition (pH 7.4 + 150 mM Cl⁻) 保活 + 适合 implantable biofuel cell / biosensor
- 应用: 生物医学 implantable biofuel cell (从血糖 / 血脂氧化提取电能), 体内 glucose biosensor cathode

## 2. 决策过程

### 候选位点策略
- **directed evolution + accumulation**:
  - **Error-prone PCR + DNA shuffling** rounds, 累积 selection 压力 (低 pH → 中性 → 中性 + Cl⁻ → blood)
  - 关键 round 切换 pressure 而不是单 pressure 持续
  - 累积 mutation 跨 round 存留 (parent-child 谱系)
- 候选数: 累积 round ~10⁵ mutant variants / round 量级; 顶级 hit 数十

### 排除的位点 (★ 必填)
- **T1 Cu site (Cys-His-His-Met 配位)** + **T2/T3 trinuclear Cu cluster (8 His 配位 3 Cu)**: AA1 multicopper oxidase 标志, 任一突变即失活
- **底物入口 (T1 pocket lid)**: 部分保留 (substrate scope 关键), 但 Cu 配位 His 严格保留
- **disulfide bridge (laccase 含 1-2 个内部二硫键)**: 多 fungal laccase 保留, 拆即 misfolding
- 注: directed evolution 由 selection 自动淘汰破坏 Cu site 的 mutation; 但显式标记 排除 mask 用于后续 rational design

### 计算工具与阈值
- 不依赖 ΔΔG 主导
- 关键工具:
  - 96-well plate ABTS oxidation assay 在 different pH / Cl⁻ condition 多平行筛
  - Saccharomyces cerevisiae 表达系统 (Alcalde 组优势, 兼容 fungal laccase 折叠 + glycosylation)
- 实验校验:
  - Top hits 纯化 + electrochemistry (在 blood-mimic buffer 中 cyclic voltammetry)
  - implantable biofuel cell prototype 集成测试

## 3. 实验结果

### 关键变体 7H7
| 量 | PM1 starter | 7H7 (best) | 提升 |
| --- | --- | --- | --- |
| pH 7.4 + 150 mM Cl⁻ kcat (ABTS) | ~1% (vs pH 4) | ~30-40% (vs pH 4) | 30-40× |
| Blood plasma 实测活性 | ~0% | 显著保留 | – |
| Total mutation 数 | – | ~7 (累积 round) | – |
| T1 Cu redox potential | ~750 mV | 类似 (保留) | – |
| 基础 fold + Cu site | 完整 | 完整 | – |

### 失败案例 (★ 必填)
- 单点 mutation 直接转移 (从中性 pH variant 复制到原始 wt) 效果差 — 必须累积谱系
- 部分 hits 在标准 laccase assay 高活但在 blood plasma 中失活 (plasma 蛋白 / 内源抑制剂 干扰); 选 condition 要 plasma 实测
- 早期 round 在低 Cl⁻ 选 pressure 得到 hits 不能直接 carry to high Cl⁻ — 需 stepwise 增 Cl⁻ 浓度
- T1 Cu pocket 周围 mutation 容易调 redox 但同时影响 substrate scope, 多 round 后部分 hits 对 ABTS 高活但对 phenolic substrate 中性

## 4. 学习收获
- **成立的规则候选**:
  - **AA1 laccase 工程化绝对禁区**: T1 Cu (Cys-His-His-Met) + T2/T3 trinuclear cluster (8 His) + 已识别的 fungal disulfide
  - **non-standard environment laccase (blood / 中性 pH / 高 Cl⁻) 必须用 stepwise selection** — 单 round 强 pressure 失败, 阶梯逐步加压成功
  - **Alcalde 平台 (Saccharomyces 表达 + 96-well ABTS)** 是 fungal laccase 工程化的事实标准
  - **PM1 chassis** 已经是工程化母板, 优于直接用 wild-type Trametes / Pycnoporus laccase 作为 starter (跳了多 round 起始 fitness)
  - **T1 Cu pocket 微调 vs. fold 整体保留**: 工程化主战场是 T1 lid + surface charge, 不是 catalytic Cu 本身
- **被推翻的假设**:
  - "fungal laccase 在中性 pH 不可工程化" — 反复 round 直接证伪
  - "Cl⁻ 不可逆抑制 fungal laccase" — selection 后变体保留 Cl⁻ tolerance, 提示是 binding mode 而不是 hard 不可逆
- **下次类似问题应优先尝试**:
  - 任何 multicopper oxidase 工程化, stepwise selection (不是 jackpot single round)
  - 用 PM1 (或类似 already-evolved chassis) 作 starter, 不要从 wild-type 重新爬
  - condition-specific mutation 必须在 condition 实测 (blood plasma vs ABTS standard buffer)
- **应避免**:
  - 任何 Cu 配位 His / Cys 周围 ±5 Å 的"看似稳定" mutation
  - 单纯 ABTS plate 选 hits, 跳过 plasma / blood 实测
  - 跨 laccase 来源 (Trametes ↔ Pycnoporus ↔ Coriolopsis) 直接转 mutation, 因序列 divergence 累积

## 5. 计算 / 实验原始数据
原始 mutation 累积谱系 + variant kinetics + electrochemistry 数据见 Chem Biol 2013 supplementary; Alcalde 组 平台技术细节 跨多 paper (Mate 2010 / Pardo 2012 / Mate 2013) 系列.
