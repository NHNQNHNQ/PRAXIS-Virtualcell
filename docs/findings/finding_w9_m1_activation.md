# Finding W9 / M1 — disagreement/abstain 在真 predictor 上"通电"自发激活(解 v0.2 局限)

> 路线图 docs/ROADMAP-v0.3-cell-os.md 阶段1/M1 ②。**把 v0.2「声明式机制 mock 不激活」从未证升级为实证。**
> 复现:`conda activate virtualcell; python -m praxis_virtualcell.benchmarks.m1_activation`(远端)。

## 结果(远端实跑,60 Norman 真扰动)

| 指标 | 值 |
|---|---|
| 扰动数 | 60(test split) |
| disagreement.score 分布 | min 0.23 / median 0.375 / **max 0.504** / mean 0.359 |
| disagreement n_models | 3(真 donor base 全参与) |
| **越阈值(>0.5)→ abstain** | **1 个**(reliability_counts `{high:59, low:1}`) |
| triggered_rate | 1/60 |

**关键对比**:mock e2e 的 disagreement 是 1 维 delta + 零向量伪 0.5(永不触发,v0.2 局限);
真 donor predictor 输出 **2000 维真 delta** → disagreement 变**真值(0.23~0.504,连续分布)** →
1 个扰动越 0.5 → ReliabilityAgent **自发 abstain**(`model_disagreement_too_high`,非手搓、非纸面)。

→ **v0.2 局限「disagreement 在 mock 流永不触发」解除:在真 predictor 上,disagreement 是真值、abstain 运行时自发激活。**

证据:`docs/findings/m1_ledger_sample.jsonl`(60 条逐样本治理记录,EvalLedger 落盘)。

## 诚实边界(必读)

- **命名遗留**:ledger `models_used` 显示 `MockLinear/MockCPA/MockGEARS` 是 **name 槽位**,实现是**真 donor predictor**(`run_request_ml` slots: `MockLinear→linear_additive, MockCPA→latent_additive, MockGEARS→gnn_pert`)。名字是 mock、实现是真;后续应重命名槽位避免误读。
- **激活率低(1/60)不是缺陷**:3 个 donor base(linear/latent/gnn)本身较一致,阈值 0.5 少被越。**重点是机制是真的、disagreement 是真值、越线即自发触发**——不夸大触发频率。后续接入更异构的 predictor(CPA/scGen/GEARS/STATE)分歧会更大。
- **单 control(W4.5 失配)仍在**:每请求用 `ds[0].control` 单一基线 + 该扰动 pert_emb;disagreement 是"3 模型对该扰动方向是否一致"的真信号,但非 per-cell 全量。per-cell 解失配是 backlog。
- **未评测准确度**:本轮 ledger `delta_pearson=None`(只证激活,未算每扰动准度);下步可填以训练阶段2 模型。
- **"真 predictor 进表 A(R8)"**:cpa/gnn/linear/latent 等 donor base 已在 v0.2 表 A(witnessed);**外部** predictor(GEARS/scGen)同协议接入是 M1 后续子步(较重)。

## M1 进度

- [x] 接线分析 + Eval Ledger(finding_w9_m1_eval_ledger)
- [x] **disagreement/abstain 真模型自发激活实证**(本 finding)+ ledger 逐样本落盘
- [ ] 外部 predictor(GEARS/scGen)同协议进表 A(R8 强化)
- [ ] ledger 填 per-pert delta_pearson(为阶段2 router/OOD/abstain 备训练数据)
- [ ] M1 验收复盘:≥3 真 predictor + ledger + 真激活(已 3/4)+ risk-coverage 多真模型(v0.2 表 C 已在真 predictor 上做过,复用)
