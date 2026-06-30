# Finding W9 / M2.1 投稿前补强 L1 — perturbation-level bootstrap CI(给核心数字加 95% 区间)

> `governance/bootstrap_ci.py`(纯 Python,Mac 原生)+ `tests/test_bootstrap_ci.py`(4 passed)。
> 数据 `docs/findings/m2_bootstrap_ci.json`(B=2000, seed=0, 全量结果)。Mac **97 passed + 25 skipped** 零回归。
> 回应数据盘点 §9「151 小样本无 bootstrap CI」(高严重度缺口)→ 现已补。

## 方法(诚实口径)

对 151 ledger 做**扰动级有放回 bootstrap**(每次重采样 151 个扰动、重算指标),取 percentile 95% CI(2.5%/97.5%)。
- **固定 OOF 预测**(R2/R3 泛化口径,`reliability_model.cv_reliability`)+ **固定 frozen 决策**(R7 in-sample,`learned_reliability.score`);
- bootstrap 只重采样**指标**,**不重做 CV 训练** —— 因为重采样会让同一扰动既进 train 又进 test(泄漏),故刻意固定预测、只评估**指标在扰动采样下的稳定性**;
- 因此 CI **不含模型重训不确定性**;R7 行的 CI 仍是 **in-sample** 回放的 CI。pert-level ≠ per-cell。
- B=2000、seed=0、确定性可复现;point estimate 在原始 151 上算,**复现已落地 finding 数字**(实现自检)。

## 结果(n=151, B=2000, 全 2000 次有效)

| 指标 | point | 95% CI | 证据类型 |
|---|---|---|---|
| **泛化(OOF)** | | | |
| reliability bad-pert AUROC(learned) | 0.9068 | [0.8458, 0.9517] | OOF |
| reliability bad-pert AUROC(disagreement-only) | 0.7743 | [0.6863, 0.8677] | OOF |
| **AUROC 差(learned − disagreement)** | **0.1325** | **[0.0564, 0.1909]** | OOF · **CI 不跨 0** |
| risk-coverage AUC(learned) | 0.7460 | [0.7009, 0.7847] | OOF |
| risk-coverage AUC(disagreement-only) | 0.7196 | [0.6730, 0.7611] | OOF |
| **risk-cov AUC 差(learned − disagreement)** | **0.0264** | **[0.0138, 0.0406]** | OOF · **CI 不跨 0** |
| **in-sample 回放(R7)** | | | |
| wrong-accept(rule_only) | 0.9737 | [0.8947, 1.0000] | in-sample |
| wrong-accept(learned) | 0.2105 | [0.0789, 0.3421] | in-sample |
| **wrong-accept 降幅(rule − learned)** | **0.7632** | **[0.5897, 0.9211]** | in-sample · **CI 不跨 0** |
| risk-coverage(rule_only) | 0.0263 | [0.0000, 0.1053] | in-sample |
| risk-coverage(learned) | 0.7895 | [0.6579, 0.9211] | in-sample |
| **risk-coverage 增益(learned − rule)** | **0.7632** | **[0.5897, 0.9211]** | in-sample · **CI 不跨 0** |
| retained-utility(learned) | 0.8053 | [0.7232, 0.8938] | in-sample |
| unnecessary-abstain(learned) | 0.1947 | [0.1062, 0.2768] | in-sample |

## 关键结论

- **point estimate 全部复现**(0.9068≈0.907、0.7743≈0.774、0.7460=0.746、0.7196=0.720、0.9737≈0.974、0.2105≈0.211、0.0263≈0.026、0.7895≈0.789)→ bootstrap 实现正确。
- **learned 的优势在小样本下统计稳健**:四个关键**配对差值** CI **均不跨 0** ——
  - learned 相对 disagreement-only:bad-pert AUROC **+0.13 [0.056, 0.191]**、risk-cov AUC **+0.026 [0.014, 0.041]**;
  - learned 相对 rule_only(in-sample):wrong-accept 降 **0.76 [0.59, 0.92]**、risk-coverage 增 **0.76 [0.59, 0.92]**。
- **单点 CI 偏宽**(如 AUROC [0.846, 0.952],跨度 ~0.11),这是 151 小样本的真实代价;但**配对差值** CI 窄且显著(paired bootstrap 抵消了共同采样波动)——论文应据此强调**相对优势的显著性**,而非单点绝对值。

## 诚实边界

- **配对差值显著 ≠ 单点精确**:单 AUC/AUROC 的 CI 宽,只能说"learned 稳定优于 baseline",不能说绝对值精确到小数点后两位。
- **R7 行 CI 仍是 in-sample**:wrong-accept/risk-coverage 的 CI 是冻结模型在其自身训练 ledger 上回放的采样波动,**不是**独立泛化区间;泛化区间看 OOF 行(AUROC/risk-cov AUC)。
- **不含 CV 重训不确定性**:固定 OOF 预测做 bootstrap;完整 nested-bootstrap(每次重做 leave-pert CV)会更彻底但在 151 上易引入重复扰动泄漏,故未采用。
- pert-level dp(≠ per-cell);disagreement 单 control(W4.5);单一 5-fold(本 finding 未加多 seed 重复 CV,B3 项)。

## 论文怎么用(A1 完成)

learned-governance.md / 中文版 / data-inventory 的 Limitations 从「151 无 CI」改为:

> *Under perturbation-level bootstrap resampling (B=2000), the learned governance advantage was statistically stable: the paired learned − disagreement-only gaps did not cross zero (bad-perturbation AUROC +0.13, 95% CI [0.056, 0.191]; abstention risk–coverage AUC +0.026, 95% CI [0.014, 0.041]). Single-point AUCs carried wide intervals at this ledger size (e.g. AUROC 0.907, 95% CI [0.846, 0.952]), so we emphasize the paired advantage rather than absolute point values.*

## 补充 — 多 seed 重复 5-fold CV(B3,回应「单一确定性 5-fold」)

打乱扰动顺序(仍 leave-perturbation-out,无泄漏)跑 5 个 seed。`governance/repeated_cv.py` + `tests/test_repeated_cv.py`(4 passed)+ `docs/findings/m2_repeated_cv.json`。

| 指标 | mean ± sd | [min, max] |
|---|---|---|
| learned bad-pert AUROC | 0.9003 ± 0.0081 | [0.8852, 0.9068] |
| disagreement-only AUROC | 0.7743 ± 0.0000 | 恒定(固定特征,不经 CV) |
| learned risk-coverage AUC | 0.7438 ± 0.0014 | [0.7414, 0.7450] |
| disagreement-only risk-cov AUC | 0.7196 ± 0.0000 | 恒定 |

- **learned 优势对 fold 划分稳健**:5 个随机 seed 下 learned AUROC 全 > disagreement(0.885–0.907 vs 0.774)、learned risk-cov AUC 全 > disagreement(0.741–0.745 vs 0.720),方向 100% 稳定、sd 极小。
- disagreement 跨 seed 恒定(固定特征排序,不依赖 fold);只有 learned(经 CV 训练)随 fold 微动 → learned 的优势不是侥幸 fold。

## 进度

- [x] **L1 bootstrap CI**(本 finding)— 四个关键差值 CI 不跨 0,缺口「151 无 CI」已补。
- [x] **B3 多 seed 重复 CV**(本 finding 补充)— 5 seed learned 优势方向 100% 稳定。
- [ ] L2 OOD enrichment / OOD-only risk-coverage(纯 Mac,下一步)
- [ ] L3 整合进 learned-governance.md(把 CI 句写进 Results/Limitations)
- [ ] B1 GEARS same split(主刊增强)· B2 per-cell 解 W4.5 · B3 多 seed 重复 CV
