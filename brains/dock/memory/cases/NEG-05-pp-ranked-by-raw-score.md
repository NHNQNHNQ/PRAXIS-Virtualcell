---
case_id: NEG-05-pp-ranked-by-raw-score
schema_version: 1
docking_type: protein_protein_blind
target_pdb: anti-pattern reference (BPTI-trypsin / ClusPro)
target_class: protease
ligand_type: protein
system_specifics:
  interface_type: transient
tools: [HADDOCK 2.4, ClusPro 2.0]
flexibility_required: rigid
validation_benchmark: CAPRI
key_paper_doi: 10.1038/nprot.2016.169
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-05-pp-raw-score-ranking
tags: [NEG, anti-pattern, PP, cluster-size, HADDOCK-score, ClusPro-score]
---

# NEG-05: PP docking ranked by raw HADDOCK/PIPER score (anti-rule-05)

## Background (anti-pattern)
团队跑 ClusPro blind PP docking on antibody-antigen，按 PIPER score top-1 取 final model 送 cryo-EM
结构验证。**没看 cluster_size**。结果 top-1 PIPER score model 在 CAPRI medium quality
但 cluster_size = 3 (small), 而 cluster #2 (PIPER score 略低) cluster_size = 87 (dominant) 才是真 binding
mode。湿实验 cryo-EM 与 cluster #2 一致，team 选错的 top-1 完全错位。

类似失败模式在 HADDOCK 上：top-1 by HADDOCK_score 经常是 outlier; cluster_size 是 docking landscape
收敛信号（大 cluster 说明很多 trajectory 收敛同一 binding mode）。

## ★ 排除/不做的事
- ❌ **ClusPro PIPER score 单一指标排序** (case dock-003)
- ❌ **HADDOCK top-1 by score 当 final** (case dock-002)
- ❌ **不报 cluster_size or top_5_cluster_sizes** in execution_results
- ❌ **Multi-weight ClusPro 只跑 1 个 weight set** (无多 weight 投票) → 失去 robust signal
- ❌ **HADDOCK with AIR active+passive > 30** → 约束被淹没 (case dock-002)
- ❌ **Skip cluster + take top score directly**

## ★ 失败模式
- **Top score outlier**: 单一物理可行 pose 偶然得高 score, but 不在 docking landscape 主流
- **Cluster #2 / #3 才是 dominant mode**: 大 cluster = 多 trajectory 收敛 = 真 signal
- **C2-symmetric PP** (e.g., antibody-antigen in some symmetric case): cluster_size 分裂；要查 multi-weight 一致性
- **Multi-weight 不一致** (balanced vs electrostatic vs hydrophobic): 真 binding mode 应该 ≥ 3 weight set 出现
- **湿实验 cryo-EM 与 cluster_size top-1 一致率**: ~70%; 与 PIPER score top-1 一致率: ~25% (industry estimates)

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-002 HADDOCK + case dock-003 ClusPro):
1. **Ranking by cluster_size** (primary), score (secondary tie-breaker)
2. **HADDOCK**: cluster top 200 RMSD 5 Å, take cluster representative — NOT top by haddock_score
3. **ClusPro**: ≥ 3 weight sets (balanced + electrostatic + hydrophobic) consensus
4. **AIR for HADDOCK**: active + passive < 30 (case dock-002 lesson)
5. **CAPRI quality 必报**: high/medium/acceptable/incorrect — cluster representative 算

**Why this beats the anti-pattern**:
- Cluster_size 是 sampling-based confidence signal (大 = 高 conf)
- Multi-weight consensus 抗 force field bias
- Score 单 metric 被 outlier dominate, cluster 平均掉

## ★ Validation metric
- design_plan.sanity_checks_planned 缺 `cluster_size_main_ranking` (PP) → BLOCK
- execution_results.cluster_size == null for protein_protein_* → BLOCK
- 对 protein_protein_with_restraints: AIR active + passive > 30 each side → BLOCK (case dock-002)
- 对 protein_protein_blind: weight_sets count < 3 → WARN (case dock-003)

## Lessons → anti-rule
- **anti-rule-05**: PP docking 必按 cluster_size 排; PIPER/HADDOCK score 单指标 → BLOCK; AIR > 30 → BLOCK
- Cross-case evidence: dock-002 (HADDOCK BPTI-trypsin), dock-003 (ClusPro mAb-RBD)
- Confidence: high
