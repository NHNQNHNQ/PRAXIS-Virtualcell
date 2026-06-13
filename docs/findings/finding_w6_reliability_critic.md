# Finding W6 — reliability/abstain/critic 强化(GPT §8, Workflow 对抗验证)

> Week 6:model disagreement(§8.3)+ CriticAgent 检查扩充(§8.4)+ abstain 条件(core_predictor_failed/cell_type)。**design workflow 对抗验证(consistent=false)抓出三机制纸面风险 + integration 冲突 + §8.5 越界 → 据 fixes 实现**。`test_week6` 11 PASS,Mac 70+23skip 零回归。

## GPT §8 验收
| § | 验收 | 实现 |
|---|---|---|
| 8.1 | 不支持物种→abstain | species_not_supported(W5) |
| 8.2 | 未知 gene→rejected | gene_not_in_graph_vocabulary(W5) + core_predictor_failed(新,声明式) |
| 8.3 | 模型冲突→降低可靠性 | EnsembleCoordinator 算 pairwise cosine disagreement → ReliabilityAgent abstain(rule 声明时)/降级(high→medium) |
| 8.4 | Critic 发现错误 provenance | CriticAgent 增 missing_provenance / missing_uncertainty / unsupported_species_in_ensemble / abstain_inconsistent_with_prediction |
| 8.5 | LLMReport 被 Critic 审 | LLMCritic(需 key);deterministic Critic 审 reliability payload 底料(**诚实:审不到 LLMReport.narrative**,语义审属 LLMCritic) |

## design verdict 抓出并修复(consistent=false)
1. **三机制纸面风险(严重)**:disagreement/core_failed/cell_type 在当前 mock e2e 流**永不触发**(三 mock 单 target 正常 delta → score 0.333<0.5;run_prediction 不抛异常;请求 cell_type=None)。→ 诚实标注(yaml/注释/finding)+ **手搓 payload 测试**证明机制非纸面、可激活;真实激活待未来真分歧/可失败 predictor。
2. **零向量伪信号**:MockLinear 恒零 → e2e 0.333 是伪分歧。→ disagreement dict 加 `n_zero_vector_pairs` 审计字段,使 0.333 来源可审、不被误读为真方向冲突。
3. **阈值硬编脆弱**:→ `disagreement_threshold` 提到 `default_abstain_rules.yaml`(缺省 0.5)可配,未来调参不改代码。
4. **integration 冲突**:设计1(disagreement)与设计3(core/cell_type)都改 reliability.py → **合并实现**(abstain 类优先;降级类在非 abstain 分支各降一档;model_disagreement/core_predictor_failed/critic_violations 三命名空间隔离)。
5. **§8.5 越界**:deterministic critic 跑在 Report 之前,读不到 LLMReport.narrative → 注释/finding 诚实标注 critic 审 payload 底料,LLM 语义审属 LLMCritic。
6. **abstain_reasons 语义**:cell_type 降级非 abstain 却进 abstain_reasons → reason 加 `downgrade:` 前缀区分。

## 诚实局限
- **1 维 delta**:mock delta 单 target 1 维,cosine 只能检符号翻转,幅度分歧([0.01] vs [100])测不出。真分歧检测待多维 delta(真 predictor 输出 n_genes 维)。
- `unsupported_species_in_ensemble` 是防御性不变量检查(正常路由不命中,抓汇总 bug 注入),非 §8.4 主力;§8.4 主力是 `missing_provenance`(实测可触发)。

## 留 backlog
真分歧 predictor 接入(让 disagreement e2e 生效);真可失败 core predictor 声明;LLMReport 端到端 critic;OOD/calibration(GPT §8 提及,本期未做)。
