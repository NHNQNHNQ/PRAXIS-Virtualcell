# finding G2 — per-cell 解 W4.5 单 control(disagreement 升级 per-cell 全量)

> 目标:把 M1/M2 的 disagreement 从**单一 control**(`ds[0].control`)升级为 **per-cell 全量**(每 cell 用自身 control),重算下游治理指标,看单 control 是否乐观。证据类型:`[远端实跑]`(远端算 per-cell disagreement)+ `[Mac确定性]`(Mac 复算下游)。runbook:`docs/G2-percell-w45-remote-runbook.md`。

## 1. 做了什么

- **远端**(`zkyd`,virtualcell,`g2_percell.py`):载 3 donor base(linear/latent/gnn),对 donor test 151 扰动的**全部 18874 cells**,逐 cell 用**自身 control** 预测 3 模型 delta → per-cell disagreement(mean pairwise (1−cos)/2,同 EnsembleCoordinator 定义)→ 按扰动聚合(per-cell 均值)。批量 control + torch 向量化,21s 全量。
- **关键前提坐实**:per-cell control **确实改变 delta**(单 control vs per-cell max|Δ| = linear 0.76 / latent 3.17 / gnn 1.48)→ W4.5 有实质影响,非纸面。
- **Mac 复算**(`reliability_model.evaluate` + `abstain_head.evaluate_abstain`,同产出 0.907/0.746 的函数):把 ledger 的 `disagreement_score` 换成 per-cell 值,重跑对照。

## 2. 结果:单 control vs per-cell(同 151 ledger)

| 指标 | 单 control(W4.5 旧) | **per-cell(解 W4.5)** |
|---|---|---|
| learned AUROC(bad-pert) | 0.907 | **0.869** |
| risk-coverage AUC(learned) | 0.746 | **0.736** |
| reg corr(pred dp, 真 dp) | 0.701 | 0.646 |
| corr(disagreement, per-pert dp) | −0.511 | −0.473 |
| disagreement-only AUROC | 0.774 | 0.748 |
| ood_only AUROC(对照,不含 disagreement) | 0.788 | 0.788(不变✓) |
| risk-cov AUC(oracle 上界) | 0.782 | 0.782(不变✓) |

## 3. 结论(诚实,与旧假设相反)

- **per-cell 让治理指标略降,非升**:此前文档假设"解 W4.5 后下游可能整体升"——**实测相反**,单 control 基线**略乐观**(learned AUROC 0.907→0.869、risk-cov 0.746→0.736)。
- **但治理结论稳健**:per-cell 下 learned 仍 **>> disagreement-only(0.869 vs 0.748)>> random**,learned 仍最佳信号;ordering、显著性、"learned 提取的可靠性信号真实"的核心论断不变。
- **对照项不变验证正确性**:ood_only(0.788)、oracle risk-cov(0.782)不含 disagreement,per-cell 下完全不变 → 复算管线正确,变化只来自 disagreement 基线升级。
- **W4.5 局限解除**:disagreement 现基于 per-cell 全量控制;论文应报 **per-cell 数(0.869/0.736)为主**,并注明比单 control 略低是更严格基线的真实代价。

## 4. 诚实边界

- per-cell 只升级 **disagreement 的 control 基线粒度**;仍 pert-level 聚合(per-cell disagreement 均值→扰动级),**不等于** per-cell 招牌准确性(ΔPearson)。
- dp(可靠性回归目标)沿用现 ledger 的 per-pert 值,未改;只替换 disagreement 特征。
- artifact:`docs/findings/m2_percell_disagreement.json`(每扰动 per-cell disagreement mean/sd/n)+ `m1_ledger_151_percell.jsonl`(disagreement 替换版)。远端脚本 `g2_percell.py`(未 vendor,复用 donor)。
