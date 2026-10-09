# Finding W9 / M2 — 固定 ensemble 决定性对照:硬路由空间被压缩,M2 应转向 abstain/selective

> 路线图铁律"router 必须 vs ensemble 不只 vs 单模型"。远端算固定 ensemble(均 3 预测后 pert-level dp)。

## 结果(151 扰动,pert-level ΔPearson)

| 策略 | dp | 相对 |
|---|---|---|
| 最强单模型 gnn | 0.6702 | — |
| **固定 ensemble(均 3 预测)** | **0.693** | +0.023 vs 单模型 |
| oracle router(每扰动选最准,**上界**) | 0.7043 | **仅 +0.011 vs ensemble** |

## 关键结论(诚实,重塑 M2)
- **固定 ensemble 已吃掉大部分路由收益**:oracle 比 ensemble 只高 +0.011(比单模型 +0.034 的大头是 ensemble 拿走的)。
- learned router 只能拿到这 +0.011 的一个分数 → **基于准确度的硬 predictor 选择,在简单 ensemble 之上几乎没有空间**。
- **不值得**把 M2 主力压在"准确度路由"上。

## M2 方向修正(回归路线图核心论点)
路线图本就说卖点是**治理/可靠性**而非准确度。本对照实证了这点:
- **准确度维度**:ensemble 已近最优,router 边际收益 ~0。
- **可靠性维度**:M1 已证 disagreement↔准度 **corr −0.716**(强)——**知道"何时不该预测"的信号很强**,且现有系统(GEARS/CPA/scGPT/scGen/STATE)**完全没有**(v0.2 表 B)。
→ **M2 主力应是 Abstain / Selective-Prediction / OOD Head**(高价值、差异化),而非 accuracy-router。
  router 可保留为"在已决定预测时选 predictor / 加权",但其主职是**弃权**而非挤 +0.01 准度。

## 诚实边界
- oracle 是上界;ensemble 0.693、单模型 0.6702 是 pert-level(≠ per-cell 0.67/0.70)。
- ensemble 这里是简单均值(非 donor Coordinator 的加权);donor Coordinator per-cell 0.7039 是另一指标,不可比。

## 下一步(M2 修正后)
- [ ] 训 **Abstain/Selective Head**:用 ledger 特征(disagreement / 各 predictor uncertainty / seen-unseen)→ accept/abstain,
      目标 = 给定 coverage 下最大化保留集 dp(把 v0.2 后处理 risk-coverage 变**训练目标**);验证 learned selective > 固定阈值 abstain。
- [ ] OOD Classifier(seen/unseen + embedding 距离)。
- [ ] router 降级为"预测时的 predictor 加权"(非主力),或并入 selective head。
