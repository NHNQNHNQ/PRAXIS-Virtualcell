# Week 2 — 通讯式多智能体 runtime(communicative agent runtime)设计 spec

- 日期:2026-06-12
- 方向:**iii-lite**(LLM-assisted but not LLM-dependent)
- 上游:用户《PRAXIS-VirtualCell 详细执行计划》§2、§4、§13、§16
- 仓:`/Volumes/T7/PRAXIS-virtualcell`(新增 top-level 包 `praxis_virtualcell/`)

---

## 0. 锁定的方向与关键决策

- **iii-lite**:离线可复现的 brain / rule / predictor-agent / reliability / provenance 为核心;LLM 仅在 API 可用时做 input 理解 / 路由建议 / critic / report 增强,**绝不进 benchmark 与主预测闭环**。
- **`praxis_virtualcell` 自包含**:自建 runtime(request/message/bus/runtime/trace/provenance),**主链路不 import praxis2**。`praxis2`(server/auth/accounting/mcp/spawn/scheduler/admin/llm)降为 **optional legacy**,保留在仓里但不进虚拟细胞主链路。
- **两套 brain 并存**:① 新 `praxis_virtualcell/brains/virtualcell/`(yaml 规则,**本项目主用**);② 旧 top-level `brains/virtualcell/`(praxis2-legacy markdown case/rule,Week 1 遗留,不在主链路)。本 spec 只动 ①。
- **数据结构用 `@dataclass`**(对齐两仓约定;不引 pydantic)。
- **双模式从第一天**:`mode = offline | llm_assisted`。Week 2 只做 offline 全链路 + mode 开关 + 无 key 时 llm_assisted 自动 fallback 到 offline(LLM agent 本周只放 stub,不真调 API)。

## 1. Week 2 目标与范围

**目标**:证明 PRAXIS-VirtualCell 是**真多智能体**,不是 predictor+ensemble 的假壳。即:输入解析成结构化 request → agent 间经 MessageBus 通讯 → 检索先行门(未查脑不许预测)→ mock predictor-agent 可独立 success/rejected/failed → ensemble → reliability/abstain → critic 抓违规 → provenance/report,全程 offline、有完整 trace。

**做(Week 2)**:
- `praxis_virtualcell/core/`:VirtualCellRequest / AgentMessage / PredictorResultMessage / ReliabilityDecision / BaseAgent / MessageBus / AgentRuntime / TraceRecorder / Provenance / exceptions / config(mode)。
- `praxis_virtualcell/agents/`(deterministic,offline):InputInterpreter / BioObjectNormalizer / SpeciesBrain / ModelApplicability / EnsembleCoordinator / Reliability / Critic / ProvenanceAgent / Report。
- `praxis_virtualcell/predictors/`:PredictorAgent base + mock_linear / mock_cpa / mock_gears(纯 mock,无 torch)。
- `praxis_virtualcell/agents_llm/`:仅占位 stub(LLMClient disabled + 4 个 optional agent 的空实现/fallback),**Week 3 才真接 API**。
- `praxis_virtualcell/brains/virtualcell/{generic,human}/`:最小 yaml(task_schema / default_abstain_rules / human model_applicability + object_vocabulary),够 SpeciesBrain + ModelApplicability + retrieve-before-predict 跑通。
- `praxis_virtualcell/workflows/predict_delta_expression.py`:串起 mock workflow。
- `praxis_virtualcell/examples/norman_mock_request.json`(+ bacteria / mouse-transfer mock,供 Week 5 用,本周建文件即可)。
- `praxis_virtualcell/tests/`:覆盖 §4.6 的 10 条验收。

**不做(留后续 week,各自 spec)**:真 LLM 调用(W3)、迁真 ML predictor(W4)、完整 species brain(W5)、reliability/critic 深化(W6)、benchmark/ablation(W7)、release(W8)。**本周禁止 import torch / 调任何 API。**

## 2. 架构(6 层)

```
Layer1 Input understanding      InputInterpreterAgent (+LLM stub)
Layer2 Object normalization     BioObjectNormalizerAgent
Layer3 Species brain governance SpeciesBrainAgent + ModelApplicabilityAgent (+LLMRouter stub)
Layer4 Predictor-agents         MockLinear/MockCPA/MockGEARS (PredictorAgent base)
Layer5 Ensemble/reliability     EnsembleCoordinatorAgent + ReliabilityAgent + CriticAgent (+LLMCritic stub)
Layer6 Provenance/report        ProvenanceAgent + ReportAgent (+LLMReport stub)
```

**Coordinator 不是黑箱中心**:`EnsembleCoordinatorAgent` 只做"通讯 + 汇总",路由决策在 `ModelApplicabilityAgent`,可靠性在 `ReliabilityAgent`。所有 agent 只经 **MessageBus** 通讯,不互相直接调内部方法。

## 3. 核心数据结构(`core/`,@dataclass)

- **VirtualCellRequest**(`request.py`):request_id / species / cell_type / tissue / perturbation_type / perturbation_targets / perturbation_dose / perturbation_time / input_modality / output_modality / task_type / baseline_context / metadata / constraints。第一阶段真支持 `species=human, input_modality=scRNA, perturbation_type=gene, task_type=predict_delta_expression`;schema 预留 drug/mutation/cytokine/environment/combination/bacteria/yeast/mouse/multiomics/phenotype/viability/morphology(字段存在即可,不实现逻辑)。
- **AgentMessage**(`message.py`):message_id / sender / receiver / message_type / payload / timestamp / parent_message_id。
- **PredictorResultMessage**(`message.py`):agent_name / status(success|rejected|failed) / prediction / uncertainty / applicability_score / evidence / rejection_reason / provenance。
- **ReliabilityDecision**(`message.py`):reliability(high|medium|low) / abstain(bool) / reasons / failed_checks / model_disagreement。
- timestamp:用注入的 clock(`config` 提供 `now()`;测试可注入固定时钟,避免 `Date.now` 类不可复现)。

## 4. 运行时(`core/`)

- **MessageBus**(`bus.py`):`send(msg)` / `get_messages(agent_name)` / `record_trace(msg)` / `export_trace(path)`。不变式:agent 间**只经 bus**;predictor-agent **只能经 bus 收任务**;workflow 结束可 `replay trace`。
- **AgentRuntime**(`runtime.py`):`register_agent(agent)` / `dispatch_message(msg)` / `run_workflow(request)` / `export_outputs(dir)`。持 `mode = offline | llm_assisted`;llm_assisted 无 key → fallback offline。
- **BaseAgent**(`agent.py`):`name`;`handle(message, bus, ctx) -> list[AgentMessage]`(只通过 bus 产出);可选 `can_handle`。
- **TraceRecorder**(`trace.py`)+ **Provenance**(`provenance.py`):导出 `trace.json` / `prediction_report.json` / `provenance.json`。
- **retrieve-before-predict 门**:runtime/predictor 强制——若 trace 中**无 SpeciesBrain 检索消息在前**,predictor-agent 的 `run_prediction` 抛/拒(`exceptions.RetrieveBeforePredictError`)。这是反幻觉硬门。

## 5. PredictorAgent base 与 mock(`predictors/`)

`PredictorAgent(BaseAgent)` 契约(每个能回答"能不能/为什么/用了什么/输出/不确定性/失败原因"):
```
assess_applicability(request, brain_context) -> applicability_score + reason
prepare_input(normalized_object)
run_prediction(model_input)                # 受 retrieve-before-predict 门约束
build_result_message(output) -> PredictorResultMessage  # status ∈ success|rejected|failed
```
mock 行为(无 torch):MockLinear 总 success 返回常数 delta(baseline/sanity);MockCPA 按 applicability(human+scRNA+gene)success,否则 rejected;MockGEARS 若 `gene_not_in_graph_vocabulary`(查 human object_vocabulary.yaml)→ **rejected**(不硬预测),否则 success。

## 6. agents_llm/ 占位(`agents_llm/`,Week 2 仅 stub)

`LLMClient`(complete(messages, schema) 接口)本周只实现 `mock` 与 `disabled` 两态;`LLMInputInterpreter/LLMRouter/LLMCritic/LLMReport` 为 optional agent,offline / 无 key 时被 runtime 跳过或返回"未启用"。**Week 2 不真调 OpenAI/Anthropic。**

## 7. mock workflow(`workflows/predict_delta_expression.py`)

输入 `examples/norman_mock_request.json`(human/K562/gene/["AHR"]/scRNA/predict_delta_expression)→
InputInterpreter → BioObjectNormalizer → SpeciesBrain(检索 human brain)→ ModelApplicability(CPA✓ GEARS✓ Mechanistic✗)→ MockCPA → MockGEARS → EnsembleCoordinator → Reliability → Critic → ProvenanceAgent → Report。输出目录含 trace.json + prediction_report.json + provenance.json。

## 8. 最小 brain(`brains/virtualcell/`,yaml)

- `generic/`:task_schema.yaml、default_abstain_rules.yaml、general_negative_transfer.yaml(占位规则)。
- `human/`:model_applicability.yaml(CPAAgent/GEARSAgent 的 supported_species/modalities/tasks/perturbations + GEARS `reject_if: gene_not_in_graph_vocabulary`)、object_vocabulary.yaml(一小批 human gene symbol,含/不含 AHR 用于测 GEARS reject)。
- SpeciesBrainAgent 读这些 yaml 返回 `brain_context`;ModelApplicabilityAgent 据此裁决。

## 9. 验收(= §4.6 的 10 条,落成 `tests/`)

1. JSON 可解析为 VirtualCellRequest(test_request_schema)
2. agent 间经 AgentMessage 通讯(test_message_bus)
3. trace.json 有完整通讯链(test_trace)
4. 未查 brain → predictor 不许执行(test_retrieve_before_predict)
5. predictor 可返回 rejected(test_predictor_rejection,GEARS on 未知 gene)
6. ReliabilityAgent 可触发 abstain(test_abstain)
7. CriticAgent 抓"未预测却声称预测"(test_no_fake_multiagent)
8. offline mode 不需任何 API key(test_offline_mode)
9. llm_assisted 无 key 自动 fallback(test_llm_optional)
10. Coordinator 不能绕过 bus 直接调 predictor(test_no_fake_multiagent / bus 不变式)

**额外硬门**:`praxis_virtualcell` 主链路 grep 无 `import torch`、无 `openai`/`anthropic` 真调用;所有 offline test 无网络/无 key。

## 10. 风险与处置(对应计划 §14)

| 风险 | 处置 |
|---|---|
| 变 LLM 包装器 | 主闭环 offline 可跑;LLM 不生成预测值;benchmark 不依赖 API(本周 LLM 仅 stub) |
| 假多智能体 | MessageBus 强制通讯 + predictor 独立返回 + trace 完整 + test_no_fake_multiagent |
| 复杂度失控 | 全 mock,不迁 torch、不接 API;先证 runtime |
| 不可复现 | 注入 clock + 固定 request_id/message_id 生成器(测试可控);offline 确定性 |

## 11. 交付物
- 新 top-level 包 `praxis_virtualcell/`(core + agents + predictors + agents_llm stub + brains + workflows + examples + tests)。
- mock workflow 可 offline 跑通,产出 trace/report/provenance。
- 10 条验收测试绿;主链路无 torch/无 API。
- 不动 praxis2 主代码(legacy 保留)。
