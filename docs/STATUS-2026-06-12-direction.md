# PRAXIS-virtualcell 现状与方向决策(2026-06-12)

## 1. 现状(Week 1 已完成)

- 新仓 `/Volumes/T7/PRAXIS-virtualcell` = **复制 PRAXIS-2 的 claude-code-style agent OS** + 去 13 学科脑 + 单一 `virtualcell` 脑。已 push 到 `NHNQNHNQ/PRAXIS-Virtualcell.git`。
- 它现在**只有 agent 框架外壳,没有任何 ML predictor**。
- ML 核心还在 donor `/Volumes/T7/Virtual-cell`:predictors(linear/cpa/gnn/latent/decoder/mechanistic + gears/scgpt 包装)、coordinator(router/ensembler/eval_agent/calibration)、ExperienceQuery、abstain。**全是 torch/numpy,API-free**,finding_015 已 3 bench PASS,Coordinator Norman~0.70。
- 计划 Week 2 = 在新仓建 `praxis_virtualcell/` 骨架,Week 3 把 donor ML 迁进来包成 predictor。

## 2. 你点出的核心张力

PRAXIS-2 的全部价值是**编排一个 LLM**用真工具 + 记忆 + 反幻觉做科研(agent loop / RMCP 相位门 / MCP / server)。
但虚拟细胞的 ML 核心(Coordinator + abstain)是**纯数值 ML**:训练→预测 delta 表达→校准→abstain,**不需要 LLM、不需要 API、不需要 agent loop**。这里的 "Coordinator" 是 ML ensembler,"Subagent" 是模型集合持有者,都不是 LLM agent。

→ 所以:**如果 ML 全程 API-free,那把整个 LLM agent 框架搬过来到底有什么用?**

## 3. "无 API / manual mode" 如何化解张力(关键)

你锁定过两条约束:**① agent-as-orchestrator(顶层 LLMAgent 查经验→路由 subagent→小模型作 tool);② 无 API key,manual mode 为主,Claude-in-chat 替代运行时 LLM 调用。**

这两条合起来,agent 框架在 API-free 世界里的真实角色是 **"确定性的、大脑引导的编排/治理层"**,不是跑一个活 LLM:
- **大脑(brains 运行时)**:物种感知的经验/case 记忆 + model_applicability / negative_transfer 规则。BM25 检索 + 规则匹配,**无 LLM**。
- **RMCP 相位门 + 检索先行反幻觉**:"预测前必须先查经验;声称预测必须真调一个 predictor(不许编)"。是状态机,**无 LLM**。
- **Tool 契约 + provenance**:predictor 当 tool,结构化结果 + 证据链。**无 LLM**。
- **rule-based 路由**(loader 关键词匹配,已是确定性):可演化成 species/task 路由。

→ **LLM(Claude,manual)只在设计/manual 时用**:帮你写大脑规则、解释结果、审 case;**不进 eval 闭环**。
→ 所以 plan A(torch-free core)**不等于"agent 框架没用"**:这里的 "agent" = 大脑 + 规则 + 路由 + 反幻觉门 + provenance,而不是活 LLM。Coordinator 就是那个确定性 agent。

但要诚实:PRAXIS-2 里**只有一部分**对 API-free 虚拟细胞有用 ——
- **有用**:`brains`(脑存储/检索/case-rule schema/RMCP write-review)、`core`(RMCP 相位门 + 检索先行)、`tools`(Tool/ToolResult 契约)、`memory`、`agents/loader`(规则路由)、provenance。
- **无用/包袱(对论文)**:`llm`(LLM client)、`server`/`auth`/`accounting`/`mcp`/`spawn`/`scheduler`/`admin` —— 这些是 SaaS + 活 LLM runtime,eval 用不到。

## 4. 方向分叉(请你判断)

### 方向 i:精简 ML,弃 agent 框架
`praxis_virtualcell` 就是个 torch ML 包(predictors + Coordinator + abstain)。承认复制 PRAXIS-2 是弯路,把它压到最小或弃用。
- **论文 = ML ensembling + abstain 可靠性。** 卖点纯数值。
- 代价:放弃"大脑引导多智能体"叙事;PRAXIS-2 白复制。

### 方向 ii:大脑引导 · 规则驱动的 agent OS(API-free)【推荐】
保留 PRAXIS-2 的 **brain / RMCP / tools / memory / provenance / rule-routing**(上面"有用"那半);裁掉 llm/server/auth/mcp 那半(或留着不依赖)。
Coordinator = 确定性 agent:**ExperienceQuery(species 脑)→ 规则路由(model_applicability)→ predictor ensemble → reliability/abstain → provenance**,全程离线无 API。
- **论文 = brain-guided multi-agent 虚拟细胞 OS,跨物种、按经验+规则路由异构 predictor、检索先行反幻觉、低可靠 abstain、全离线。** ML 数值结果(Norman 0.70 / abstain gain)做支撑证据,框架治理是主贡献。
- LLM(Claude,manual)只在设计期写规则/解释,不进 eval。

### 方向 iii:manual-mode LLM agent(ii + 活 LLM 可选挂载)
同 ii,但额外保留"可挂活 LLM(manual / Claude-in-chat)做路由/解释"的路径,论文强调 LLM 编排 + manual mode。比 ii 多背 llm/server 那半,复杂度更高。

## 5. 我的推荐:方向 ii

理由:① 让 agent 框架在无 API 下**真的有用**(大脑+规则+反幻觉门是确定性的,能跑 eval);② 复用 PRAXIS-2 的真资产(brain/RMCP/tools/provenance),不白复制;③ 符合你锁定的 agent-as-orchestrator + no-API;④ 论文有框架级新意(离线 brain-guided predictor 编排 + 跨物种治理 + abstain),又有硬数值支撑。
代价:得把 PRAXIS-2 那"无用的一半"(llm/server/auth/mcp/...)显式标记为 optional / 后续裁,别让它进 ML eval 依赖。

## 6. 每个方向下 Week 2 变成什么

- **i**:`praxis_virtualcell/` = 纯 torch 包(core 类型 + Predictor base + Coordinator),不碰 praxis2。最小、最快。
- **ii(推荐)**:`praxis_virtualcell/core`(torch-free 富类型,plan A)+ `Predictor`/`Subagent` base + `VirtualCellCoordinator` skeleton,**且 Coordinator 接 praxis2 的 brain(ExperienceQuery)+ RMCP 检索先行门 + Tool 契约 + provenance**。mock workflow 跑通"查脑→路由→mock predictor→abstain→带 provenance 的 Prediction",全离线。
- **iii**:ii + 一个 optional LLM 编排适配器(manual mode),Week 2 先不做。

→ 关键洞察:**plan A 的 torch-free core 在方向 ii/iii 下完全成立且必要**(core 是公共契约,torch 留在具体 predictor;Coordinator 用 praxis2 大脑做路由/治理)。你担心的"没必要加 agent 框架"只在方向 i 成立。
