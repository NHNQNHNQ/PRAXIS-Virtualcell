# Finding W4b — Coordinator 复现(M1 Task 3)

> praxis 经 `coordinator_bridge` 复用 donor `Subagent`/`Coordinator`,在 Norman 实测多组合 ΔPearson。**复现 ~0.70 达成**。

## Coordinator 实测(远端 virtualcell GPU, Norman test, max_cells=200 / seed=1)
| 组合 | ΔPearson | n |
|---|---|---|
| latent+gnn | 0.6847 | 18874 |
| cpa+decoder+gnn | **0.7020** | 18874 |
| linear+latent+cpa+gnn+decoder (all-5) | **0.7039** | 18874 |

- **复现 ~0.70**:all-5 = 0.7039,cpa+decoder+gnn = 0.7020(均 > 0.70)。
- **ensemble 有效**:all-5 0.7039 > 单 base 最强 cpa 0.6716(+0.032)。
- latent+gnn 0.6847(< 0.70):因 latent 偏弱(0.6365);run_full_bench 注释的「latent+gnn」并非最优组合(早期数字误导,见 [[finding_w4b_multi_anchor]])。

## 真实 donor API(踩坑记录)
- 类名小写:`Subagent` / `SubagentSpec`(非 SubAgent)。
- `SubagentSpec(id, perturbation_kinds, bench_id)`;**一个 `Subagent` 持有多个 Predictor**(内部 ensemble):`Subagent(spec, [predictors])`;`Coordinator([subagent])`。
- `Coordinator` **非 nn.Module** → 不被 `EvalAgent.to(device)` 递归 → predictors 须显式 `.to(device)`(否则 cpu/cuda 不匹配)。

## test_ml_coordinator 2 passed
`test_coordinator_latent_gnn_runs`(跑通 > 0.6)+ `test_coordinator_strong_combo_reaches_070`(cpa+decoder+gnn > 0.70)。

## DoD M1 达成
M1(纯 ML 复现)完成:6 predictor 锚定复现 + 等价性 + **Coordinator ~0.70**。
