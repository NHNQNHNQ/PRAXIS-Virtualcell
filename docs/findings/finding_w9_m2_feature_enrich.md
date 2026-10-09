# Finding W9 / M2.1 Step3.5 — 特征增强(诚实负结果:幅度/不确定性不升,disagreement 主导)

> 远端对 151 扰动算每 predictor 预测 delta 范数(magnitude)+ uncertainty(std)→ 推理期特征(无泄漏)。
> 数据 `docs/findings/m1_pred_features.json`。Mac pert-level 5-fold CV 对照 base vs base+新特征。

## 结果(151 OOF,pert-level CV)

| 特征集 | reg_corr | bad-pert AUROC | risk-cov AUC |
|---|---|---|---|
| **base(3:disagreement+OOD+n_zero)** | **0.701** | **0.907** | **0.7460** |
| base + 6 原始(norm/std ×3) | 0.686 | 0.891 | 0.7378 |
| base + 2 派生(norm_spread + mean_std) | 0.699 | 0.905 | 0.7450 |

## 结论(诚实负结果)
- **加预测幅度/不确定性特征不改善**:原始 6 个**反降**(151 样本上添噪声/轻过拟合);派生 2 个**持平**。
- → **disagreement(cosine 集成分歧)已是主导可靠性信号**;raw prediction magnitude/std 不带来正交增益。
- **决定:不并入模块**。reliability_model / abstain_head 保持精简 base 3 特征(验证过的选择,适配小样本)。

## 价值
- 证实"加特征≠必升"——按计划据实报负结果,**防止过度工程**。
- 强化论点:PRAXIS 可靠性的核心信号是**模型间分歧**(cosine),不是单模型预测幅度;这与 −0.716(M1)一致。
- 未来若 ledger 扩大(>151)或接入更异构 predictor(STATE/GEARS),可重测这些特征——现在的结论限于当前数据规模。

## M2 进度
- [x] Step1 审计 / Step2 Reliability(0.907)/ Step3 Abstain(0.746)
- [x] **Step3.5 特征增强(负结果:保持 base 3 特征)**
- [ ] Step4 Router(regret;诚实预判硬路由空间小)→ Step5 soft MoE → Step6 整合回 runtime → M2.4 Delta-Adapter
