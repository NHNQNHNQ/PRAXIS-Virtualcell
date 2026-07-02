# PLAN v0.6 — LLM-Assisted Local Scientist Interface(工程化,代码对齐版)

> 来源:用户工程化方案(2026-07-02)。本文件把它对齐到**现有代码库**并拆成可执行分阶段步骤。
> **铁律(最高优先,写进代码注释)**:核心科学闭环离线/确定性/可复现;LLM 只做 4 件事(输入解析 / 路由建议 / critic 复核 / 报告润色),**绝不**碰 prediction / hard-rule / learned reliability / abstain-downgrade-accept 终决 / artifact 校验 / provenance。默认 `mode=OFFLINE, llm_enabled=False`。
> `allow_llm_to_modify_core_decision / _prediction / _override_hard_rules` **永远 False**(常量,不可配置为 True)。

## 0. 现状对齐(gap analysis)

| 组件 | 现状 | 动作 |
|---|---|---|
| `core/config.py` Mode/llm_enabled/deepseek_* | ✅ 已有 | 加 3 个 `allow_llm_*=False` 常量 flag + 断言 |
| `agents_llm/`(client/interpreter/router/critic/report) | 🟡 已有但薄(32-55 行),有 `test_llm_*` | **补强**:JSON schema 输出 + deterministic validator + fallback + prompt/response hash;抽 `prompts/*.md` |
| 确定性 runtime/bus/governance/predictors | ✅ 完整(203 tests) | **不动**(LLM 是外层) |
| workflows predict_delta_expression(_ml) | ✅ 已有 | 加 `run_virtualcell_query`(自然语言→candidate→validator→confirmed→runtime→report,含 LLM 元数据) |
| `io/job_store` / report_export | ❌ 无 | 新建(sqlite/文件 runs/) |
| `praxis_vc_api/`(FastAPI) | ❌ 无 | Phase 2 新建 |
| `praxis_vc_web/`(Streamlit) | ❌ 无 | Phase 3 新建 |
| CLI console_scripts | ❌ 无 | pyproject 加 `praxis-vc` 入口(run/ask/serve/web) |

**结构决策(建议,待确认)**:**不做**方案里的大重构(现有 `predictors/ml`、`benchmarks/` 布局能跑、203 tests 绿)。按现结构**增量加** `io/` + `praxis_vc_api/` + `praxis_vc_web/` + CLI,降风险。`predictors/donor|gears|cpa` 重排 = 可选后续,非本次。

## ✅ 决策已定(2026-07-02:增量不重构 · 直推 MVP · 真调 DeepSeek 已验证)+ 原决策记录

> **MVP 已交付**:package(P1)+ FastAPI(P2)+ Streamlit(P3);221 passed;真调 DeepSeek 解析验证通过;见 `docs/USAGE-llm-interface.md`。

### 原决策待确认(开工前)
1. **包结构**:增量加(推荐,不重构)vs 按方案重排 `predictors/donor|gears|...`。
2. **v0.1 网页**:Streamlit(方案已定)。
3. **MVP 范围**:Phase 1+2+3(package→API→Streamlit)一次到 MVP,还是先 Phase 1(LLM 外层 + 统一 workflow + CLI `ask`)交付再往上。
4. **LLM 真调用**:Phase 1 默认离线 + fallback 测试;是否要我用 .env 里 DeepSeek key 真连一次验证解析(会产生 token 调用)。

---

## Phase 1 ✅ — LLM 外层 + 统一 query workflow(纯 Python,TDD,无网络依赖)

### - [ ] P1.1 — config 安全 flag + 边界断言
- `core/config.py` 加 `allow_llm_to_modify_core_decision/_prediction/_override_hard_rules: bool = False`(注释:永为 False)。加一处启动断言/常量守卫,任何路径不得置 True。
- 验收:`test_llm_boundary_flags_always_false`。

### - [ ] P1.2 — LLMClient 补强(不抛 + hash + 可选 json)
- `agents_llm/llm_client.py`:确认 `complete()` 不抛、失败返 error、temp=0、json_mode 可选(已基本有);**加** provider/model/temperature/prompt_hash/response_hash/schema_valid/fallback_used 元数据返回(不存 key/原文敏感)。
- 验收:`test_llm_client_no_key_returns_error`、`test_llm_assisted_mode_records_prompt_hash`。

### - [ ] P1.3 — LLMInputInterpreter + deterministic validator
- `llm_input_interpreter.py`:自然语言 → **JSON**(species/cell_type/perturbation{type,targets}/task/requested_outputs/confidence/missing_fields/assumptions)。prompt 抽 `prompts/input_interpreter.md`。
- **validator**(pydantic/dataclass):species∈支持集、perturbation type∈白名单、targets 非空且归一、task∈允许、outputs∈白名单;非法→fallback deterministic parser→仍失败→`clarification_required`(结构化缺失字段,**不让 LLM 追问用户**)。
- 验收:`test_llm_parser_schema_validation`、`test_llm_input_parser_fallback`、`test_natural_language_to_confirmed_request`。

### - [ ] P1.4 — LLMRouter(仅建议)+ LLMCritic(仅文本)+ LLMReport(仅叙述)补强
- router:只输出 suggested_task_type/suggested_agents/risk_flags/rationale,**禁** final_model/final_decision/prediction;写入 provenance 的 `llm_router_suggestion`。最终路由仍走 SpeciesBrain→ModelApplicability→assess_applicability。
- critic:输入 structured report+provenance+deterministic critic 结果,只输出 issues/suggested_edits(overclaim/per-cell 混淆/OOD 冒充等),**不改数值/决策**。
- report:输入结构化报告→人类可读叙述,**不得**新增结论/隐藏 abstain-downgrade/删 uncertainty/把 hypothesis 写成 conclusion。
- 验收:`test_llm_router_cannot_set_final_route`、`test_llm_critic_cannot_modify_decision`、`test_llm_report_cannot_modify_prediction`、`test_llm_overclaim_detected_by_critic`。

### - [ ] P1.5 — 统一 `run_virtualcell_query` workflow
- `workflows/run_virtualcell_query.py`:text →(LLM interpret + validator)→ candidate_request →(确认接口)→ VirtualCellRequest → 现有 runtime → structured report →(可选 LLMReport)→ {structured, narrative, trace, provenance, llm_metadata}。
- 冲突规则:LLM vs deterministic 冲突 → **deterministic wins** + provenance 记冲突 + critic warning。
- 验收:`test_offline_mode_never_calls_llm`、`test_confirmed_request_to_runtime_job`、`test_runtime_job_report_contains_llm_metadata`、`test_no_api_key_full_fallback`。

### - [ ] P1.6 — io/job_store + CLI `run`/`ask`
- `io/job_store.py`:runs/<job_id>/{request,candidate_request,trace,report,narrative_report,provenance,llm/*hash}.
- pyproject `[project.scripts]` `praxis-vc`:`run --request ... --mode offline`、`ask --text ... --mode llm-assisted`。
- 验收:CLI 冒烟(offline 无 LLM;ask 无 key→fallback)。

### - [ ] P1.7 — Golden tests(10 自然语言输入)
- human K562 KO / human drug / mouse ortholog / bacteria KO / 不支持物种 / 空 targets / 模糊 cell type / 临床越界 / drug+gene 混合 / 机制 overclaim。
- 每条验:parsed 正确 / fallback 正确 / hard rule 保留 / report 不 overclaim。

---

## Phase 2 ✅ — FastAPI 本地服务(`praxis_vc_api/`)

### - [ ] P2.1 — FastAPI 骨架 + endpoints
- `main.py` + routes:`GET /api/health`、`POST /api/parse`、`POST /api/jobs`、`GET /api/jobs/{id}`、`GET /api/reports/{id}`、`/trace`、`/provenance`。
- services:runtime_service(调 workflow)/ llm_service / job_service(job_store)。pydantic api_schema。
- 依赖:fastapi/uvicorn/pydantic(+ sqlite/duckdb 可选)。加 `[project.optional-dependencies] api`。
- 验收:`GET /health` 返 mode/llm_enabled/version;parse→jobs→reports 全链本地跑通;offline 无 LLM。

## Phase 3 ✅ — Streamlit 本地网页(`praxis_vc_web/`)

### - [ ] P3.1 — 5 页
- Ask(文本+模式选择+Confirm)/ Parsed Request(可改)/ Running Trace(逐 agent status)/ Report(4 块 + 可选 narrative,标注"LLM 未改预测/治理")/ Provenance(version/artifact_sha/fallback/prompt-hash/trace 下载)。
- CLI `serve`/`web`。验收:科学家不写 JSON 也能完成一次查询。

## Phase 4 — React 正式网页(Streamlit 稳定后)
- React/Vite + FastAPI;多 job 管理、报告导出、trace 可视化。

---

## 决策边界(写进代码 + 文档)
- LLM **可**影响:candidate_request / router_suggestion / critic_notes / narrative_report。
- LLM **不可**影响:validated_request / hard_rule_decision / prediction / learned_reliability_score / abstain_decision / artifact validation / provenance truth。
- 冲突:deterministic wins;记 provenance;critic warning。

## 安全
- `.env.example`:PRAXIS_MODE=offline / PRAXIS_LLM_ENABLED=false / DEEPSEEK_*。`.gitignore` 含 `.env`/`*.key`/`secrets/`/`runs/*/llm/raw*`。LLM 调用只存 hash,不存 key/原始 prompt 敏感内容。

## 论文口径
> All benchmark/prediction/reliability/abstention results were generated in offline deterministic mode without LLM calls. The optional LLM-assisted interface (parsing / routing suggestion / critic review / report narration) is outside the predictive core and cannot override rule-based or learned reliability decisions.

## MVP(交付定义)
package 可装 · FastAPI 可启 · Streamlit 可用 · 自然语言→VirtualCellRequest · 用户可确认/改 · runtime 离线执行 · LLM report 可选 · provenance 记 LLM 是否用 · 无 key 完整 fallback · 测试证明 LLM 不影响预测/治理。
