# PRAXIS-VirtualCell — 项目全景总结(供独立判断)

> 生成日期:2026-06-27 · git HEAD:`84211de`(已 push `origin/main`)· 测试:Mac 75 passed + 25 skipped
> 本文按「**真实见证 / 复现 donor / 声明式未激活 / off-axis 不可比 / 完全未做**」分层呈现,刻意不替读者下结论。

---

## 1. 一句话定位

PRAXIS-VirtualCell 把"可信虚拟细胞扰动预测"重述为**控制流 / 治理问题**:不追求"预测更准",而是在不损害预测的前提下,给异构预测模型套一层 **OOD 拒绝 / 弃权(abstain)/ 适用性检查 / 溯源(provenance)/ 可审计消息通讯**。这些治理能力是现有预测模型(GEARS / CPA / scGPT / scGen / STATE)普遍不具备的。

- 方向:**iii-lite**——LLM 可选增强(输入理解 / 路由审查 / critic / 报告),**绝不进预测核心**;预测主闭环完全离线可复现。
- 派生自 PRAXIS-2(去掉 13 学科脑 → 单一 virtualcell 脑)。

---

## 2. 完成时间线(Week 1–8)

| Week | 能力 | 关键产出 |
|---|---|---|
| W1 | bootstrap | PRAXIS-2 派生,单 virtualcell 脑 |
| W2 | communicative runtime | `VirtualCellRequest` / `AgentMessage` / `MessageBus` / `AgentRuntime` / retrieve-before-predict 门 / mock workflow |
| W3 | LLM-assisted(可选) | DeepSeek httpx,4 LLM agent,无 key 自动降级 |
| W4a/b | donor ML 迁移 | 6 predictor 锚定复现 + 等价性(atol 1e-6);**Coordinator 复现 0.7039**;真 predictor 接 communicative 骨架 |
| W4c | 外部模型 | GEARS 原生 pearson_de 0.8392;scGPT frozen head 0.4407(破 torchtext/PyG 两个 env 死结) |
| W5 | cross-species brain | human/mouse/bacteria/yeast 脑 + 路由(ortholog caution 真投影 / negative-transfer 命中) |
| W6 | reliability/abstain/critic | model disagreement / core-failed / cell-type 降级 / Critic 7 检查 / report 拆 abstain vs downgrade |
| W7 | ablation | A(ML-only)↔ D(Full)两极 × 5 指标 0→1 |
| **W8**(本会话) | **系统全面对比 + 诚信验证** | 准确性数字远端见证为真;治理能力矩阵;mean-perturbation baseline;manifest + abstain_gain;三表汇总进论文 |

---

## 3. 关键结果数字 + 可信度分层(判断核心)

### A. 真实跑出来、本会话远端当场见证为真(可复现,凭证见 `finding_w8_provenance_reverify.md`)
| 指标 | 值 | 见证方式 |
|---|---|---|
| Coordinator ΔPearson(all-5) | **0.7039**(0.703874) | 远端重 eval |
| Coordinator(cpa+decoder+gnn / latent+gnn) | 0.7020 / 0.6847 | 远端重 eval |
| 6 base(cpa/decoder/gnn/linear/latent/pretrained) | 0.6716 / 0.6709 / 0.6675 / 0.6639 / 0.6365 / 0.6183 | linear 逐位,其余 diff 与 finding 一致 |
| scGPT frozen(53.8M backbone + 2.47M head) | **0.4407** | 存档 ckpt 逐位复现(n=7290) |
| mean-perturbation naive baseline | **0.4615** | 本会话新写、实跑(n=18874) |
| abstain_gain risk-coverage | 0.672→0.754(弃权 26% 时 +0.082) | 本会话新做,真 donor predictor |
| ablation A↔D 五指标 | 全 0→1 | Mac 本地确定性,75 passed 当场复跑 |
| 等价性 | atol 1e-6(linear 逐位 diff 1.2e-8) | — |
| n(主 split) | 18874 | — |

> **诚信结论:论文里没有任何编造或对不上的数字。** 全部可追溯、可复现。

### B. 是「复现 donor」,不是 PRAXIS 自己更准(易误读)
- 0.7039 = 复现 donor Coordinator 的 ensemble。**通讯层不参与张量计算**;智能体包装只逐元素复现底层预测器(atol 1e-6)。
- 性能 claim 仅"包装**不损害**性能",**不是"message-passing 跑出更高 Pearson"**。

### C. 声明式、当前 mock 流不自发激活(机制存在 ≠ 运行时触发)
- model-disagreement 子触发 / core-predictor-failed / cell-type 降级:有实现 + **手搓测试证明可激活**,但 mock 端到端流不自发触发,真实激活待真 predictor。
- 注:abstain **主路径**(物种拒绝 / 空 targets / 全拒)是运行时真激活;disagreement-based abstain 在 abstain_gain 实验里也用**真 predictor 跑通**。

### D. off-axis,不可比
- GEARS pearson_de **0.8392**(重训 0.8461 同量级,确认真实):指标 = DE 基因 absolute pearson、split 不同,**永不与 ΔPearson 同表**。

---

## 4. 系统全面对比(W8 三表)

### 表 A — 准确性(same-protocol:donor norman test · per-cell ΔPearson · 同 EvalAgent · n=18874)
Coordinator 0.7039 > 6 base 0.6716–0.6183 > **mean-baseline 0.4615** > scGPT frozen 0.4407。
- 诚实点:scGPT frozen **反低于**平凡 mean baseline(印证"规模非解药")。
- 缺口:强外部 task-specific baseline(GEARS 同 split / scGen / STATE)**未接入**(S3/S5 未做)。

### 表 B — 治理能力矩阵(据实核查 5 系统公开论文+repo,每格附依据)
| 能力 | GEARS | CPA | scGPT | scGen | STATE | PRAXIS |
|---|---|---|---|---|---|---|
| OOD/跨物种拒绝 | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| applicability 检查 | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| abstain | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| provenance + trace | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| 多模型可审计通讯 | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| retrieve-before-predict + critic | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| 离线确定性可复现 | 部分 | 部分 | 部分 | 部分 | 部分 | ✓ |

### 表 C — abstain_gain / risk-coverage(真 donor predictor,manifest `data/manifests/norman_2019.yaml`)
| coverage | 保留集 ΔPearson | gain(vs 满覆盖 0.6716) |
|---|---|---|
| 1.00 | 0.6716 | —(参考)|
| 0.96 | 0.6830 | +0.011 |
| 0.88 | 0.7071 | +0.036 |
| 0.82 | 0.7320 | +0.060 |
| 0.74 | 0.7536 | +0.082 |
> 单调正向。阈值附近有 GPU 浮点抖动 → 用固定满覆盖参考、强调趋势、不报单点。

**真实 OOD-pert split**:test 151 扰动中 **82 个未见(13056 cells)**、69 已见(5818 cells),由 train/test 重叠实测导出。数据指纹:norman h5ad 937614888 B,sha256 `e3d116b4…4317de`。

---

## 5. 论文状态

- **v0.2 完整初稿** `docs/paper/v0.2/PRAXIS-VirtualCell-v0.2-manuscript.md`:ARS 管线从头写;四问四节;中英双语摘要;**22 篇引用全部 CrossRef/官方核验真实**(`phase1_literature.md`);W8 三表已汇总进 §3.3/§3.4/Discussion/Limitations/Abstract。
- v0.1 旧稿 `docs/paper/PRAXIS-VirtualCell-v0.1-manuscript.md`(已过 5 审稿人对抗审查),保留对照。
- 5 张图 `docs/paper/figures/`(Fig1–5,4 格式)。
- **两条最致命审稿缺口已补**:R8(无外部 baseline)由 mean-baseline 部分补;R9(无 manifest/abstain_gain)由真 manifest + risk-coverage 补。

---

## 6. 诚实局限(完整,供扣分)

1. **性能维度不赢 SOTA、也不声称赢**;强外部 task-specific baseline(GEARS 同 split / scGen / STATE)**未接入**——表 A 最大空缺。
2. **最小可发表口径**:仅在**人类**单细胞扰动上验证;mouse/bacteria/yeast 是**路由层原型**,无真跨物种预测器(ortholog 投影只跑路由/caution,未驱动真预测)。
3. abstain_gain 在**整个 test set** 上做;"仅 OOD 子集 / abstained 是否富集 OOD"未做;阈值附近 GPU 浮点抖动。
4. 声明式机制(§3C)真实激活待真 predictor。
5. ablation 实为 A↔D 两极(B 纸面、C≈D 被砍);A 是 stub,4/5 指标 0 是"结构性没有"而非"测出来差"。
6. abstain_gain 用的是 cpa 为 primary、其余 base 作 aux 的一种配置;未系统比较其他 primary/aux 组合。

---

## 7. 工程 / 代码 / 测试

- **测试**:Mac **75 passed + 25 skipped**(ml 测试标 `remote`,Mac 无 torch 自动 skip;远端全 ml pass)。
- **代码**:已全部 push `origin/main`(`git@github.com:NHNQNHNQ/PRAXIS-Virtualcell.git`,HEAD `84211de`)。
- **远端**:`zkyd@10.102.106.53`(8×A100);env `virtualcell`(torch2.6+donor+GEARS/PyG)/ `vc-scgpt`(torch2.3+scgpt)/ `vcell`;donor 只读 `/home/zkyd/data1/mzy/'Virtual cell'`。
- **架构**:`core`(request/message/bus/agent/runtime,**freeze**)+ 10 个确定性 agent(input_interpreter→object_normalizer→species_brain→model_applicability→predictor-agents→ensemble→reliability→critic→provenance→report)+ 4 个可选 LLM agent + `predictors/ml`(donor 桥接)+ `brains/virtualcell`(逐物种 YAML)+ `benchmarks`。

---

## 8. 未做 / Backlog(带工作量估计)

| 项 | 价值 | 工作量 |
|---|---|---|
| S3:GEARS 适配 donor split + ΔPearson(解不可比) | 高(补 R8 强 baseline) | 中–大(gene-name 接口 → EvalAgent delta 格式) |
| S3:scGen 接入同协议 | 高 | 中(新 predictor + 训练) |
| S5:STATE 接入同协议 | 高(最新 SOTA 对照) | 大(跨 env 适配 Arc 模型) |
| 真 cross-species predictor(让 ortholog 投影驱动真预测) | 中–高(去掉"仅路由层"局限) | 大 |
| 声明式机制真激活(需真可失败 predictor) | 中 | 中 |
| `agent_adapter` single-control→per-cell(解 W4.5 失配,让 C/D 出独立 Pearson) | 中 | 中 |
| B/C ablation 真实现(若审稿坚持 4 档) | 中 | 中 |
| abstain_gain OOD 细化(仅 OOD 子集 / 富集度) | 中 | 小–中 |
| 论文收口(转 LaTeX/DOCX、再过 ars-reviewer、AI disclosure) | 高(投稿前必做) | 小–中 |

---

## 9. 诚信验证记录(本会话当场见证)

应"复核是否有编造"的要求,本会话在远端重跑见证:linear 逐位复现 S0=0.6638587(16 位)→ 评测 harness 真实;6 base diff 与历史一致;Coordinator 0.703874;scGPT 逐位 0.4406901964584723;GEARS 重训 0.8461 同量级;ablation/cross-species Mac 当场复跑(75 passed)。**结论:全部量化结果真实,未发现任何编造。** 凭证:`docs/findings/finding_w8_provenance_reverify.md`。

---

## 10. 供你自己判断的问题清单

- **定位**:你要投的场子吃不吃"治理 / 可信 / 系统"论文(vs 硬要求预测 SOTA)?PRAXIS 的全部卖点押在这个角度。
- **预测贡献**:能接受"预测性能上是复现 donor + 套壳、无新 SOTA"吗?
- **scope**:mouse/bacteria/yeast 只到路由层,会不会被认为 over-scoped、该砍回纯 human?
- **外部 baseline**:R8 只是部分补(mean-baseline + scGPT),没有强外部 task-specific baseline,够不够过审?
- **可信 vs 噱头**:治理层(拒绝/弃权/溯源/审计 + abstain_gain 定量证据)是否构成足够的"新贡献",还是会被视为工程包装?

---

## 11. 关键文件索引

- 论文:`docs/paper/v0.2/PRAXIS-VirtualCell-v0.2-manuscript.md` · `phase1_literature.md` · `04_systems_comparison_plan.md` · `docs/paper/PRAXIS-VirtualCell-v0.1-manuscript.md` · `docs/paper/figures/`
- findings:`docs/findings/finding_w4{a,b,c}_*` · `finding_w5_cross_species` · `finding_w6_reliability_critic` · `finding_w7_ablation` · **`finding_w8_systems_comparison`**(三表)· **`finding_w8_provenance_reverify`**(诚信)
- manifest:`data/manifests/norman_2019.yaml`
- benchmarks:`praxis_virtualcell/benchmarks/{mean_baseline,abstain_gain,coordinator_eval,_anchor_donor_linear,_anchor_donor_multi,gears_norman,scgpt_train_eval,ablation}.py`
- 版本 / 交接:`docs/RELEASE-v0.1.0.md` · `docs/HANDOFF-w8-comparison.md`
