# Finding W9 / M1 — Eval Ledger 填每扰动准度 + disagreement↔准度验证(阶段2 训练数据就绪)

> 路线图 docs/ROADMAP-v0.3-cell-os.md 阶段1/M1 ①(给 ledger 填 per-predictor delta_pearson)。
> 远端算 151 扰动 × 3 真 donor predictor 的逐扰动 ΔPearson(`_group_mean` + `_safe_pearson`,donor 指标),
> 合进 activation ledger(60 扰动,含 disagreement)。`benchmarks/eval_ledger.py` 加 `per_predictor_delta_pearson` 字段。

## 两个关键结果

### 1. disagreement 真能预测准度 —— abstain 的 per-sample 验证
- **corr(disagreement_score, per-pert ΔPearson) = −0.716**(强负相关,n=60)。
- 分歧高半 平均 dp **0.571** vs 分歧低半 平均 dp **0.841**(n_hi=n_lo=30)——分歧大的扰动准度低 ~27 点。
- → v0.2 表 C 在**聚合**层证了 risk-coverage 正向;这里在**逐样本**层坐实:disagreement 不是噪声,**高分歧 ⇒ 低准度**,abstain/降级的依据真实。

### 2. best predictor 因扰动而异 —— MoE Router 有真实信号
- 全集 151 扰动最准 predictor:**gnn 75 / linear 39 / latent 37**(无单一处处最优)。
- 60 样本:gnn 28 / latent 20 / linear 12。
- → 阶段2 **MoE Router 动机坐实**:学"哪个 predictor 配哪个扰动"有真实增益空间(单选最优组合 > 任一固定单模型)。

### 3. Eval Ledger 阶段2 训练特征就绪
每扰动:`disagreement_score` + `per_predictor_delta_pearson{linear,latent,gnn}` + `delta_pearson`(均值代理)+
`seen_in_train`(OOD 标签)+ `reliability/abstain/downgrade`。**enriched 60/60**,落 `docs/findings/m1_ledger_sample.jsonl`。
→ 这正是阶段2 OOD Classifier / Abstain Head / MoE Router 的训练表。

## 诚实边界
- **per-pert ΔPearson 是 pert-level**(mean 聚合,~0.57–0.84),**高于 per-cell 全局 0.67**;用于扰动间相对比较/路由,
  **不是**论文招牌的 per-cell 数(delta_pearson_mean 0.706 是 60 扰动 3-predictor 均值的均值,非 per-cell 0.7039)。
- **disagreement 单 control(W4.5 失配)**、准度 proper pert-level;两者皆 per-pert 合并。−0.716 在单 control 分歧下已成立(鼓舞);
  per-cell disagreement 待 W4.5 解后更严格。
- `models_used` 名字 `Mock*` 仍是槽位、实现是真 donor predictor(命名遗留)。

## M1 进度
- [x] 接线分析 + Eval Ledger 结构(finding_w9_m1_eval_ledger)
- [x] disagreement/abstain 真模型自发激活(finding_w9_m1_activation)
- [x] **ledger 填每扰动准度 + disagreement↔准度验证(−0.716)+ router 信号(本 finding)**
- [ ] 外部 predictor(GEARS 适配同 split / scGen)进表 A(解 R8 强化,较重,可分叉;下轮评估)
- M1 核心已达成(治理骨架通电 + 阶段2 训练数据就绪);外部 baseline 强化为剩余项。
