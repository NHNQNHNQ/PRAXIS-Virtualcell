# Finding W9 / M2.1 投稿前补强 L2 — OOD enrichment / OOD-only risk-coverage

> `governance/ood_enrichment.py`(纯 Python)+ `tests/test_ood_enrichment.py`(4 passed)。
> 数据 `docs/findings/m2_ood_enrichment.json`。Mac 全套零回归。
> 回应 data-inventory §9 缺口 + 旧局限「abstained 是否富集 OOD 未验证 / 仅 OOD 子集 risk-coverage 未做」。

## 方法

- OOD 标签来自 ledger `seen_in_train`(推理期 OOD flag,**特征非 label**):82 未见 / 69 已见,与 v0.2 表 C split 一致。
- learned/rule 软风险 flag 复用 `bootstrap_ci._prepare`(固定 OOF 预测 + frozen 决策);子集 risk-coverage 用 `abstain_head`。
- odds ratio 用 Haldane–Anscombe(+0.5)校正。

## 结果(n=151)

| 指标 | 值 |
|---|---|
| base rate OOD(未见/全部) | 82/151 = **0.5430** |
| 平均 dp:OOD vs seen | **0.5136 vs 0.8266**(OOD ≈ 低准度) |
| learned 软弃权/降级数(n_flagged) | 52 |
| **learned-flagged 中 OOD 占比** | **0.9808**(51/52) |
| learned-retained 中 OOD 占比 | 0.3131(31/99) |
| rule-flagged 中 OOD 占比 | 0.0000(rule 只 flag 3 个,均 seen) |
| **OOD enrichment odds ratio(learned)** | **74.66** |
| 2×2 列联表(flagged/retained × OOD/seen) | flagged_ood 51 / flagged_seen 1 / retained_ood 31 / retained_seen 68 |
| **OOD-only 子集 risk-coverage AUC(learned)** | **0.5769** |
| **seen-only 子集 risk-coverage AUC(learned)** | **0.8612** |
| reliability bad-pert AUROC:learned vs ood-only | **0.9068 vs 0.7877** |

## 关键结论

1. **learned abstain 强烈偏好弃权 OOD 扰动**:52 个被 flag 的里 51 个(98%)是未见扰动,odds ratio **74.7**(远高于 base rate 0.543)。learned governance preferentially captures unseen / out-of-distribution perturbation regimes。
2. **但 learned 超越 OOD 标签本身**(不是 OOD flag 的简单代理):
   - bad-pert 检测 learned AUROC **0.907 > ood-only 0.788**;
   - **OOD-only 子集**(OOD 标签在此为常数、无区分力)内 learned risk-coverage AUC **0.577 > 0.5** —— 靠 disagreement 仍能在纯 OOD 扰动里按可靠性排序、选择性弃权;
   - **seen-only 子集** AUC **0.861** —— 已见扰动并非都可靠,learned 在其内部也能区分。
   - → learned abstain captures low-accuracy perturbations **beyond OOD status alone**。

## 诚实边界

- learned 富集 OOD **部分由模型显式含 `seen_in_train` 特征**驱动(标准化权重 +0.136);但 OOD-only / seen-only 子集 risk-coverage(在 OOD 标签恒定的子集内仍有选择性)证明价值不止于 OOD 标签。
- **runtime `seen_in_train` 多为 None**(训练集查表未接入运行时);本分析在 **ledger** 上 flag 齐全(82/69),enrichment 结论限于"OOD 标签可得"的离线评估场景。
- pert-level(≠ per-cell);单 control(W4.5);151 单一 5-fold。
- rule-flagged OOD 占比 0 是因 rule 用 disagreement>0.5(与 seen/unseen 无关),恰好那 3 个高分歧扰动为 seen —— 据实记,非结构性结论。

## 论文怎么用(L3 整合)

learned-governance.md / -zh / data-inventory 在 R3(弃权)后加一段:

> *Learned abstention preferentially flags unseen/OOD perturbations (98% of flagged are OOD; enrichment odds ratio 74.7), consistent with OOD perturbations being lower-accuracy (mean Δ-Pearson 0.51 vs 0.83). Crucially it is not a mere OOD-label proxy: within the OOD-only subset — where the OOD label is constant — learned reliability still ranks perturbations for selective abstention (risk–coverage AUC 0.577 > 0.5), and the learned detector exceeds the OOD-only heuristic (AUROC 0.907 vs 0.788).*

## 进度

- [x] **L2 OOD enrichment**(本 finding)— 强富集(OR 74.7)+ 超越 OOD 标签(OOD-only 子集 risk-cov 0.577,AUROC 0.907>0.788)。
- [ ] B3 多 seed 重复 CV(纯 Mac,下一步)
- [ ] L3 整合 CI + OOD 进 v0.3 文档
- [ ] 🛑 L4 GEARS same split(远端) · 🛑 B2 per-cell 解 W4.5(远端)
