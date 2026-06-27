# Finding W9 / M1 — 接线分析 + Eval Ledger(v0.3 Cell-OS 阶段1)

> 路线图见 docs/ROADMAP-v0.3-cell-os.md。M1 目标:把真 predictor 接成 agent + 建 Eval Ledger +
> 让 disagreement/abstain 在真模型上**自发激活**(解 v0.2 声明式 mock 不激活)+ 真模型进表 A。

## 1. 接线现状分析(读码确认,非臆测)

**disagreement / abstain 是完全接好、运行时条件触发的**(非纸面):
- `agents/ensemble.py::_disagreement`:对各 predictor 的 delta 向量算 mean pairwise (1-cos)/2 ∈[0,1];零向量对记中性 0.5 + 单列 `n_zero_vector_pairs`(防伪分歧)。
- `agents/reliability.py`:`score > threshold`(默认 0.5,brain `default_abstain_rules.disagreement_threshold`)→ 若 `model_disagreement_too_high ∈ abstain_rules` 则 **abstain**,否则**降一档**(report 留 `downgrade:` 理由)。

**v0.2「mock 不激活」的真实原因**(读码定位,可解):
1. mock e2e 是 **1 维 delta**(单 target)→ disagreement 只能检符号翻转,幅度分歧不可见(ensemble.py 注释明示)。
2. 部分 mock(如 MockLinear 恒零)→ 零向量伪分歧 0.5。
→ **真 donor predictor 输出 2000 维真 delta → disagreement 变真值 → 降级/abstain 自发触发。** 接线无需改,只需"通电"。

**ML 通讯 workflow 已存在**:`workflows/predict_delta_expression_ml.py::run_request_ml` 已注册 **3 个真 donor predictor**(linear/latent/gnn,借 Mock 槽位:`{MockLinear:linear_additive, MockCPA:latent_additive, MockGEARS:gnn_pert}`)走完整通讯流。

## 2. 本轮产出:PRAXIS Eval Ledger(M1 数据骨架)

`praxis_virtualcell/benchmarks/eval_ledger.py` —— 把每次 communicative run 的 report 抽成逐样本治理条目:
- predictor 参与(used/rejected/failed)、ensemble 分歧(score/triggered/n_models/n_zero_pairs)、
  reliability/abstain/abstain_reasons/downgrade_reasons、critic_violations、caution_flags;
- **可选**外部评测信号:`delta_pearson`(该样本预测准度,有 ground-truth 才填)、`seen_in_train`(OOD 标签,来自 manifest)。
- `record(report,...)` / `to_jsonl` / `from_jsonl` / `summary()`(abstain_rate / disagreement_mean / reliability_counts / delta_pearson_mean)。

**设计纪律**:只记 report 真实字段(report.py 结构),不编造;没评测就 `delta_pearson=None`(诚实)。纯 Python 无 torch,Mac 可建/测。
测试 `tests/test_eval_ledger.py`(2 passed,合成 正常/降级/abstain 三种 report)。**Mac 77 passed + 25 skipped 零回归。**

**用途**:这是阶段2 自研模型(MoE Router / OOD Classifier / Abstain Head)的训练数据来源——每个 predictor 在每个样本上的表现 + 分歧 + OOD + 误差。

## 3. M1 进度 / 下一步

- [x] 接线分析:disagreement/abstain 运行时条件触发已确认;真模型即可通电。
- [x] Eval Ledger 数据骨架 + Mac TDD。
- [ ] **远端 run_request_ml(真 predictor)→ 记进 Ledger**:跑一批 Norman 扰动,落盘逐样本 ledger,
      **证明 disagreement.score 真值化、降级/abstain 在真模型自发触发**(解 v0.2 声明式局限,非手搓)。
- [ ] 真 predictor(GEARS/CPA/scGen)同协议进表 A(解 R8);其中 GEARS/CPA donor 侧已有 ckpt,scGen 待接入。
- [ ] M1 验收:≥3 真 predictor 进表 A + ledger 逐样本 + abstain/disagreement 真激活 + risk-coverage 多真模型复现。

## 诚实边界
- 本轮仅建**结构 + Mac 测**;「disagreement 真激活」尚待远端真 predictor 跑出(下轮),**未声称已激活**。
- `run_request_ml` 现用 `agent_adapter` single-control(W4.5 失配,backlog),per-cell 全量待解;先验证激活,再解失配。
