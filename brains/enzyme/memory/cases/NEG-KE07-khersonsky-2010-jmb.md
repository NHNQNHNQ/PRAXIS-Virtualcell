---
case_id: NEG-KE07-khersonsky-2010-jmb
schema_version: 1
parent_enzyme:
  uniprot: null
  enzyme_family: synthetic_design_anchor
  cazy_family: null
  ec: 4.99.1.7                  # tentative; Kemp elimination 化学反应不在常规 EC, 多归入 4.99 类
  organism: synthetic_design
  pdb: 3IIO                     # KE07 design 早期 deposit (Röthlisberger 2008 Nature)
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "[O-][N+](=O)c1ccc2c(c1)c(no2)C"   # 5-nitrobenzisoxazole (Kemp substrate)
  class: nitro_benzisoxazole / Kemp_elimination_substrate
target_property: activity        # 计算设计 baseline 极低, directed evolution 提升 ~400×
status: partial                  # 反例: 单纯计算设计活性远不够工业, 必须 experimental optimization
provenance:
  source_type: literature
  doi: "10.1016/j.jmb.2009.12.031"
  pmid: 20036254
  citation: "Khersonsky O, Röthlisberger D, Dym O, Albeck S, Jackson CJ, Baker D, Tawfik DS (2010). Evolutionary optimization of computationally designed enzymes: Kemp eliminases of the KE07 series. Journal of Molecular Biology 396(4):1025-1042."
  extracted_at: 2026-04-28
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1016/j.jmb.2009.12.031 与 PMID 20036254 我推测; CrossRef 验证"
    - "原始 KE07 设计来自 Röthlisberger D et al. Nature 2008 (computational de novo design); 本 2010 JMB 论文是 directed evolution 后续"
    - "PDB 3IIO 我推测为 evolved KE07 round 7 deposit; 原始 KE07 design 在 3DK9 等系列"
    - "Kemp elimination 化学: 5-nitrobenzisoxazole + base → 2-cyano-4-nitrophenol; 由 Asp/Glu/His 通用 base 催化"
    - "本案例标记为反例 (NEG-) 因核心结论是: 纯计算设计 baseline kcat ~10⁻⁵ s⁻¹ 不实用, 必须 ≥17 round directed evolution 提升 ~400× 才接近 'reasonable' enzyme 活性"
    - "Tawfik 实验室 (Weizmann) + Baker 实验室 (UW) 合作; 反例性质是双方都同意的 'computational design 还远不够' 的证据"
tags: [computational_design, directed_evolution, Kemp_elimination, de_novo_design, post_design_optimization, NEGATIVE_case, failure_mode_anchor, design_limit, Baker-lab, Tawfik-lab]
---

## 1. 背景与目标 — 反例性质
- parent: KE07, computational de novo designed Kemp eliminase, scaffold 基于 TIM barrel (1thf 衍生); 设计目标是 catalyze Kemp elimination (5-nitrobenzisoxazole)
- 起始性质: 计算 designed KE07 round 0 kcat ~0.1 s⁻¹, kcat/KM ~50 M⁻¹·s⁻¹ — 远低于天然酶 (~10⁵-10⁷)
- 目标 (本论文): 通过 17 round directed evolution 优化计算设计 baseline, 看活性能提升多少 + 看 evolution 怎么改造 active site
- 反例核心: 计算设计单独不足以达到 'usable' enzyme 活性, 必须配合 experimental directed evolution

## 2. 决策过程

### 候选位点策略
- 17 round random mutagenesis (error-prone PCR) + 单点 saturation 在 Tawfik 组高通量 plate 筛
- 不固定位点; selection 自动找有效 mutation
- 累积 mutation > 11 个跨 17 round

### 排除的位点 (★ 必填)
- 计算设计的 catalytic Glu101 (general base, KE07 设计核心) 严格保留 — 突变即失活
- TIM barrel β-strand backbone fold 约束 (protein scaffold) 保留

### 计算工具与阈值
- 不再依赖计算设计 (本论文是 post-design evolution)
- Plate-based Kemp eliminase 活性 readout (吸光度变化 380 nm)

## 3. 实验结果

### 17 round evolution 进展
| Round | kcat (s⁻¹) | kcat/KM (M⁻¹s⁻¹) | 提升因子 |
| --- | --- | --- | --- |
| Round 0 (computational) | 0.1 | 50 | 1× |
| Round 7 | ~5 | ~1500 | ~30× |
| Round 17 (best) | ~10 | ~2000 | ~400× |
| 天然酶参考 | 10²-10³ | 10⁶-10⁷ | – |

### 失败案例 (★ 必填) — 这是本案例的核心
- **计算设计 active site geometry 偏离最优 catalytic geometry**: round 1-3 evolution 主要 'fix' 了 designed catalytic Glu 与 substrate 的几何错位 — 设计预测的 substrate orientation 与实际不一致
- **计算设计的稳定性预测过乐观**: KE07 设计 ΔΔG -预测稳定, 实测在 37 °C melting; 后续 evolution 引入 stabilizing mutation 才达到 60 °C+
- **多个 'computationally rational' mutation 在实验不工作**: round 4 中 Baker 组建议的 Asn → Asp mutation 计算预测增 catalysis, 实测降 50% 活性
- **Active site 邻位 (5 Å) 残基预期对 catalysis 贡献小, 实验显著重要**: 多个 round 12+ 突变是 distal residues, 计算时被忽略
- **17 round 后仍达不到天然酶活性**: 即使大量 evolution, kcat/KM ~2000 远低于天然酶 ~10⁶ — 计算设计 + DE 联合仍有数量级差距
- **跨 KE design (KE07, KE10, KE15, KE16) 的 evolved mutation 不可转移**: 不同 scaffold 上的 mutation 无家族转移性 — 与 case-distilled rule 形成对比

## 4. 学习收获 — 反规则 / anti-rule
- **成立的反规则 (anti-rule)**:
  - **'Computational de novo design 一步到位' 是错觉**: 当前最优计算设计 baseline 仍距实用酶活性 4-5 个数量级
  - **'Design + 短 round evolution 即可'** 失败 — KE07 需要 17 round 才接近 useful
  - **'Computationally rational mutation 总能改善活性'** 失败 — 多个反例; 只有 selection 才可信
  - **跨 designed scaffold 经验转移**: 不能直接转 — 与天然酶家族经验转移规则相反
- **被推翻的假设**:
  - "RosettaDesign + matchup → working enzyme" — 多次反例
  - "计算预测的 catalytic geometry 准确" — 实测 几何 偏离, 是 evolution 主要 fix 对象
- **下次类似问题应优先尝试**:
  - 任何 de novo 设计酶, 接 ≥10 round directed evolution 作为 mandatory step
  - 设计阶段保 design 简单 (single catalytic residue), 让 evolution 完成 catalytic geometry 优化
- **应避免**:
  - 直接发表计算设计酶的 'usable' claim 而无 directed evolution 配合
  - 把 Rosetta ddG 预测当作可信 mutation 排序 — 在 designed enzyme 上 ROC 极差

### Anti-retrieval 信号 (★ 强标记)
本案例进入 indices/anti/ 后, 任何"computational design + 不评估 directed evolution"的工程化候选应被 vetoed; 任何"ΔΔG / Rosetta 预测稳定就直接采用 mutation"的策略被 vetoed.

## 5. 计算 / 实验原始数据
17 round mutation 累积谱系 + per-round kinetic 数据见 JMB 2010 supplementary; Röthlisberger 2008 Nature 提供原始计算设计数据.
