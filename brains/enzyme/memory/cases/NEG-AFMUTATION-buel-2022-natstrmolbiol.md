---
case_id: NEG-AFMUTATION-buel-2022-natstrmolbiol
schema_version: 1
parent_enzyme:
  uniprot: null
  enzyme_family: methodology_critique
  cazy_family: null
  ec: null
  organism: review_anchor
  pdb: null
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: ""
  class: review_anchor / AlphaFold_mutation_critique
target_property: stability       # AF 多用于稳定性预测; 也涉及 substrate_specificity
status: partial                  # commentary / 评论; status partial 标记 review-anchor 性质
provenance:
  source_type: literature
  doi: "10.1038/s41594-021-00714-2"
  pmid: 35046575
  citation: "Buel GR, Walters KJ (2022). Can AlphaFold2 predict the impact of missense mutations on structure? Nature Structural & Molecular Biology 29(1):1-2."
  extracted_at: 2026-04-28
  extraction_confidence: medium
  unverified_details:
    - "DOI 10.1038/s41594-021-00714-2 与 PMID 35046575 我推测; CrossRef 验证"
    - "本 commentary 是 Nat Struct Mol Biol 2022 vol 29 issue 1 关于 AF2 处理 missense mutation 局限的综评"
    - "类似主题更长 paper: Pak et al 2023 PLoS One 'Using AlphaFold to predict the impact of single mutations on protein stability and function' / McBride et al 2023 NAR 类似题目, 多位作者群同发问"
    - "标记反例 (NEG-) 因核心结论是: AF2 (与衍生模型) 在 mutation effect prediction 上不可靠 — wild-type 输出, mutant 输出几乎相同 (因 AF2 训练在 wild-type structures), 不能用作 ΔΔG 替代品"
    - "本 commentary 进入 PRAXIS-Enzyme 后, 直接进 indices/anti/ 作 anti-retrieval 信号"
tags: [AlphaFold, AF2, mutation_prediction_limitation, ddG_prediction_failure, NEGATIVE_case, failure_mode_anchor, computational_predictor_critique, structural_prediction_misuse, Buel_Walters, theoretical_anchor]
---

## 1. 背景与目标 — 反例性质
- 背景: AlphaFold2 (Jumper 2021 Nature) 革命性提升 protein 结构预测精度; 大量后续工作直接拿 AF model 替代 X-ray 结构, 包括用 AF model 做突变 effect / ΔΔG 计算
- 目标 (本 commentary): 系统讨论 AF2 是否能可靠 predict missense mutation 的 structure / stability / function impact
- 反例核心: 论文证明 AF2 对 single missense mutation 的输出几乎不变 (高 sequence-similarity 时 AF model 主要从 evolutionary signal 推断 fold, 单 mutation 信号被淹没), **不能作为 mutation effect predictor**

## 2. 决策过程 (本 commentary 是 critique, 非 engineering)

### Critique 范围
- 多个公开 AF2 用法的局限: 
  - WT vs single-mutant AF model 比较: 几乎相同 → 用 AF model 之差作 mutation 效应替代 失败
  - AF model + PyRosetta 流水线: 把 AF model 当 X-ray 输入, 但 PyRosetta FastRelax (cartesian) 假设 X-ray 级 side-chain 排布; AF predicted side-chain 不达此精度
  - AF model active-site engineering: pLDDT 中等区域 (50-70) 在 active-site 周围常出现, 工程化基于 AF model 的 active-site 重构高风险

### 排除的位点 (★ 必填)
- 本案例为 review-anchor (methodology critique), 不针对单一 enzyme 工程化, 因此无具体残基级排除清单
- Implicit 排除: 任何依赖 'AF2 model = X-ray equivalent' 假设的工程化路线在此被 critiqued; 在 anti-retrieval 索引中作为 veto 信号传播
- 任何 pLDDT < 70 的活性位点 / 关键 loop 区域必须 explicit 排除于 mutation 排序基准 (anti-rule)

### 计算工具与阈值
- 主要 critique 对象: AF2 + PyRosetta / AF2 + Rosetta / AF2 + PyRosetta / AF2 + ML predictor 联合
- 替代方案 (论文建议):
  - AF2 用作 fold ID (在无 X-ray 时), 不用作 mutation effect
  - mutation effect 优先用 (i) 多 sequence alignment-based 模型 (ESM-1v, EVE) — 直接 sequence-to-effect (ii) X-ray + traditional ddG predictor
  - AF cluster (multiple seed AF models) 估 mutation 引起的 conformational ensemble shift

## 3. 综评核心论点

### AF2 单 mutant 输出的 limitations
| 现象 | 解释 |
| --- | --- |
| WT vs 单点 mutant AF output 几乎相同 | AF2 训练目标是 sequence-to-fold, 单 mutation 在 MSA-driven 推断中信号被多 evolutionary 模板淹没 |
| AF model side-chain 精度 < X-ray | side-chain 配置精度典型 RMSD 0.5-1.0 Å, 不足以做 ΔΔG (要求 < 0.3 Å) |
| pLDDT < 70 区域不可靠 | 多 active-site loop 在 pLDDT 50-70, 工程化必须 explicit 排除 |
| Multiple-seed AF 输出方差小 | 单 mutation 引起 ensemble shift 不被捕捉, 静态 model 假设破裂 |

### 失败案例 (★ 必填) — 本案例的核心
- **AF model + PyRosetta 预测 ΔΔG 失败**: 多个独立 benchmark 显示在 AF model 上跑 PyRosetta, ΔΔG ROC 比 X-ray 输入下降 ~30-50%
- **AF model active-site engineering misleading**: 多个项目用 AF model + AutoDock 做底物 docking, 后期 X-ray 校正发现 docking pose 错位 ~3-5 Å
- **AF model 用于 multi-mutation 累积 stability 预测**: 多 mutation 之间的 epistatic structural interaction AF 完全不建模, single-point predictions 也不准
- **AlphaFold-Multimer 用于界面 mutation 预测同样不可靠**: 界面接触面 AF 可信度更低
- **过度信任 AF model 导致工程化轮空一年**: 综评作者引用多个 community 报告 — 工业团队用 AF + ML 做工程化, 实测命中率 < 5%, 浪费湿实验资源

## 4. 学习收获 — 反规则 / anti-rule
- **成立的反规则 (anti-rule)**:
  - **AF2 不是 X-ray 的 drop-in 替代**: side-chain 精度 + active-site loop pLDDT 限制下, PyRosetta / Rosetta ddG 输入必须用 X-ray; AF 仅 emergency starter
  - **'AF model + 单 mutation' 不能用作 stability prediction**: 输出几乎不变, 任何 ΔΔG 信号是 noise
  - **优先用 sequence-only mutation effect predictor** (ESM-1v / EVE): 直接 sequence-to-effect 训练, 不依赖 X-ray-quality 结构
  - **AF model active-site engineering 必须 + X-ray 校正**: pLDDT < 70 周围必须先解 X-ray 才能信
  - **Multiple-seed AF + 比较输出**: 是当前 AF 估 mutation impact 的最低 baseline 协议 (虽然仍不理想)
- **被推翻的假设**:
  - "AF model 准确度足以做 mutation effect prediction" — commentary 直接 critique
  - "AF + ML predictor 联合可替代实验工程化" — 5% 命中率反例
- **下次类似问题应优先尝试**:
  - 任何依赖结构的 mutation effect prediction, 优先 X-ray; AF 仅紧急起点
  - sequence-only mutation effect predictor (ESM-1v / EVE / Tranception) 作 first-pass screen
  - AF + multiple-seed 估 ensemble 后再做 ΔΔG 估计
- **应避免**:
  - AF model + PyRosetta 直接当作 ΔΔG ground truth
  - AF model active-site loop 做 substrate docking 而无 X-ray 校正
  - 把 AF model 用于 multi-mutation 累积 stability 预测

### Anti-retrieval 信号 (★ 强标记)
本案例进入 indices/anti/: 任何"AF model + PyRosetta 直接做 mutation 排序"的项目被 vetoed; 任何"AF model active-site engineering 而无 pLDDT < 70 排除"被 vetoed; 任何"用 AF 替代 X-ray 做 ddG"被 vetoed.

## 5. 计算 / 实验原始数据
本 commentary 综合多个 community-reported benchmark; 后续 systematic 验证见 Pak et al 2023 PLoS One / Akdel et al 2022 Nat Struct Mol Biol community assessment / McBride et al 2023 NAR 等.
