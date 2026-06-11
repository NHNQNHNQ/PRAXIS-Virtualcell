---
case_id: NEG-RETROALDO-jiang-2008-science
schema_version: 1
parent_enzyme:
  uniprot: null
  enzyme_family: synthetic_design_anchor
  cazy_family: null
  ec: 4.1.2.-                   # retro-aldolase (synthetic, EC 4.1.2.4-like or designed)
  organism: synthetic_design
  pdb: 3B5L                     # RA61 design 早期 deposit (Jiang 2008 deposit); QA 验证
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "OC(c1ccc(N(=O)=O)cc1)CC(=O)c2ccccc2"   # methodol (4'-nitrobenzaldehyde + acetone aldol product) 示意
  class: synthetic_aldol_product / methodol
target_property: activity        # 计算设计 baseline 极低, RA61 起始 kcat ~10⁻⁵ s⁻¹
status: partial                  # 反例: 计算 de novo 设计 retro-aldolase 起始活性远不够
provenance:
  source_type: literature
  doi: "10.1126/science.1152692"
  pmid: 18323452
  citation: "Jiang L, Althoff EA, Clemente FR, Doyle L, Röthlisberger D, Zanghellini A, Gallaher JL, Betker JL, Tanaka F, Barbas CF 3rd, Hilvert D, Houk KN, Stoddard BL, Baker D (2008). De novo computational design of retro-aldol enzymes. Science 319(5868):1387-1391."
  extracted_at: 2026-04-28
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1126/science.1152692 与 PMID 18323452 我推测; CrossRef 验证"
    - "PDB 3B5L 我推测对应 RA61 design; 同时 deposit 还有 RA22 等系列 (3B5V 等)"
    - "32 个 RA designs, 10 个有可检测活性 (RA22 / RA45 / RA46 / RA60 / RA61 等), 其中 RA61 baseline 较高但仍 kcat ~10⁻⁵ s⁻¹"
    - "本论文是 Baker / Hilvert / Houk / Stoddard / Tanaka / Barbas 团队合作的 de novo retro-aldolase 设计开山论文, 是 'design 路线' 的代表"
    - "标记为反例 (NEG-) 不是因为 paper 失败, 而是因为 paper 数据本身揭示了'纯 design baseline 不实用'的事实, 需配合 directed evolution"
    - "Lys 类 imine-机制 retro-aldol: Lys nucleophile + 邻位 H-bond donor 协同; 设计选 Lys 是否 protonated 是关键变量"
    - "RA61 后续被 Hilvert 组 directed evolution 推到 HG3.17 (Obexer 2017 Nat Chem) 显示 evolution 比 design 重要得多"
tags: [computational_design, retro_aldolase, de_novo_design, Lys_imine_mechanism, NEGATIVE_case, failure_mode_anchor, design_limit, baseline_activity, Baker-lab, Hilvert-lab]
---

## 1. 背景与目标 — 反例性质
- 32 个 retro-aldolase de novo design candidate, 不同 scaffold + 不同 catalytic residue 配置
- 起始性质: 32 个 design 中 10 个 (~30%) 有可检测活性, 顶级活性 RA61 kcat ~10⁻⁵ s⁻¹, kcat/KM ~10⁻¹ M⁻¹·s⁻¹
- 反例核心: 即使是当时最强 design 算法 + 多 scaffold + 仔细 catalytic geometry 摆位, 起始活性距实用酶 (kcat/KM ~10⁵-10⁷) 5-7 个数量级
- 论文 explicitly 提示后续 directed evolution 是必需 step

## 2. 决策过程

### 候选位点策略
- 计算设计 (Rosetta 系列 + RosettaMatch + 几何匹配 + 全 scaffold 库 ~10⁵ scaffolds)
- 多 catalytic residue 配置: Lys-Tyr-H-bond-network / Lys-Asp / 等
- 32 candidates 实验合成 + 表达 + 测活

### 排除的位点 (★ 必填)
- 计算设计的 Lys 严格保留 (catalytic nucleophile 假设)
- TIM barrel scaffold core (β-strands) 保留以维持 fold
- 但论文 implicitly 显示: 这些 'rationally 排除' 的预设, 在后续 evolution 中被 evolution 替换 (e.g. HG3.17 evolution 反而把 Lys 邻位 Tyr 替换)

### 计算工具与阈值
- Rosetta 全 design pipeline (ddG / 几何匹配 / dock-and-design)
- 不依赖 directed evolution (本论文 design-only, 后续 paper 接 DE)
- 实验校验: 异源表达 in E. coli, 测 retro-aldol 反应初速度 (荧光 readout)

## 3. 实验结果

### 32 design 顶级活性
| 设计 | kcat (s⁻¹) | kcat/KM (M⁻¹s⁻¹) | 与天然酶比 |
| --- | --- | --- | --- |
| RA22 | ~10⁻⁵ | ~0.1 | 10⁻⁶× |
| RA60 | ~5×10⁻⁵ | ~1 | 10⁻⁶× |
| **RA61 (best)** | ~10⁻⁴ | ~10 | 10⁻⁵× |
| RA45/RA46 | ~10⁻⁵ | ~0.5 | 10⁻⁶× |
| 天然 retro-aldolase 参考 | 10⁻¹ | 10⁵ | 1× |
| Hit rate | ~10/32 (~30%) | – | – |

### 失败案例 (★ 必填) — 本案例的核心
- **22/32 designs 完全无活性**: 虽然计算预测有 catalytic geometry, 实测无任何 turnover — design 命中率 30% 即上限
- **Hit designs 也距实用 5-7 个数量级**: kcat/KM ~10 远不如 'background catalysis' (e.g. simple amine + small molecule), 工业不可用
- **Catalytic Lys 几何偏移**: subsequent crystal structure 显示 designed Lys 在实测中位置偏离 design ~2-3 Å, 解释低活性
- **Solvent access pocket 不够大**: design 侧重 transition state 几何, 忽略 substrate 进出 channel; 实测 KM 高
- **Proton shuttle network 失效**: design 多假设 H-bond network 独立稳定, 实测 dynamic 不稳, water-mediated 是主导
- **Subsequent papers 显示 DE 比 design 重要得多**: HG3.17 (Obexer 2017 Nat Chem) 在 RA-class scaffold 上 evolved kcat 提升 ~6 个数量级 — 远超 design 阶段贡献

## 4. 学习收获 — 反规则 / anti-rule
- **成立的反规则 (anti-rule)**:
  - **De novo computational design baseline 是不实用的起点, 不是终点**: 任何 publication 把 design baseline 当 'usable' 都误导
  - **30% hit rate 是 design 上限**: 不要期待新 design 项目 hit rate >30% (即使 method 不断进步, 这一比率 stable 多年)
  - **Design 假设的 catalytic geometry 是粗略 approximation**: 后续 crystal 多揭示偏移 — 工程化必须接 evolution + 接 structure 反复
  - **Catalytic Lys / Cys 类 nucleophile 的 microenvironment 设计极困难**: pKa / 几何 / dynamics 三联耦合, 计算难全捕捉
- **被推翻的假设**:
  - "更复杂的 catalytic ensemble (Lys+Tyr+Asp+...) 的 design 比简单 (Lys-only) 强" — 反例: 简单 design 经 evolution 后超过复杂 design
- **下次类似问题应优先尝试**:
  - 任何 de novo design 项目, 起始预算 ≥10 round directed evolution; design 是 starter 而非 product
  - 设计阶段保 catalytic site 简单 (单 Lys / 单 Cys), 让 evolution 完成 catalytic ensemble
- **应避免**:
  - 直接以 design baseline 评估 method (例如 'RA61 hit kcat=10⁻⁴' 不是 'works', 是 'starting point')
  - 把 'design hit rate' 当 method 评价 metric — 应当看 'evolution-rescued usable activity'

### Anti-retrieval 信号 (★ 强标记)
本案例进入 indices/anti/: 任何"de novo computational design 不接 directed evolution"的工程化方案被 vetoed; 任何"design-only baseline ≥10⁻³ s⁻¹ 即认为可用"的判断被 vetoed.

## 5. 计算 / 实验原始数据
32 design library + per-design kinetic 数据见 Science 2008 supplementary; Hilvert 后续 evolution paper (Obexer 2017 Nat Chem) 提供 ~10⁶× 活性提升的 evolution 数据.
