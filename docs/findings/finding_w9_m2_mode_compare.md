# Finding W9 / M2.1 Step6 — rule_only vs learned_with_rule_fallback 运行时对照(论文硬证据)

> `governance/mode_compare.py`。用 151 ledger 复算(真 disagreement + 真 dp),证明默认 learned 模式**真的改变软风险决策**、
> **不破坏硬规则**、**provenance 完整**。bad = dp 底 25%(thr 0.455);38 bad / 113 good。

## 对照表(n=151)

| Mode | wrong_accept ↓ | unnecessary_abstain ↓ | risk_coverage ↑ | retained_utility ↑ | n_flagged | hard_rule_override | provenance |
|---|---|---|---|---|---|---|---|
| rule_only | **0.974** | 0.018 | **0.026** | 0.982 | 3 | 0 | — |
| **learned_with_rule_fallback** | **0.211** | 0.195 | **0.789** | 0.805 | 52 | **0** | **complete** |

## 结论
- **rule_only 几乎挡不住软风险**:disagreement>0.5 才动,ledger 多 <0.5 → 只 flag 3 个 → **97.4% 的 bad 扰动被接受**(risk_coverage 仅 0.026)。
- **learned 大幅改善**:wrong_accept **0.974→0.211**(抓住 79% 的 bad)、risk_coverage **0.026→0.789**,代价是 unnecessary_abstain 0.018→0.195、retained_utility 0.982→0.805——合理的风险/可用性折中。
- **hard_rule_override = 0**:learned 只接管软判定,物种/空/全拒/core 硬规则不被覆盖(另有单测 test_hard_abstain_not_overridden_by_learned)。
- **provenance complete**:learned 模式每条决策带 score/decision/features_used/model_version/feature_schema_version/artifact_sha256/fallback。

→ **默认 learned_with_rule_fallback 不是形式集成,而是真的把"被规则放过的软风险"抓了回来,同时保住硬规则权威与可审计性。** 这是论文 Result"learned governance improves soft reliability decisions while preserving hard-rule authority and auditability"的硬证据。

## 诚实边界
- ledger 复算(pert-level dp ≠ per-cell;disagreement 单 control,W4.5),非新远端 runtime 跑;rule_only 差是因 0.5 阈值保守、ledger 分歧多 <0.5,learned 从同一信号里提取更多。
- ledger 全 human/in-vocab → 无硬规则触发样本,hard_rule_override=0 by construction;硬规则保全由单测独立证明。
- 阈值(abstain 15%/downgrade 35% 分位)非端到端调优,unnecessary_abstain 可随阈值调。

## M2.1 Step6 收口
- [x] 整合回 runtime(默认 learned_with_rule_fallback)+ artifact_sha256 + content_sha256 tamper-fallback
- [x] **rule vs learned 运行时对照(本 finding)**
- → 下一步:写 v0.3 论文新 Result(用 PRAXIS 自己口径,不碰 E9)。
