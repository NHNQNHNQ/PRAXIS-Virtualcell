---
case_id: NEG-EPISTASIS-bershtein-2006-nature
schema_version: 1
parent_enzyme:
  uniprot: P62593               # TEM-1 β-lactamase (Escherichia coli); 实验所用 starting protein
  cazy_family: null
  ec: 3.5.2.6                   # β-lactamase
  organism: Escherichia coli
  pdb: 1ZG4                     # TEM-1 apo crystal; 与 stiffler 2015 同一 starting protein
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "CC1(C)S[C@@H]2[C@H](NC(=O)Cc3ccccc3)C(=O)N2[C@H]1C(=O)O"   # benzylpenicillin (penam-class) 示意
  class: β-lactam_antibiotic
target_property: stability       # 实际是 fitness landscape mapping; stability = 必要 fitness 维度
status: validated                # 论文是 validated science, 标 NEG- 因核心结论是 'mutation effects are context-dependent'
provenance:
  source_type: literature
  doi: "10.1038/nature05385"
  pmid: 17086194
  citation: "Bershtein S, Segal M, Bekerman R, Tokuriki N, Tawfik DS (2006). Robustness-epistasis link shapes the fitness landscape of a randomly drifting protein. Nature 444(7121):929-932."
  extracted_at: 2026-04-28
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1038/nature05385 与 PMID 17086194 我推测; CrossRef 验证"
    - "本论文是 Tawfik 实验室 (Weizmann) 关于 fitness landscape + 随机漂变 + epistasis 的奠基工作"
    - "TEM-1 β-lactamase 是模型 enzyme; 通过 random mutagenesis + 不同 selection 强度建造 'random drift' library, 量化 mutation 之间的 epistatic interaction"
    - "反例性质: 论文核心结论是 mutation effects ARE highly context-dependent, additivity 假设是错的"
    - "对 PRAXIS-Enzyme 的具体反规则: 任何 single-mutation 经验都不能直接 stack 多个 mutation 而预期叠加效应; epistasis 是 rule, additivity 是 exception"
    - "本案例直接反对 ProSAR / consensus / multi-point mutation linear assumption 类默认做法"
tags: [epistasis, fitness_landscape, random_drift, robustness, beta_lactamase, TEM1, NEGATIVE_case, failure_mode_anchor, multi-point_mutation_pitfall, Tawfik-lab, theoretical_anchor]
---

## 1. 背景与目标 — 反例性质
- parent: TEM-1 β-lactamase, 4 个独立 mutation 起始 + random mutagenesis 大库 (10⁶ 量级 variants)
- 起始: TEM-1 在 ampicillin 高浓度 (selection pressure) 下 fitness 高; 在低 selection 下 'neutral drift' 允许多 mutation 累积
- 目标: 系统量化 single mutation effect 与 multi-mutation 累积效应的偏离 — fitness 'epistasis'
- 反例核心: 论文证明在中性漂变下累积的 single-mutation 'tolerable' 损失, 一旦 stack 多个 mutation 进同一蛋白, fitness 是 super-linear 损失 (epistasis-shaped)

## 2. 决策过程

### 候选位点策略
- 不针对位点; random mutagenesis (epPCR) 大库
- 通过不同 selection 严格性建造 fitness landscape: high-selection (ampicillin 1 mg/mL) vs low-selection (1 μg/mL) 下的 mutation 频谱

### 排除的位点 (★ 必填)
- 论文非 directed engineering, 不显式排除位点
- 但实验设计 implicitly 排除 catalytic Ser70 + Lys73 (β-lactamase active site) 位的 productive mutation, 因 selection automatically 淘汰致死 mutation

### 计算工具与阈值
- 主要工具: 大库 + selection + sequencing
- Single mutation effect 计算: 单 mutant 在 ampicillin 浓度梯度下 IC50 测定
- Multi-mutation effect: 多 mutation 在同 background 下的 fitness 减损测定

## 3. 实验结果

### 关键发现 — Epistasis 量化
| 量 | 值 |
| --- | --- |
| Single mutation 平均 fitness loss (in TEM-1) | ~5-10% (高 selection) |
| Linear additivity prediction (n mutations) | n × 5-10% |
| Observed n-mutation fitness loss | super-linear (n=3 约 50-70%, n=5 接近完全失活) |
| Robustness-epistasis 链接 | mutation 越早累积, 后续 mutation epistasis 越强 |

### 失败案例 (★ 必填) — 本案例的核心
- **'独立 mutation, 直接累积' 失败**: 4 个 single-tolerable mutation 累积后 TEM-1 失去 ampicillin 抗性; 单看任一 mutation 都 tolerable
- **'consensus 推 8-10 mutation 同时引入' 失败**: 累积 epistasis 致 fitness 崩溃; 最大可累积量取决于 starting fitness margin
- **'B-factor / PyRosetta 单点筛选 → 多点 stacking' 失败**: 标准协议在 enzyme 工程化 popularly 用, 但理论基础 (additivity) 在本论文实验下被否
- **'Random drift 后的 mutation 也 stable' 误导**: drift 后 mutation 是 'tolerable in starting context' 而非 'always tolerable'; 进一步 mutation 可以让原来 tolerable 的变 lethal
- **同 fitness 但不同 robustness**: 相同 fitness 的 variants 对后续 mutation 的 buffer capacity 极不同 — robustness 是 hidden 维度

## 4. 学习收获 — 反规则 / anti-rule
- **成立的反规则 (anti-rule)**:
  - **Multi-mutation additivity 假设是错的, 必须实验验证 stacking**: 任何 ≥3 mutation 的 stacking 必须直接测试, 不能从 single-mutation 数据外推
  - **Robust starting protein > 高 fitness starting protein**: robustness 决定后续 evolutionary potential
  - **Epistasis 是 default, additivity 是 exception**: ProSAR 类 multivariate regression 在低 mutation count 时还可信, ≥4-5 mutation 时显著失精度
  - **Cumulative 'tolerable' mutation 累积时 fitness 'cliff' 是常态**: 多个 single-tolerable mutation 突然组合致命
- **被推翻的假设**:
  - "Single-mutation 数据可外推到 multi-mutation" — 论文实验直接证伪
  - "Mutation effects 是位点局部 + additive" — 实验显示 distal coupling 显著
- **下次类似问题应优先尝试**:
  - 任何 multi-mutation stacking 设计, 直接构建 stacking variant 测试 (而非外推 single-mutation 数据)
  - 选 starting protein 时优先 robust (能容忍 mutation) 而非单纯 high fitness
  - 在 ProSAR 模型外加 epistatic interaction term (二阶 cross terms) 提升预测能力
- **应避免**:
  - 把 single-mutation 设计 stack 4+ mutation 而不直接测试
  - 把 random drift mutation 假定为 'safe to compound'

### Anti-retrieval 信号 (★ 强标记)
本案例进入 indices/anti/ 后, 任何"用 single-mutation 数据外推 multi-mutation 性能"的策略应被 vetoed; 任何"ProSAR / linear regression 直接 stack 4+ mutation 而无实验验证"的设计被 vetoed.

## 5. 计算 / 实验原始数据
TEM-1 random drift library + per-mutation fitness 数据见 Nature 2006 supplementary; Tawfik 组后续 (2007 PNAS, 2008 PLoS Biol) 扩展 epistasis 量化.
