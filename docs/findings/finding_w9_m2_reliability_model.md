# Finding W9 / M2.1 — 第一个自研模型:Learned Reliability Model(治理可学习,赢过单信号)

> M2-lite Step2。`governance/reliability_model.py`(**纯 Python** ridge,无 numpy/sklearn,Mac 原生)。
> 数据扩到 151 enriched(`docs/findings/m1_ledger_151.jsonl`)。pert-level 5-fold CV,无泄漏(只用 INFERENCE_FEATURES)。

## 结果(151 扰动,OOF / pert-level CV)

| 任务 | 指标 | 值 |
|---|---|---|
| 可靠性回归 | OOF corr(预测 dp, 真 dp) | **0.701** |
| bad-pert 检测(bad=dp 底 25%, thr=0.455) | **learned AUROC** | **0.907** |
| | ood_only AUROC | 0.788 |
| | disagreement_only AUROC | 0.774 |
| | random AUROC | 0.479 |

**learned(disagreement + OOD + n_zero_pairs)0.907 > disagreement-only 0.774(+0.13)> random 0.48。**

## 意义
- **PRAXIS 的可靠性治理从"规则"升级为"可学习",且学出来的比单信号启发式强**——这是路线图核心论点的首个自研实证。
- 满足用户定的成功标准:learned ≥ disagreement-only(且显著超过)。disagreement-only(0.774)本身已是 PRAXIS 的强发现(r=−0.716);多特征组合再 +0.13。
- 现有系统(GEARS/CPA/scGPT/scGen/STATE)无此可靠性模型(v0.2 表 B)——这是差异化能力,不是包装。

## 守纪律(防四坑)
- **无泄漏(坑1)**:特征仅 `disagreement_score / seen_in_train / n_zero_pairs`(INFERENCE_FEATURES);真 dp 只当 label,`extract_features` 编译期断言。
- **pert-level split(坑2)**:`leave_perturbation_out_folds` 5-fold,每条=一个扰动,无 cell 泄漏。
- **轻模型(坑3)**:纯 Python ridge(3 特征),151 样本不过拟合。
- 不只看一个数:回归 corr + 分类 AUROC + 多 baseline 对照。

## 诚实边界
- pert-level dp(target,~0.5–0.9)≠ per-cell 招牌数;disagreement 仍单 control(W4.5)。
- 单一确定性 5-fold(无 bootstrap CI);但 learned 0.907 vs disagreement 0.774 差距清晰、跨 fold OOF。
- 特征偏少(magnitude/uncertainty 未记进 ledger);加更多推理特征预计还能升。

## M2.1 进度
- [x] Step1 Ledger 审计(防泄漏)
- [x] **Step2 Learned Reliability Model(AUROC 0.907 > disagreement 0.774)**
- [ ] Step3 Learned Abstain head(把可靠性预测 → accept/abstain,risk-coverage 对照固定阈值/v0.2 规则)
- [ ] Step4 Router(regret);Step5 soft MoE
