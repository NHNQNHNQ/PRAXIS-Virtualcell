# Finding W9 / M2.1 Step 1 — Ledger 审计:无泄漏特征/标签/诊断三分类(防坑1+坑2)

> M2-lite 第一步、防泄漏命门。操作化成 `praxis_virtualcell/governance/ledger_features.py`(编译期防泄漏 + perturbation-level split)。Mac TDD 3 passed,80 passed 零回归。

## 列三分类(audit_columns)

| 类 | 列 | 规则 |
|---|---|---|
| **INFERENCE_FEATURES**(推理期可得 → 可当特征) | `disagreement_score`, `disagreement_n_zero_pairs`, `disagreement_n_models`, `seen_in_train`(OOD flag,查表可得), `n_models_used` | 预测新扰动时就能算 |
| **LABELS**(真实准度,推理期不可得 → **严禁当 feature**) | `delta_pearson`(可靠性回归 target), `per_predictor_delta_pearson`(router label=argmax) | 训练时知道、预测时不知道(坑1) |
| **DIAGNOSTIC**(现行规则决策,作 baseline 对照,不当 feature) | `reliability`, `abstain`, `abstain_reasons`, `downgrade_reasons` | 避免与 learned 自指 |

- `extract_features()` **断言** feature∩label=∅,且每行只含 INFERENCE_FEATURES 键(编译期防泄漏)。
- `reliability_target()`=delta_pearson;`router_label()`=per_predictor argmax(label,非 feature)。
- `leave_perturbation_out_folds(k=5)`:每条 ledger=一个扰动,按条目分 fold = **perturbation-level split**(坑2,无 cell 泄漏),确定性可复现。

## 诚实/现状
- 当前可用推理特征**偏少**(主力是 `disagreement_score`,−0.716 强信号)。`seen_in_train` 是 OOD flag。
  预测 magnitude / 各 predictor uncertainty **尚未记进 ledger**(M2 plan 建议加),需后续 re-run 记录 → 扩特征。
- ledger 仅 **60 条 enriched**(坑3:只够 linear/logistic/ridge/RF,不上深度)。建议下步扩到 151。

## M2.1 下一步(拆小)
- [ ] **扩 ledger 60→151**(远端跑 activation 全 151 拿 disagreement;merge per-pert dp)→ 更多训练数据 + 记录 prediction magnitude/uncertainty 扩特征。
- [ ] **Step 2 Reliability baseline**:dp ~ disagreement(+OOD),pert-level CV,报 corr/R²/bad-case AUROC/risk-coverage;baseline 必含 disagreement-only / OOD-only / random / v0.2 规则。
- [ ] Step 3 Learned abstain;Step 4 Router(regret);Step 5 soft MoE。
