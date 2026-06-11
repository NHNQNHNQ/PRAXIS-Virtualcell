---
case_id: NEG-13-dud-e-no-baseline
schema_version: 1
docking_type: protein_ligand
target_pdb: anti-pattern reference (DUD-E enrichment)
target_class: kinase
ligand_type: small_mol_drug_like
system_specifics:
  ligand_drug_likeness: drug_like
tools: [AutoDock Vina 1.2.5]
flexibility_required: rigid
validation_benchmark: DUD-E
key_paper_doi: 10.1021/jm300687e
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-01-no-redock-self-test
tags: [NEG, anti-pattern, DUD-E, enrichment, no-baseline, AUC-only]
---

# NEG-13: DUD-E enrichment shipped without per-target redock baseline (anti-rule-01)

## Background (anti-pattern)
团队报告 "Vina 在 DUD-E AKT1 上 EF1% = 12.5, AUC = 0.78"，**没在同一 receptor 上验证 redocking
top-1 ≤ 2 Å rate**。后续 prospective screen 命中率仅 0.3% (vs 文献 5%)。Post-hoc redock self-test
显示该 AKT1 crystal 上 Vina top-1 ≤ 2 Å rate 仅 22% (anti-pattern threshold 30%)。
**EF1% benchmark good 但 prospective fail** — receptor-specific docking 质量没验证。

## ★ 排除/不做的事
- ❌ **DUD-E enrichment metric (EF / AUC) 当 prospective predictor**: retrospective benchmark 不预测 prospective performance
- ❌ **Vina default 跳过 ligand prep**: DUD-E ligands 已是 prepared formats — 真实 prospective screen 必 enum stereo/protonation/tautomer
- ❌ **不做 receptor-specific redock self-test**: per-target sanity gate 必须 (case dock-001 lesson)
- ❌ **DUD-E decoys 当 prospective negatives**: decoys 是 property-matched, 不代表实际 screening library
- ❌ **跨 target enrichment 平均**: 单 target 22% top-1 ≤ 2 Å vs 全 DUD-E 平均 50% — 不能拉平均

## ★ 失败模式
- **EF1% 好但 redock fail**: docking 区分 active vs decoy (binary task) 比 binding pose 准 (regression task) 容易
- **Property-matched decoys**: 同 logP/MW 但化学骨架不同的 decoys 容易拒绝，给假高 AUC
- **DUD-E 训练-测试泄漏**: many ML scoring functions 在 DUD-E 上 train+test, AUC 1.0 但 prospective 0.6
- **Prospective screen hit rate 0.3%**: industry baseline 5%, 此 pipeline 16x 低
- **Verifying Vina default for new target**: 必须 case dock-001 redock benchmark first

## ★ 方法选择决策链 (correct alternative)
**Correct path**:
1. **Per-target redock self-test FIRST** (case dock-001) — 30% threshold 强制
2. **Both metrics**: redock self-test + DUD-E enrichment — both informative, neither alone sufficient
3. **Prospective screen requires**: redock_self_test ≥ 30% + EF1% > 5 + multi-method consensus
4. **For known DUD-E-trained ML scoring functions** (RF-Score, NNScore): cross-validate on PDBbind time-split (not DUD-E)

## ★ Validation metric
- DUD-E benchmark report 缺 per-target `redock_self_test` → BLOCK
- AUC > 0.8 但 redock top-1 ≤ 2 Å rate < 30% → mark `prospective_unreliable`

## Lessons → anti-rule
- **anti-rule-01 (extension)**: DUD-E EF/AUC 不替代 redock self-test; 两者都需 (multi-anchor with NEG-01)
- Cross-case evidence: NEG-01 + NEG-13 + dock-001
- Confidence: high
