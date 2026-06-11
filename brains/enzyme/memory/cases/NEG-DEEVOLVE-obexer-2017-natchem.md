---
case_id: NEG-DEEVOLVE-obexer-2017-natchem
schema_version: 1
parent_enzyme:
  uniprot: null
  enzyme_family: synthetic_design_anchor
  cazy_family: null
  ec: 4.1.2.-                   # retro-aldolase (synthetic)
  organism: synthetic_design
  pdb: 5AN7                     # HG3.17 evolved variant deposit (Obexer 2017); QA 验证
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "OC(c1ccc(N(=O)=O)cc1)CC(=O)c2ccccc2"   # methodol (与 RA61 同 substrate)
  class: synthetic_aldol_product / methodol
target_property: activity        # 18 round DE 后 kcat 提升 ~6 个数量级 vs RA61 design baseline
status: validated
provenance:
  source_type: literature
  doi: "10.1038/nchem.2596"
  pmid: 27995924
  citation: "Obexer R, Godina A, Garrabou X, Mittl PRE, Baker D, Griffiths AD, Hilvert D (2017). Emergence of a catalytic tetrad during evolution of a highly active artificial aldolase. Nature Chemistry 9(1):50-56."
  extracted_at: 2026-04-28
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1038/nchem.2596 与 PMID 27995924 我推测; CrossRef 验证"
    - "PDB 5AN7 我推测对应 HG3.17 evolved variant; HG3 系列 (HG3, HG3.7, HG3.17) 是 RA61 → evolution 的衍生"
    - "本论文是 'design + evolution' 联合范式的代表 — 设计 RA61 → 18 round DE → HG3.17 (kcat/KM ~ 10⁵ M⁻¹·s⁻¹)"
    - "标记为反例 (NEG-) 因核心结论是 'design 阶段贡献 <1%, evolution 阶段贡献 ~99%' — 反对 'design 是主要工程化贡献' 的常见认知"
    - "evolution 中 emergence 了一个 design 阶段未预期的 catalytic tetrad: 原 design 的 Lys-Tyr-Asp 被 evolution 替换为 Lys-Tyr-Asn-Asp + 结构性 water"
    - "Hilvert 实验室 (ETH) + Baker 实验室 (UW) + Griffiths (CNRS) 合作; ultrahigh-throughput microfluidic droplet selection 是技术 enabler"
tags: [computational_design, directed_evolution, retro_aldolase, HG3, catalytic_tetrad_emergence, NEGATIVE_case, failure_mode_anchor, design_vs_evolution, microfluidics, Hilvert-lab, Baker-lab]
---

## 1. 背景与目标 — 反例性质
- parent: HG3 (computational design, RA-class scaffold derivative); 起始 kcat ~10⁻⁴ s⁻¹ (与 Jiang 2008 RA61 相当)
- 目标 (本论文): 用 microfluidic droplet 高通量 selection 做 ≥17 round directed evolution, 看活性提升上限 + 解析 evolved structure 揭示 catalytic mechanism 的演化
- 反例核心: 18 round 后 HG3.17 kcat/KM ~10⁵ — 提升 ~10⁶× vs. design baseline; **'design 阶段 <1% 贡献, evolution 阶段 >99% 贡献'**

## 2. 决策过程

### 候选位点策略
- 17 round DE: error-prone PCR + saturation + DNA shuffling 组合
- Microfluidic droplet selection — 单细胞封装在水滴, 测定 retro-aldol 活性, FACS-like 分选
- 关键变量: throughput ~10⁸ variants/round, 远超传统 plate (~10⁴)

### 排除的位点 (★ 必填)
- 起始 design 的 catalytic Lys 严格保留
- TIM barrel scaffold backbone 保留
- 但 evolution 多次"违反"了 design 阶段的 assumption (e.g. designed Tyr 被 Asn 替换), 显示 design 排除非绝对

### 计算工具与阈值
- 不依赖 ΔΔG (DE 主导)
- Microfluidic droplet platform + 荧光 readout (retro-aldol 释放 6-methoxy-2-naphthaldehyde)

## 3. 实验结果

### Evolution 进展
| Round | Variant | kcat (s⁻¹) | kcat/KM (M⁻¹s⁻¹) | 提升 |
| --- | --- | --- | --- | --- |
| 0 (HG3 design) | HG3 | ~10⁻⁴ | ~10 | 1× |
| 7 | HG3.7 | ~10⁻³ | ~10³ | 100× |
| **17 (best)** | **HG3.17** | **~10** | **~10⁵** | **~10⁶×** |
| 天然 RuBisCO 参考 | – | ~10 | ~10⁵ | – |

### Catalytic tetrad emergence
| Round | Active site composition |
| --- | --- |
| Design (HG3) | Lys-Tyr-Asp + design-predicted geometry |
| Round 7-12 | Lys-Tyr-Asn 引入 (Tyr 一部分被替换) |
| Round 17 (HG3.17) | Lys-Tyr-Asn-Asp + 结构 water 形成 'catalytic tetrad' — 完全 emergent, design 阶段未预期 |

### 失败案例 (★ 必填) — 本案例的核心
- **设计预测的 catalytic geometry 在 evolution 中显著重构**: Lys-Tyr-Asp triad → 4-residue tetrad + water
- **设计的多个 secondary residues 被 evolution 替换**: 14 个 evolution mutation 中, 多个在 design 时被认为 'optimal' 的位置
- **Design 阶段贡献 <1% 的总活性提升**: 起始 vs final 是 10⁶× 提升, design 占 ~1% (10⁰× → 10⁰× factor 1), evolution 占 ~99% (10⁶× factor)
- **微流控 + droplet selection 是 technical 必需**: 传统 plate selection 无法支持 17 round 的 throughput (10⁸ variants × 17 = 10⁹+ assays)
- **Single-active-site mutation 在 evolved background 不可解释**: HG3.17 移除任一 evolution mutation 全部失活, evolved 状态高度耦合
- **跨 starting design 的 evolution mutation 无可转移性**: HG3.17 上的 14 mutation 不能直接转 RA61 / RA60 等其他 design — 各 design backbone 局部环境差异大

## 4. 学习收获 — 反规则 / anti-rule
- **成立的反规则 (anti-rule)**:
  - **'Computational design baseline 是终点'** 失败 — design 是 1% 贡献者
  - **'Catalytic geometry 被 design 锁定'** 失败 — evolution 大幅重构, 形成 emergent 配置
  - **'Single-residue mutation 经 ddG 排序'** 在 evolved background 无 ROC — evolved enzyme 高度耦合, single-mutation 数据不可外推
- **被推翻的假设**:
  - "Design 设计的 catalytic ensemble 已最优, evolution 仅微调" — 反例: catalytic tetrad 完全 emergent
  - "DE 主要 fix designed 缺陷" — 实际: DE 改变 catalytic mechanism 本身
- **下次类似问题应优先尝试**:
  - 任何 de novo design 接 ≥15 round DE + 高通量 selection (microfluidic droplet 类技术)
  - 接受 evolved enzyme 与 designed 起始物的差异极大 — 不期待 'minor refinement'
  - 解 evolved 结构以理解 catalytic mechanism 的 emergent 特性 (与 design 假设比较)
- **应避免**:
  - 把 design baseline kinetic 当作 method evaluation metric
  - 在 evolved enzyme 上 直接转移 design 阶段的 'rules' (常常无效)

### Anti-retrieval 信号 (★ 强标记)
本案例进入 indices/anti/: 任何"computational design + 不做 ≥15 round DE"的项目应被 vetoed; 任何"在 evolved 蛋白上做 single-mutation ddG 排序"作为主要 ranking 信号被 vetoed.

## 5. 计算 / 实验原始数据
HG3 → HG3.17 evolution mutation 累积 + microfluidic kinetic 数据见 Nat Chem 2017 supplementary; PDB 5AN7 + 起始 HG3 deposit 可比较 active site 重构.
