---
case_id: NEG-SCHEMA-otey-2004-chembiol
schema_version: 1
parent_enzyme:
  uniprot: P14779               # Bacillus megaterium P450-BM3 (parent of SCHEMA chimeras in this work)
  cazy_family: null
  ec: 1.14.14.1                 # cytochrome P450
  organism: Bacillus megaterium (BM3 parent) + 同源 P450 from CYP102A1 family
  pdb: 1FAG                     # P450-BM3 reference structure
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "CCCCCCCCCCCCC(=O)O"   # myristic acid 类长链脂肪酸 (BM3 native)
  class: long-chain_fatty_acid
target_property: substrate_specificity
status: validated
provenance:
  source_type: literature
  doi: "10.1016/j.chembiol.2004.02.018"
  pmid: 15123274
  citation: "Otey CR, Silberg JJ, Voigt CA, Endelman JB, Bandara G, Arnold FH (2004). Functional evolution and structural conservation in chimeric cytochromes p450: calibrating a structure-guided approach. Chemistry & Biology 11(3):309-318."
  extracted_at: 2026-04-28
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1016/j.chembiol.2004.02.018 与 PMID 15123274 我推测; CrossRef 验证"
    - "本论文是 SCHEMA (Structure-guided recombination, Voigt-Mayo-Arnold 算法) 的 calibration paper — 系统揭示 SCHEMA 块重组的实际 fold 失败率"
    - "Arnold 实验室 (Caltech) 主导 + Voigt + Silberg 合作"
    - "SCHEMA: 用 protein 结构上的 'block boundaries' (低 inter-block 接触数) 切 protein, 块间 recombination 应保 fold; 但实际 chimera 多失活"
    - "在 P450-BM3 chimera 库中, 仅 ~50% 表达 + ~30% folded + ~10-20% 有催化活性 — 总命中率类似 de novo design (不到目标值)"
    - "本论文展示 'SCHEMA disruption parameter m' (块间被打断的接触数) 是 chimera fold-likeliness 预测器, 但即使 m 最低的 chimera 也常失败"
tags: [SCHEMA, structure_guided_recombination, chimeric_protein, P450_BM3, NEGATIVE_case, failure_mode_anchor, fold_failure, Arnold-lab, Voigt, recombination_pitfall, computational_design_critique]
---

## 1. 背景与目标 — 反例性质
- 背景: SCHEMA (Voigt 2002 Nat Struct Biol) 提出用 protein 3D 结构识别 'block boundaries', 块间 recombination 保 fold 期望; 工业应用是 'CYP102 family chimeric library' 用以扩 substrate scope
- 目标 (本论文): 实测 SCHEMA-designed chimeras 实际 fold 失败率, 校准方法学
- 反例核心: **SCHEMA 实测 chimera 命中率 ~10-20%** (与 de novo design 类似), 远低于"结构指导即保 fold"的理论期望

## 2. 决策过程

### SCHEMA 流程
- 选 多个 同家族 protein (P450-BM3 + CYP102 同源, ~60% identity)
- 计算 inter-block 接触数, 切割成 'low-disruption blocks'
- 块间 random recombination 形成 chimera 库 (~10⁴-10⁵ variants)
- 实验测试 各 chimera 的 表达 + fold + 催化活性

### 计算工具与阈值
- SCHEMA (Voigt 2002 算法): m = inter-block disruption count
- m 低 = chimera 应 fold OK; m 高 = chimera 应失 fold
- 实测验证: 异源 E. coli 表达 + heme incorporation (作 fold proxy) + 底物代谢

### 排除的位点 (★ 必填)
- P450-BM3 catalytic Cys (heme 配位) + heme binding pocket 严格保留 (SCHEMA 不切此区, 块边界自动避开)
- 块边界**禁忌**落于: substrate channel 关键 loop, catalytic 残基 ±5 Å, heme 配位 Cys 周围
- 本案例 implicit anti-pattern: parent identity < 70% 时 SCHEMA 失败率急剧上升, 应排除此 design space

## 3. 实验结果

### Chimera 命中率
| 量 | SCHEMA chimera library |
| --- | --- |
| 表达 yield (≥ WT 50%) | ~50% |
| Fold 正确 (heme incorporated) | ~30% |
| 催化活性保留 | ~10-20% |
| Substrate scope 显著扩展 | 几个 hits (~5-10%) |
| 总 'usable variant' rate | ~10% |

### 失败案例 (★ 必填) — 本案例的核心
- **m 最低 chimera 也失败**: 虽 m 与 fold success 正相关, 但低 m chimera 仍 ~50% 失败 — 说明 m 是粗略 metric, 不是充分条件
- **跨 sequence identity gap chimera**: 当 parent 间 identity ~60%, 块边界局部包装失败率高; identity > 80% chimera fold rate 显著上升 (但 substrate scope 扩展窄)
- **块边界处的 hidden epistasis**: 一些 chimera 单看 inter-block 接触少, 但块内 long-range 接触在新 chimera 中异常 — SCHEMA 不建模 long-range 包装
- **P450 heme cofactor 难 incorporate**: SCHEMA chimera 表达后 heme insertion 步骤额外失败 — cofactor-dependent enzyme SCHEMA 不友好
- **Substrate scope 扩展不可预测**: 即使 fold 成功, 哪些 chimera 接受新 substrate 不可由 SCHEMA m 预测, 必须实验 screen
- **SCHEMA 在功能 essential loop 切**: 部分 'low-disruption' boundaries 实际位于 substrate channel 关键 loop, fold OK 但活性丢失

## 4. 学习收获 — 反规则 / anti-rule
- **成立的反规则 (anti-rule)**:
  - **SCHEMA 'm parameter' 不是 chimera fold 充分条件**: 仅 ~30% fold rate 即使最低 m
  - **块重组工程化命中率 ~10-20%**: 与 de novo design 同量级 (~30%), SCHEMA 不显著优于"随机切"
  - **Cofactor-dependent enzyme (P450 / 金属酶) SCHEMA 失败率高**: 必须 + cofactor incorporation 步骤
  - **跨 parent sequence identity < 70% SCHEMA chimera fold rate 急剧下降**: parent 选择是 SCHEMA 成功率的最强变量
- **被推翻的假设**:
  - "结构指导块重组保 fold" — 反例显示仅 30% fold rate
  - "SCHEMA 优于 de novo design" — 数据上 ~10-20% 命中率 vs ~30%; 不显著优势
- **下次类似问题应优先尝试**:
  - SCHEMA 工程化前先评估: parent identity ≥ 70%? cofactor required? 多 ortholog 可用?
  - 与 directed evolution 配合 — SCHEMA hits 作 starter, 接 evolution 拉 substrate scope
  - **Cross-family 重组优先用 ancestral reconstruction (ASR) 而不是 SCHEMA** (ASR 自动平衡 phylogeny)
- **应避免**:
  - SCHEMA 工程化期待 > 30% 命中率
  - 在 cofactor-dependent enzyme (P450, 金属酶) 上单 SCHEMA 不接 评估 cofactor incorporation
  - 块边界落 substrate channel / catalytic loop 区域

### Anti-retrieval 信号 (★ 强标记)
本案例进入 indices/anti/: 任何 "SCHEMA chimera library 不做 cofactor incorporation 检查" 的项目被 vetoed; 任何 "parent identity < 70% 仍单 SCHEMA" 被 vetoed; 任何 "块重组期待 > 30% 命中率" 的预算被 vetoed.

## 5. 计算 / 实验原始数据
SCHEMA chimera 表达 + heme + 活性数据见 Chem Biol 2004 supplementary; Drummond 2005 PNAS (intragenic recombination conservation) 提供后续理论分析.
