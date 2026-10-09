# Finding W9 / M2 — 路由 oracle 上界(MoE Router 增益空间量化)

> 阶段2 起点:训练 router 前先量化"值不值"。用 M1 ledger 的 151 扰动 × 3 predictor pert-level ΔPearson
> (`docs/findings/m1_per_pert_dp.json`)算 oracle 上界。纯 Mac、用现有数据。

## 结果(151 扰动,pert-level ΔPearson)

| 策略 | 平均 pert-level ΔPearson |
|---|---|
| 固定 linear | 0.6639 |
| 固定 latent | 0.6360 |
| 固定 gnn(最强单模型) | 0.6702 |
| **oracle router(每扰动选最准)** | **0.7043** |

- **oracle 增益上界(vs 最强固定单模型 gnn)= +0.0341**。
- oracle 选择分布:gnn 75 / linear 39 / latent 37(无单一处处最优 → router 有学的东西)。

## 诚实边界(防 over-claim)
- **oracle = 上界**:假设每扰动都选到最准的 predictor;learned router 会**低于**此(真实增益是上界的一个分数)。
- **决定性对照缺失**:router 真正要打败的不只是最强单模型,而是**固定 ensemble**(均预测后算 dp)。本 finding 未算 ensemble 的 pert-level dp,**下一小单元补**——若 ensemble 已接近 oracle,则 router 增益空间被压缩,须诚实呈现。
- **pert-level ≠ per-cell**:0.66~0.70 是 pert-level(mean 聚合);oracle 0.7043 与 v0.2 Coordinator per-cell 0.7039 数值接近是**巧合、不可比**。
- 数据来自 M1 ledger(单 control disagreement,W4.5),per-predictor dp 是 proper pert-level。

## 下一步(M2,拆小)
- [ ] **固定 ensemble pert-level dp**(远端,均 3 预测后算 dp)→ 完成 router-vs-ensemble 决定性对照。
- [ ] 扩 ledger 训练数据(全 151 含 disagreement;现 60)。
- [ ] 训练第一个 learned router(简单模型:扰动特征 → predictor 选择/权重),验证 learned > 固定单模型 +(关键)≥ 固定 ensemble。
- [ ] 之后 OOD Classifier / Abstain Head / Delta Adapter。
