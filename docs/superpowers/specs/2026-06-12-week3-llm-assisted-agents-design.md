# Week 3 — LLM-assisted agents(纯 DeepSeek)设计 spec

- 日期:2026-06-12
- 状态:待用户复核
- 前置:Week 2 communicative agent runtime(已完成,35 tests 绿)
- 上游:iii-lite 计划 §5;方向见 `docs/STATUS-2026-06-12-direction.md`

## 0. 决策(已与用户确认)
1. **纯 DeepSeek**:httpx 直打 `api.deepseek.com/chat/completions`,不做 OpenAI/Anthropic 抽象,不引入 `openai`/`anthropic` SDK。
2. **LLM 测试用真 DeepSeek,不 mock**:LLM-assisted 通讯式智能体是创新,必须真打 DeepSeek 验证。无 key/无网时这些测试 skip;Week 2 的 35 个 offline 测试不变(无 key 也绿)。

## 1. 目标与范围
在 Week 2 runtime 上加 **LLM-assisted seam**:`offline` 走纯确定性路径(Week 2);`llm_assisted` 引入 4 个 LLM agent 做**输入理解 / 路由建议 / critic / 报告生成**的增强。**LLM 严格只增强、只建议,绝不进数值预测路径**;主预测/benchmark 数值在 offline 下可复现、不依赖 API。

**不做(本期)**:OpenAI/Anthropic backend;迁真 ML predictor(W4);真实 benchmark(W7)。

## 2. 组件

### 2.1 LLMClient(纯 DeepSeek,httpx)
`agents_llm/llm_client.py`(替换 Week 2 stub):
- `complete(messages, *, json_mode=False) -> dict`:`disabled` 时返回 `{"disabled": True}`;否则 httpx POST `{base_url}/chat/completions`,body `{model, messages, temperature:0, max_tokens, response_format:{"type":"json_object"} if json_mode}`,`Authorization: Bearer {key}`,timeout 60s。返回 `{"disabled": False, "content": <str>, "raw": <resp>}`;HTTP/解析失败返回 `{"disabled": False, "error": <str>, "content": None}`(不抛,调用方 fallback)。
- 不 import openai/anthropic;只用 httpx(现成依赖)。
- `make_llm_client(config)`:`enabled = mode is LLM_ASSISTED and bool(config.deepseek_api_key)`。

### 2.2 config + .env
`core/config.py`:
- `RuntimeConfig` 加 `deepseek_api_key: str = ""`、`deepseek_base_url: str = "https://api.deepseek.com"`、`deepseek_model: str = "deepseek-chat"`。
- `load_env(path=".env")`:若文件存在,逐行 `K=V` 注入 `os.environ`(无新依赖;已存在的 env 不覆盖)。
- `RuntimeConfig.from_env()`:`load_env()` 后从 `os.environ` 读 key/base_url/model + `PRAXIS_VIRTUALCELL_MODE`。
- 提交 `.env.example`(占位);`.env` 仍 gitignored。

### 2.3 4 个 LLM agent(都是 BaseAgent,走 bus,trace 可审计)
均构造时持 `LLMClient`;`enabled=False` 时 emit 一条"skipped"消息并退化(等价 offline)。

- `LLMInputInterpreterAgent`(`agents_llm/llm_input_interpreter.py`):
  收 `{"text": <free-text>}` → prompt DeepSeek(json_mode)出 VirtualCellRequest JSON → **`VirtualCellRequest.from_dict` 校验** → 成功 emit `request_parsed`(与 Week 2 `InputInterpreter` 同 message_type,下游管线零改动);失败(LLM error / 校验失败)→ emit `llm_input_failed`,runtime fallback 到 `input_missing` 报告。
- `LLMRouterAgent`(`agents_llm/llm_router.py`):
  收 `{request, brain_context, applicable, rejected_candidates}` → DeepSeek 出 `{recommended_agents, excluded_agents, reasoning_summary, risk_flags}` → emit `llm_route_suggestion`。**仅建议**:runtime 记进 provenance;与 rule 决策(`ModelApplicability`)冲突 → 记 `caution` flag。**不改 applicable 集 → 不改数值。**
- `LLMCriticAgent`(`agents_llm/llm_critic.py`):
  收 `{report}` → DeepSeek 审(夸大 / 违 brain rule / 漏不确定性 / rejected 写成 used)→ emit `llm_critic_notes`(notes + flags)。**不改 prediction**;并进 provenance。
- `LLMReportAgent`(`agents_llm/llm_report.py`):
  收 `{report}` → DeepSeek 把结构化报告转中文 NL 叙述 → emit `llm_narrative`。挂到 `report["narrative"]`;**结构化字段不变**,不得编造结构里没有的结论。

### 2.4 runtime mode 集成
`core/runtime.py`:
- `run_workflow(request)`(结构化输入,offline + llm_assisted 都用):数值路径与 Week 2 完全一致。当 `mode==LLM_ASSISTED and client.enabled`,在 seam 额外经 bus 调:
  - applicability 后:`LLMRouter` → 建议进 provenance(+ 冲突 caution),applicable 集不变。
  - critic 后:`LLMCritic` → notes 进 provenance。
  - report 后:`LLMReport` → narrative 挂 `report["narrative"]`。
- `run_workflow_from_text(text)`(free-text,仅 llm_assisted):`LLMInputInterpreter` → `request_parsed` → 复用 `run_workflow` 余下管线;offline 模式调用 → 抛 `InputValidationError("free-text 需 llm_assisted + key")`。
- LLM agent 经 `build_runtime(config)` 在 llm_assisted 时注册(持 client)。

## 3. 数值不变保证(核心不变量)
`llm_assisted` 下 `predictor → ensemble → reliability → abstain → 结构化报告字段`(prediction/abstain/reliability/models_used/models_rejected/abstain_reasons/critic_violations)与 `offline` **逐字节相同**(给定同一 VirtualCellRequest)。LLM 仅新增:`report["narrative"]`、`provenance["llm_route_suggestion"]`、`provenance["llm_critic_notes"]`。
→ 复现性测试:结构化输入,断言 llm_assisted 的结构化字段 == offline。

## 4. 测试(真 DeepSeek,标 `llm`)
`praxis_virtualcell/tests/conftest.py`:注册 marker `llm`;`pytest_collection_modifyitems` 在 `not os.environ.get("DEEPSEEK_API_KEY")` 时 skip 所有 `llm` 用例。LLMClient 用 `RuntimeConfig.from_env()`。

- Week 2 的 35 offline 测试**不变**(无 key 也绿)。
- 新增(标 `@pytest.mark.llm`,真打 DeepSeek,断言鲁棒抗 LLM 抖动):
  - `test_llm_input_interpreter.py`:一句中文实验描述(如 "在 K562 细胞里敲除 AHR,预测转录组变化")→ 解析出 `species=human`、`AHR` ∈ targets、`task=predict_delta_expression`。
  - `test_llm_router.py`:出建议且 `recommended ⊆ 候选`;runtime 最终 applicable 集 == 纯 rule 结果(LLM 不改)。
  - `test_llm_critic.py`:注入一份"把 rejected 模型写成 used / 夸大"的报告 → LLMCritic flags 命中。
  - `test_llm_report.py`:abstain 的报告 → narrative 含 abstain 语义、不出现结构里没有的预测数值。
  - `test_llm_e2e_demo.py`:free-text → 真 DeepSeek 解析 → 预测 → LLMCritic → LLM 中文报告;断言 report 有 narrative + 完整 provenance + trace 含 `llm_*` 消息。
  - `test_llm_numeric_invariance.py`:结构化输入,`llm_assisted` 结构化字段 == `offline`。
- 无 key fallback 测试(**offline 标,无需 key**):llm_assisted 配置但 key 空 → client disabled → `run_workflow` 等价 offline 路径(structured 字段与 offline 同),不抛。

## 5. 安全/配置
- `.env`(gitignored)持真 key;`.env.example`(提交)占位。
- LLM 输出一律 JSON mode + `from_dict`/schema 校验;校验失败 fallback,不让 LLM 自由文本直接进结构。
- offline 路径零 LLM、零网络调用(保留 Week 2 硬门:主链路无 openai/anthropic SDK import)。

## 6. 交付物
- `agents_llm/{llm_client, llm_input_interpreter, llm_router, llm_critic, llm_report}.py`(替换/扩展 stub)
- `core/config.py` 扩展 + `load_env`/`from_env`;`core/runtime.py` llm_assisted seam
- `.env.example`;`examples/free_text_request.txt`
- `praxis_virtualcell/tests/conftest.py` + 上述测试
- Week 2 offline 底座零改动

## 7. 验收(对齐 iii-lite §5.7)
1. 无 key 时所有 offline 测试通过(35 + fallback 测试)。
2. 有 key 时 LLMInputInterpreter 正确解析复杂 NL 输入。
3. LLMRouter 只建议,不改 applicable 集。
4. LLMCritic 不改 prediction 数值,能挑出违规报告。
5. LLMReport 不编造 provenance/结论。
6. 结构化输入下 offline 与 llm_assisted 主预测结构化字段一致。
7. end-to-end llm_assisted demo 用真 DeepSeek 跑通(free-text → 中文报告 + provenance + trace)。

## 8. 风险
- LLM 非确定性 → temp=0 + JSON mode + 鲁棒断言(查结构属性非精确文本)。
- DeepSeek 网络/额度波动 → `llm` 测试 skip-without-key;offline 底座不受影响。
- LLM 越界改数值 → 架构上 LLM 不在数值路径;numeric_invariance 测试守住。
