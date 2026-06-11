---
case_id: NEG-01-no-redock-self-test
schema_version: 1
docking_type: protein_ligand_redocking
target_pdb: PDBbind core set (anti-pattern reference)
target_class: mixed
ligand_type: small_mol_drug_like
system_specifics:
  ligand_drug_likeness: drug_like
tools: [AutoDock Vina 1.2.5]
flexibility_required: rigid
validation_benchmark: PDBbind
key_paper_doi: 10.1021/acs.jcim.8b00545
status: anti_pattern
source: praxis_seed_neg
anti_rule: anti-rule-01-no-redock-self-test
tags: [NEG, anti-pattern, PL, redocking, no-self-test, black-box]
---

# NEG-01: Production PL docking shipped without redock self-test (anti-rule-01)

## Background (anti-pattern)
团队拿到一个新 kinase target (apo crystal)，直接对 ChEMBL kinase library (~10k 化合物) 跑 Vina docking,
按 top-1 score 排前 100 个化合物送湿实验。**没有先在已知 holo crystal complex 上做 redocking
self-test 验证 pipeline pose accuracy**。结果湿实验 hit rate < 1% (industry 平均 5-15%)。
事后 post-hoc redock 才发现该 receptor 在 PDBbind 平均 top-1 ≤ 2 Å rate 仅 18% — pipeline 本身不及格。

## ★ 排除/不做的事 (Anti-pattern - DO NOT DO)
- ❌ **Production VS / docking 之前不做 redocking benchmark**: black-box pipeline 不可信
- ❌ **直接相信 Vina top-1 score 当 final ranking** without per-target sanity gate
- ❌ **不区分"通用文献 success rate" vs "我自己 target 上的 success rate"**: PDBbind 平均 50-60% 不代表本 target
- ❌ **跳过 ligand prep 重 enum** (tautomer/protonation/stereo) — 信息泄漏会让 redock 假高
- ❌ **不报 redock_self_test 字段在 design_plan**

## ★ 失败模式 (concrete failure modes)
- **湿实验 hit rate < 1%** (industry 5-15%) → 资金/时间损失
- **False-positive enrichment**: top-100 中含 PAINS / 反应性化合物 / 高 strain 失败 pose
- **下游 ADMET / 选择性 panel 浪费**: 由 docking-rank 错配的化合物
- **Cofactor / metalloprotein cases 尤其失败**: 默认 force field 不准 → top-1 RMSD 经常 > 4 Å

## ★ 方法选择决策链 (correct alternative)
**Correct path** (case dock-001 lesson):
1. 先在 receptor 上跑 redock_benchmark skill (5-10 已知 holo complex)
2. 计算 top-1 ≤ 2 Å rate
3. **rate ≥ 30% → production OK**; rate < 30% → block + 转 ensemble docking / IFD / AF3-as-docking
4. 必须用 **fresh-prepped ligand** (信息不泄漏) — 不能直接用 crystal coords

**Why this beats the anti-pattern**:
- 30% threshold 来自 PDBbind core set 测得 industry 平均 baseline
- per-target 验证比文献 success rate 可靠 ~10x
- 早期发现 "this receptor is hard for rigid docking" 比湿实验 hit rate < 1% 后才知道便宜得多

## ★ Validation metric (how Reviewer detects this anti-pattern)
- design_plan 缺 `sanity_checks_planned: redock_self_test_top1_le_2A_rate_min_0.30` → BLOCK
- execution_results 中无 `redock_self_test.performed=true` 且 docking_type ∈ {protein_ligand, protein_ligand_redocking, induced_fit_protein_ligand} → BLOCK
- redock self-test rate < 0.30 但 confidence_label ∉ {low, cold_start} → BLOCK (case dock-001)

## Lessons → anti-rule
- **anti-rule-01**: Production PL docking 必有 redock self-test ≥ 30% 阈值; 缺失 = 默认 reject
- Cross-case evidence: dock-001 (PDBbind), dock-008 (kinase IFD), real-run-1m17 (EGFR)
- Confidence: high (industry-wide consensus + cross-target verified)
