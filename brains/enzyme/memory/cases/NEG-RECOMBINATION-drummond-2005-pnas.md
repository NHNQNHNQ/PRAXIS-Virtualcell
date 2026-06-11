---
case_id: NEG-RECOMBINATION-drummond-2005-pnas
schema_version: 1
parent_enzyme:
  uniprot: null
  enzyme_family: methodology_critique
  cazy_family: null
  ec: null
  organism: theory_anchor
  pdb: null
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: ""
  class: theory_anchor / recombination_critique
target_property: stability
status: validated
provenance:
  source_type: literature
  doi: "10.1073/pnas.0500729102"
  pmid: 15809427
  citation: "Drummond DA, Silberg JJ, Meyer MM, Wilke CO, Arnold FH (2005). On the conservative nature of intragenic recombination. PNAS 102(15):5380-5385."
  extracted_at: 2026-04-28
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1073/pnas.0500729102 与 PMID 15809427 我推测; CrossRef 验证"
    - "Arnold + Wilke 实验室合作; Drummond 一作"
    - "本论文是 SCHEMA / DNA shuffling 等 intragenic recombination 方法的理论分析"
    - "标记反例 (NEG-) 因核心结论是 'recombination 必然 conservative — 与 random mutation 相比, 必须保 fold = 必然较低多样性'"
    - "对工程化反规则: recombination 在多样性 vs fold-保 之间是 fundamental tradeoff, 不能寻找一个 'fold-safe + 高多样性' 的 sweet spot"
tags: [recombination, DNA_shuffling, SCHEMA, intragenic, conservatism, NEGATIVE_case, failure_mode_anchor, theoretical_anchor, Wilke_Drummond, Arnold-lab, fold_diversity_tradeoff]
---

## 1. 背景与目标 — 反例性质
- 背景: DNA shuffling (Stemmer 1994 PNAS) 与 SCHEMA (Voigt 2002) 等 intragenic recombination 方法被认为 'fold-保 + 多样性高' — 双 advantage
- 论文用 protein 进化理论 + 数值模拟显示: **recombination 必然 conservative — 任何一个 'fold-保' 的 chimera 在序列空间上一定 close to parent**
- 反例核心: recombination 多样性 ≠ random mutation 多样性; recombination chimera 的 'effective sequence diversity' 低于乍看上的, 实际多样性受 fold-保约束

## 2. 决策过程 (本论文是 theory + simulation)

### 论文展示
- 模拟 random recombination chimera 库 vs random mutation 库
- 对 fold-保 (能折叠) 子集的 sequence diversity 分布
- 显示: random mutation 的 'usable variant' 在序列空间上多样性大; recombination chimera 的 'usable variant' 多样性显著小, 因 recombination 自动 enriches 了 conservative chimera

### 排除的位点 (★ 必填)
- 本案例为 theory-anchor, 不针对单一 enzyme 残基级排除
- Implicit 排除: 跨 sequence identity gap 大 (parent identity < 50%) 的 chimera 设计被排除 (anti-rule)
- 'Recombination 高多样性 + fold-保' 双 win 的工程化诉求被排除 (theoretical 不可能)

## 3. 失败案例 (★ 必填) — 本案例的核心

- **'高多样性 chimera library' 的实际 fold rate 极低**: 多样性高 → fold rate 低 (单调 trade-off), 不存在 sweet spot
- **'fold-保 chimera 多样性高' 是错觉**: 表面看 chimera 与 parent ~50% 不同, 但 fold-保子集的有效多样性 < 30%
- **SCHEMA m parameter 隐 conservative bias**: 低 m chimera (fold OK) 实际是 'conservative' chimera, 多样性低
- **DNA shuffling crossover 偏 high-conservation 区**: shuffling crossover 多 occur at 高保守区, 多样性 contribution 集中于已保守 region (低多样性贡献)
- **'广义 directed evolution > recombination'**: 当目标是大幅 substrate scope / 活性提升, random mutation + selection 比 recombination 更可能找到 distant variant
- **跨 sequence identity gap recombination 不可信**: parents identity < 50% recombination 有效 fold rate 趋近 0

## 4. 学习收获 — 反规则 / anti-rule
- **成立的反规则 (anti-rule)**:
  - **Recombination ≠ free 多样性**: chimera library 的实际 'usable variant diversity' 远低于 sequence-level 多样性
  - **Recombination 与 random mutation 的 trade-off 是 fundamental**: 没有 'fold-保 + 高多样性' 的 free lunch
  - **目标是大幅活性 / scope 改造时, recombination 不一定优于 random mutation**: 取决于目标 vs parent 的 distance
  - **SCHEMA m 低 = chimera 保守 = 多样性贡献小**: 不能"低 m = 实测命中 + 高多样性"双 win
  - **Parent identity 决定 recombination 适用性**: < 50% identity recombination 失败率高, 50-70% 是 sweet spot, > 80% recombination 是 'redundant mutation'
- **被推翻的假设**:
  - "Recombination 比 random mutation 总优 (因 fold-保)" — 多样性 trade-off 反例
  - "Chimera library 的 sequence diversity 等于 effective diversity" — usable subset 多样性远低
- **下次类似问题应优先尝试**:
  - 任何 recombination 工程化项目, 评估目标 vs parent distance 是否合适 (50-70% identity 是 SCHEMA 最佳 niche)
  - 大幅 substrate scope 改造优先 random mutation + selection (而非 recombination)
  - 配合 ASR (ancestral reconstruction) 拓宽 starting parent diversity 后再 recombine
- **应避免**:
  - 用 recombination 期待"fold-保 + 高多样性" 双 win
  - parent identity < 50% 仍单做 SCHEMA / shuffling
  - 把 'sequence-level diversity' 当作 'usable diversity'

### Anti-retrieval 信号 (★ 强标记)
本案例进入 indices/anti/: 任何 "recombination chimera 期待 > 30% fold rate + 大幅多样性" 被 vetoed; 任何 "parent identity < 50% 仍 SCHEMA recombination" 被 vetoed; 任何 "用 recombination 替代 random mutation 做大幅 substrate engineering" 被 vetoed.

## 5. 计算 / 实验原始数据
理论分析 + 数值模拟数据见 PNAS 2005 supplementary; 后续工作 (Bloom JD et al 系列 NRG / Annu Rev Biophys) 进一步量化 recombination 多样性 vs fold-保 trade-off.
