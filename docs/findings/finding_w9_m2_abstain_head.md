# Finding W9 / M2.1 Step3 — Learned Abstain head:把 v0.2 表 C 升级为 learned 选择性预测(更强)

> `governance/abstain_head.py`(纯 Python)。用 reliability model OOF 预测做 risk-coverage,对照各排序信号。
> 151 ledger,pert-level CV,无泄漏(learned 用 OOF)。

## 结果(risk-coverage AUC,越大越好)

| 排序信号 | AUC |
|---|---|
| oracle(真 dp,上界) | 0.7822 |
| **learned(reliability OOF)** | **0.7460** |
| ood_only | 0.7297 |
| disagreement_only(v0.2 用的) | 0.7196 |
| random | 0.6595 |

保留集 dp @ coverage(1.0 / 0.8 / 0.6):
- oracle 0.657 / 0.772 / 0.842
- **learned 0.657 / 0.733 / 0.796**
- disagreement_only 0.657 / 0.713 / 0.749

## 意义
- **learned abstain AUC 0.746 > disagreement-only 0.720**(满足验收 learned > v0.2 规则),> ood-only/random。
- 捕获"规则→oracle"差距的约一半;coverage 0.6 时保留集 dp 0.796 vs 规则 0.749(+0.047)。
- → **v0.2 表 C 的"按 disagreement 弃权"被 learned reliability 弃权超越**:治理的弃权决策从规则升级为可学习、且更强。这是 M2 第二个自研模块兑现。

## 诚实边界
- **pert-level risk-coverage**(基于 ledger per-pert dp)**≠ v0.2 per-cell 表 C**,互补不替代;不可直接比绝对值。
- learned 仍只用 3 特征(disagreement/OOD/n_zero),特征增强(Step3.5)预计再升。
- 151 样本单一 5-fold(无 bootstrap CI);差距 0.746 vs 0.720 跨 fold OOF。
- disagreement 单 control(W4.5);pert-level dp ≠ per-cell 招牌数。

## M2 进度
- [x] M2.1 Step1 审计 / Step2 Reliability Model(AUROC 0.907)
- [x] **M2.1 Step3 Learned Abstain head(risk-coverage AUC 0.746 > 规则 0.720)**
- [ ] Step3.5 特征增强(magnitude/uncertainty)
- [ ] Step4 Router(regret) → Step5 soft MoE → Step6 整合回 runtime → M2.4 Delta-Adapter
