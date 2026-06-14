# PRAXIS-VirtualCell v0.1.0 — Release Notes

**发布日期**:2026-06-13
**定位**:大脑引导的可通讯虚拟细胞智能体系统(brain-guided communicative agent OS for virtual cell prediction)。把虚拟细胞任务解析为结构化生物学请求,经物种脑检索模型适用性与负迁移规则,让异构预测模型以 predictor-agent 形式可审计通讯,在可靠性不足时主动 abstain,产出可追溯结果。**主预测闭环完全离线可复现**;API key 可用时 LLM agent 增强输入理解/路由审查/critic/报告,但不替代预测模型。

---

## 本版完成(GPT 计划 Week 1–7 / §4–§9)

| Week | 能力 | 关键结果 |
|---|---|---|
| **W1** | bootstrap | PRAXIS-2 派生, 去 13 学科脑 → 单 virtualcell 脑 |
| **W2** | communicative agent runtime | VirtualCellRequest / AgentMessage / MessageBus / AgentRuntime / retrieve-before-predict 门 / mock workflow(35 tests) |
| **W3** | LLM-assisted(可选) | 纯 DeepSeek httpx, 4 LLM agent(Input/Router/Critic/Report)+ fallback, 无 key 自动降级(48 tests) |
| **W4a/b** | donor ML predictor 迁移 | 远端 `virtualcell` env(torch 2.6, A100);6 predictor donor_bridge 锚定复现 + 等价性(atol 1e-6);**Coordinator 复现 Norman ΔPearson ~0.70**(all-5 0.7039);真 predictor 接 communicative 骨架 + 端到端 trace/provenance/abstain |
| **W4c** | 外部模型(GEARS/scGPT) | 破两个 env 死结(scGPT torchtext ABI / GEARS PyG);scGPT 训 head ΔPearson 0.4407(frozen 局限诚实记);GEARS 原生 norman pearson_de 0.8392(6 轮老包坑破解, 与 base 不可比) |
| **W5** | cross-species brain | human/mouse/bacteria/yeast brain + 路由扩展;§7 五条满足(ortholog caution 真投影 / negative-transfer 命中 / martian 无假证据) |
| **W6** | reliability/abstain/critic 强化 | model disagreement(pairwise cosine)/ core_predictor_failed / cell_type 降级 / Critic 增 4 检查 / report 拆 abstain_reasons vs downgrade_reasons;§8 验收 |
| **W7** | benchmark + ablation | A(ML-only)↔D(Full)两极:OOD_rejection 0→1.0 / wrong_model_use 1.0→0 / provenance 0→1.0 / abstain 0→1.0 / trace 0→1.0(§9.3 Full 明显优于 ML-only) |

## 关键数字
- **Norman ΔPearson**:donor Coordinator 复现 **0.7039**(all-5);单 base cpa 0.6716 最强。
- **测试**:Mac 71 passed + 23 skipped(ml 测试标 `remote`, Mac 无 torch 自动 skip;远端全 ml pass)。
- **ablation A↔D**:5 个可靠性/系统指标全两极(Mac offline 确定性, 全复现)。
- **provenance/trace**:Full 系统 8/8 stage trace + 6/6 provenance schema 字段。

## 工程方法:Ultracode 双 Workflow 对抗验证
W5–W7 每个特性都经**两层对抗验证**(design workflow + implement review),抓出纸面 review 抓不到的真实缺陷:
- W5:caution 不可见 / negative_transfer 死代码 / martian 假证据 / drug 拒因把药名当基因 / ortholog 投影零执行。
- W6:disagreement/core_failed/cell_type 三机制在 mock e2e **永不触发**(纸面风险)→ 诚实标注 + 手搓测试证明可激活。
- W7:挡掉方法论站不住的 4 档 ablation(B 纸面 / C≈D / 性能同义反复 / abstain_gain 违反 manifest 制度)→ 收敛到最小可发表 A↔D 两极。

## 诚实边界(不 over-claim)
- **性能维度 communicative 层不参与张量计算**:D 的 Pearson 由共享 predictor 经 EvalAgent 给出;ablation 性能 claim 仅"不损害", 非"更准"。
- **声明式机制 mock 不激活**:disagreement/core_failed/cell_type/真 ortholog 投影在当前 mock e2e 不触发(已 yaml/注释/finding 标注), 手搓测试证明可激活, 真实激活待真 predictor。
- **外部模型局限**:scGPT frozen backbone 0.44 < base(foundation 非银弹);GEARS 与 base 不可比(指标/split 不同)。
- **未做**:B/C ablation 档、OOD-pert split manifest + abstain_gain 数值、per-cell communicative Pearson、OOD/calibration、真 cross-species ML predictor。

## 下一步(Week 8 / §10–§11)
v0.1 finalize:CLI(`praxis-vc run`)、README、examples、package 安装;论文主线(§11 四问:理解输入 / 真多智能体 / 保持性能 / 提高可靠性)。详见 `docs/HANDOFF-v0.1-next.md`。
