# Finding W9 / M2.1 Step6 — learned reliability/abstain 接回 runtime(治理从"可学习"到"运行时真的在用")

> 把 M2.1 的 learned Reliability/Abstain 从"分析结果"变成**系统能力**:接回 `ReliabilityAgent`,默认
> `learned_with_rule_fallback`,fail-closed 回退,全 provenance,无泄漏。**Mac 91 passed + 25 skipped 零回归。**

## 做了什么
- **冻结 artifact**(`governance/artifacts/`,`freeze_artifacts.py` 可复现):`reliability_model_v0_3.json`
  (features=disagreement/seen/n_zero,ridge weights:disagreement **−0.118**、seen +0.136、n_zero 0,带训练 ledger sha256
  `548c444f…` + n_train 151 + finding 引用)、`abstain_head_v0_3.json`(abstain<0.448 / downgrade<0.549,risk_cov_auc 0.746)、
  `feature_schema_v0_3.json`(model_features + labels_forbidden 防泄漏)。
- **runtime scorer** `governance/learned_reliability.py`:加载 artifact → 算 reliability_score/abstain_score/decision;
  artifact 缺失/schema 不匹配/异常 → `fallback=True`(caller 退回 rule);断言 runtime 特征不含 label。
- **ReliabilityAgent 集成**(`mode` 参数,默认 rule;workflow 注入 `cfg.reliability_mode`,默认 `learned_with_rule_fallback`):
  **硬规则(物种/空/全拒/core)恒 rule 权威**;learned 只接管 disagreement **软判定**(降级/软 abstain)。
- **report 透出** `learned_reliability`:reliability_mode/reliability_score/abstain_score/abstain_decision/features_used/model_version/feature_schema_version/fallback。

## 7 gates(全过,test_learned_reliability_integration 7 tests)
1. Mac tests 全过(91 passed)。2. learned mode 能运行。3. 无 artifact → fallback rule。4. schema 不匹配 → fallback。
5. label 进 runtime 特征 → 断言失败(无泄漏)。6. report 含 learned 决策(e2e 实测 mode=learned_with_rule_fallback、
score 0.717、ver reliability_v0.3.0)。7. 复现 risk-coverage AUC 0.746(用 ledger,不需 runtime 重训)。
+ 硬 abstain(全拒)即便 learned mode 也不被覆盖。

## 意义
- **PRAXIS 运行时默认就在用 learned 可靠性**(非旁路):每次预测的 report 带 learned 决策 + 完整 provenance + 可审计。
- 这是 PRAXIS 主线(离线可复现的**可审计治理 + abstain + provenance**)的兑现——从 v0.2 的"规则治理"推进到"运行时可学习治理"。
- 安全:fail-closed(artifact 缺失/schema 变 → 自动 rule),向后兼容(直接构造 `ReliabilityAgent()` 仍 rule),硬规则不被 learned 削弱。

## 诚实边界
- runtime `seen_in_train` 多为 None(训练集查表未接入)→ predict_dp 用训练均值填,`features_used` 如实记;
  disagreement 是主导特征(Step3.5),影响有限。
- 决策仍基于 pert-level 训练(≠ per-cell);disagreement 单 control(W4.5)。
- learned 阈值由训练预测分布定(abstain 15%/downgrade 35% 分位),非端到端调优;可后续按运营反馈调。

## M2 进度
- [x] M2.1 Step1 审计 / Step2 Reliability(0.907)/ Step3 Abstain(0.746)/ Step3.5 特征增强(负结果)/ **Step6 整合回 runtime**
- [ ] Step4 Router(**deferred**:固定 ensemble 0.693 近 oracle 0.7043,硬路由空间小;待接入更异构 predictor 再启)
- [ ] M2.4 Delta-Adapter(最后,谨慎)
