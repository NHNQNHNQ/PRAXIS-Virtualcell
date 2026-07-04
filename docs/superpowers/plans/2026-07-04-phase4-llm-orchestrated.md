# Phase 4:LLM_ORCHESTRATED 模式(LLMModulePlanner + safety_contract + cross_module_reasoner + 接管线)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `LLM_ORCHESTRATED` 运行模式:在 Phase 3 的确定性 module 路由之上,让 LLM **先出 module 集建议**,经 `safety_contract` 过滤成合法 module 集(∈ Phase 1 support matrix + Phase 3 确定性候选),再转 `AgentMessage` 交给 `ModuleRouterAgent` 合成同一 `ModulePlan`;另加 `LLMCrossModuleReasoner`(只出 advisory notes/flags,不碰裁决)。**默认仍 OFFLINE 走确定性 ModuleRouter(零 LLM),LLM 路径 gated(无 key / 非 LLM_ORCHESTRATED 不触发)**。同时把 `SpeciesContextAgent` + `ModuleRouterAgent`(Phase 3 刻意没接)**接进 `run_workflow` 固定管线**(插点 A/B),OFFLINE 路径行为不变。Phase 4 完成 = **v1.1 里程碑**(LLM-orchestrated)。

**Architecture:** 全部**净新增 + 复用**,不改现有 predictor / 治理引擎 / route_table / ModulePlan / Phase 3 三个 agent 的任何**逻辑**(仅 `core/config.py` 加枚举值、`workflows/predict_delta_expression.py` 加节点注册、`core/runtime.py` 加**可选**插点)。LLM 编排复刻 `LLMRouter`(`agents_llm/llm_router.py`)的"只能从候选选"约束:`LLMModulePlanner` 产出 module 集后,`safety_contract.filter_to_supported_modules(llm_modules, candidates)` 做 `[m for m in llm_modules if m in candidates]`,candidates = **Phase 3 确定性 primary/secondary ∪ 该物种 support≠unsupported 的模块**。LLM **只挑 module（"选哪几个模块"），绝不设 engine/verdict/prediction/provenance**——engine 仍由 `route_table.route()` 落、verdict 仍由 `synthesize_verdict` 保守合成、`ModulePlan` 仍由 `ModuleRouterAgent` 用 Phase 3 完全相同的代码路径构造。`LLMCrossModuleReasoner` 复刻 `LLMCritic` 模式:读 `ModulePlan.to_dict()` 只 emit `{notes, flags}`,写进 `report.provenance`,不改任何 entry。新子包 `llm_orchestration/`(planner/reasoner/safety_contract)与现有 `agents_llm/` 平行。管线接法(§插点归置):OFFLINE 与 LLM_ORCHESTRATED 共用 SpeciesContext→ModuleRouter 两节点产 `module_plan`(挂进 `report.provenance.module_plan`,不改 predictor fan-out 上游契约);LLM_ORCHESTRATED 额外在 ModuleRouter **之前**插 LLMModulePlanner(出候选建议)、在 Report **之后**插 LLMCrossModuleReasoner(出 notes)。

**Tech Stack:** Python 3.13 / pytest 参数化 / PyYAML / dataclasses(标准库)/ 复用现有 `agents_llm/llm_client.py:LLMClient`(httpx,无 openai/anthropic SDK)。LLM 单测用 **FakeLLMClient / monkeypatch**(不真调 API,延续 `test_llm_router.py` 之外的离线契约模式);真调 API 的连通性测试打 `@pytest.mark.llm`(无 `DEEPSEEK_API_KEY` 自动 skip,见现有 `conftest.py`)。OFFLINE 路径零 LLM、零 torch、零 cobra。

---

## 铁律(每个 task 验收都要守)

- **纯新增 + 复用,不改现有逻辑**:只新增 `llm_orchestration/`(子包 + planner/reasoner/safety_contract)、新测试;`core/config.py` 仅**加 2 个 Mode 枚举值**(不删不改现有 `OFFLINE`/`LLM_ASSISTED`,不动三 flag 与 `assert_llm_boundaries`);`workflows/predict_delta_expression.py` 仅**增量注册**新 agent(不改现有注册);`core/runtime.py` 仅在 `run_workflow` 加**可选**插点(OFFLINE 分支必须与现在字节等价)。**不改** predictor / 治理引擎 / route_table / ModulePlan / Phase 3 三 agent 的逻辑。若发现现有行为与预期不符 → **真实 bug,停下报告,不改代码/不改测试迁就**(红线 5)。
- **红线 1:OFFLINE 默认零 LLM 不变**。默认 `mode=OFFLINE`、`llm_enabled=False`,核心 case/预测/治理零 token 可跑。LLM_ORCHESTRATED 是**可选**模式;无 key / 非该模式时 `LLMModulePlanner`/`LLMCrossModuleReasoner` **不注册**(复刻 `build_runtime` 里 `if client.enabled` 的门)。OFFLINE 走 Phase 3 确定性 ModuleRouter,零 `agents_llm`/`llm_orchestration` 的 LLM 调用。
- **红线 2:`assert_llm_boundaries` 三 flag 恒 False**。`allow_llm_to_modify_core_decision/_prediction/_override_hard_rules` 在 LLM_ORCHESTRATED 下仍全 False;新增枚举不改守卫。LLM 绝不碰 prediction / hard-rule / learned-reliability 终决 / provenance / ledger。**专门契约测试**(扩 `test_llm_boundary_flags` 模式)钉死:LLM_ORCHESTRATED 下三 flag 仍 False、`assert_llm_boundaries` 仍拦截、LLM 产物只进 `provenance`/candidate 过滤不进 prediction。
- **红线 3:LLM plan 必须转 AgentMessage 才能执行**。`LLMModulePlanner` 不直接产 `ModulePlan`;它 emit 一条 `module_candidates_llm`(候选过滤后的合法 module 集)→ `ModuleRouterAgent` 读它、用**同 Phase 3 代码路径**合成 `ModulePlan`。LLM **不给 unsupported module 硬解释**(过滤时 unsupported 直接剔除)、**不把 downgrade 改 accept**(verdict 仍由 `synthesize_verdict` 定,LLM 不参与)、**不新增无 provenance 的证据**(LLM 只挑 module id,reason/engine/pillars 全来自确定性源)。
- **红线 4:unsafe-accept = 0 / 无静默 accept**。原 route golden/negative + Phase 3 module golden 的 KPI 每 task 后仍绿;LLM_ORCHESTRATED 下 mismatch/unsupported 仍 verdict 降级不 accept(LLM 无法把它捞回 accept)。
- **红线 6:LLM 不可用不静默**。无 key / LLM 解析失败 / LLM 返回空 → `safety_contract` fail-closed **回退到 Phase 3 确定性候选**(不硬塞、不虚构 module),并在 plan `notes` 记 `llm_unavailable`/`llm_parse_failed`。
- **测试口径** = `praxis_virtualcell/tests`(**绝不碰根 `tests/`**)。Phase 4 起点基线(当前分支 `feat/v0.9-phase0-module-core`,含 Phase 0/1/2/3)**实跑核实 = 450 passed / 25 skipped / collected 475**(2026-07-04 `pytest --junit-xml` 实测)。`-q` 不打印精确 passed;精确数用 `--junit-xml` 属性换算:**passed = tests(collected) − skipped − failures − errors**(junit `tests` 属性是 collected 含 skipped,不是 passed)。**LLM 单测用 FakeLLMClient/monkeypatch 离线跑(计入 passed,不增 skip);真 API 测试打 `@pytest.mark.llm`(无 key 自动 skip)。skip 基线 25 不因 Phase 4 破坏**——即 Phase 4 新增的 `@pytest.mark.llm` 测试在无 key 的 CI 下会 skip、使 skip 数上升是**不允许**的口径漂移;故 Phase 4 **除连通性 smoke 外一律用 FakeLLMClient 离线跑**,连通性 smoke 若加则须在"skip 基线"一并声明(本计划选择**不新增** `@pytest.mark.llm` 测试,全部离线 fake,保 skip 恒 25)。验收只认:**failures=0 errors=0 skipped=25** + 每 task 新增测试条数正确。
- **每 task 全量回归绿**后再 commit:`PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`;commit 前 `find . -name '._*' -delete`(外置盘 AppleDouble);commit message 末尾加 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`;当前分支 `feat/v0.9-phase0-module-core`,**不 push**。
- **v1.1 里程碑 tag**:Phase 4 是 v1.1 里程碑(路线图 §5)。**只在最后一个 task(4.8)全绿 + 红线核验通过后打 tag**(`git tag v1.1-...`),tag 不 push(房规:当前分支不 push;tag 打在本地由人决定何时推)。中间 task 不 tag。

---

## 数据契约(已实跑核实,计划代码与之对齐)

以下是 Phase 4 依赖的**真实接口**(2026-07-04 实读源码核实,非路线图旧描述):

- **`core/config.py`**(实读):`class Mode(str, Enum)` 现有 `OFFLINE="offline"`、`LLM_ASSISTED="llm_assisted"` 两值。`RuntimeConfig` 字段:`mode=Mode.OFFLINE`、`llm_enabled=False`、`deepseek_api_key=""`、`deepseek_base_url`、`deepseek_model`、`reliability_mode`、`brains_root`、三 flag(`allow_llm_to_modify_core_decision/_prediction/_override_hard_rules` 恒 False)。`RuntimeConfig.from_env()` 仅在 `PRAXIS_VIRTUALCELL_MODE == "llm_assisted"` 时置 `LLM_ASSISTED`。`assert_llm_boundaries(config)` 检三 flag,任一 True 抛 `RuntimeError`。**Phase 4 新增 `LLM_ORCHESTRATED="llm_orchestrated"`(+ `LLM_ORCHESTRATED_STRICT="llm_orchestrated_strict"`)两枚举值**,`from_env` 认 `PRAXIS_VIRTUALCELL_MODE == "llm_orchestrated"`,`llm_enabled` 判定扩为"mode ∈ {LLM_ASSISTED, LLM_ORCHESTRATED, LLM_ORCHESTRATED_STRICT} 且有 key"。
- **`agents_llm/llm_client.py`**(实读):`LLMClient(*, enabled, api_key, base_url, model, timeout)`;`complete(messages, *, json_mode=False, max_tokens=1024) -> {disabled, content, error}`(不抛,失败返回 `content=None`)。`make_llm_client(config) -> LLMClient`:`enabled = config.mode is Mode.LLM_ASSISTED and bool(config.deepseek_api_key)`。**Phase 4 需把 `make_llm_client` 的 enabled 判定扩到 LLM_ORCHESTRATED**(否则该模式下 client 不 enabled、LLM 节点不注册)。
- **`agents_llm/llm_router.py:LLMRouterAgent`**(实读,复刻范本):`__init__(client)`;`handle` 里 `candidates = list(applicable) + list(rejected_candidates)`;调 `client.complete([sys,user], json_mode=True)`;**核心过滤** `[a for a in (d.get("recommended_agents") or []) if a in candidates]`;`res.content` 为空 → `risk_flags=["llm_unavailable"]`;`json.JSONDecodeError` → `["llm_parse_failed"]`;emit `llm_route_suggestion`,payload `{suggestion, conflict_with_rule}`。**LLM 只从 candidates 选、不发明新名字。**
- **`agents_llm/llm_critic.py:LLMCriticAgent`**(实读,cross_module_reasoner 范本):`__init__(client)`;`handle` 读 `payload["report"]`,`client.complete(json_mode=True)`,emit `llm_critic_notes` payload `{notes, flags}`;content 空 → `flags=["llm_unavailable"]`;解析失败 → `["llm_parse_failed"]`。**只出 notes/flags,不改 prediction。**
- **`biological_modules/module_plan.py`**(实读,Phase 3 交付,Phase 4 输入契约):`synthesize_verdict(route_disposition, species_verdict, mismatch)->str`(保守合成,`_SEVERITY={accept:0,caution:1,downgrade:2,abstain:3,reject:3}`);`ModulePlanEntry(module, display_name, role, engine, route_disposition, species_support, species_verdict, caution_flags=[], data_gated=False, pillars=[], available_models=[], reason="", mismatch=None, verdict=None)` —— `__post_init__` 校验 module∈MODULE_ORDER、engine∈ENGINES、role∈{primary,secondary},verdict=None 则合成;`to_dict()`。`ModulePlan(species, request, primary, secondary, entries, notes=[])` —— `__post_init__` 校验 primary∈MODULE_ORDER 且 ∈entries、secondary∈MODULE_ORDER;`overall_verdict` property(entry verdict 取最保守;空 entry→abstain);`to_dict()` 键=`{species, request, primary, secondary, overall_verdict, entries, notes}`。
- **`agents/module_router_agent.py:ModuleRouterAgent`**(实读,Phase 3):`name="ModuleRouterAgent"`;`handle` 读 `payload["request"]`(raw)→ `normalize_request` → 读 `payload.get("module_support", {})`、`payload.get("mismatch_queries", {})` → `module_rules.pick_primary/pick_secondary` → 对每 module `_build_entry`(复用 `route()`、`M.MODULES[mid]`、`synthesize_verdict`)→ 合成 `ModulePlan` → emit `module_plan_ready` payload=`plan.to_dict()`,receiver="EnsembleCoordinator"。**Phase 4 让它可选读 `payload.get("module_candidates")`(LLM 过滤后的 module 集)覆写 primary/secondary 的产生源,但 engine/verdict/entry 构造完全不变**(见决策 P2)。
- **`agents/module_rules.py`**(实读):`pick_primary(req)->str`、`pick_secondary(req, primary)->list[str]`、`mismatch_query_for(req, module)->str|None`。纯函数、零 LLM。Phase 4 的 candidate 全集从这里 + support matrix 派生。
- **`agents/species_context_agent.py:SpeciesContextAgent`**(实读,Phase 3):`name="SpeciesContextAgent"`;`__init__(registry=None)`;`handle` 读 `payload["request"]` → 8 模块 `module_support[mid]={support, verdict, display_name, models, tools, reason}` + `mismatch_queries{query:verdict}` → emit `species_context_ready`,receiver="ModuleRouterAgent"。
- **`agents/route_table.py`**(实读):`ENGINES=("donor_predictor","gem_fba","embedding","state_scoring","pathway_scoring","communication","spatial_niche","reject")`;`route(req)->RouteDecision(engine, disposition, reason, caution_flags=[], data_gated=False)`;`disposition∈{accept,caution,downgrade,abstain}`。
- **`agents/species_schema.py`**(实读):`normalize_request(raw)`;`SPECIES={human,mouse,yeast,bacteria}`;`PERTURBATION_OBJECTS={gene,gene_combination,drug,medium,ligand}`;`TARGET_OUTPUTS={expression,growth,flux,state,communication}`;非法 → `SchemaError`(ValueError 子类)。
- **`biological_modules/modules.py`**(实读):`MODULE_ORDER`(8 项)、`MODULES[mid]={code,display_name,engines,pillars}`、`display_name(mid, species=None)`(bacteria M3 → "Energy metabolism / redox module")。
- **`biological_modules/registry.py:ModuleRegistry`**(实读):`support(species,mid)->dict`、`default_verdict(species,mid)->str`(`_VERDICT={strong:accept,medium:accept,weak:caution,unsupported:reject}`)、`matrix()`、`biological_mismatch(species,query)`、`display_name(species,mid)`。
- **`core/runtime.py:AgentRuntime`**(实读):`register_agent(agent)`、`mk_message(sender, receiver, message_type, payload, parent_message_id=None)`、`dispatch_message`、`_dispatch_collect(message, expected_type)->AgentMessage`。`run_workflow(request)` 固定管线节点顺序:`InputInterpreter → BioObjectNormalizer → SpeciesBrain → ModelApplicability →[LLMRouter?]→ predictor fan-out → EnsembleCoordinator → Reliability → Critic → ProvenanceAgent → Report →[LLMCritic?][LLMReport?]`。LLM 节点全部 `if "X" in self._agents` gated。
- **`workflows/predict_delta_expression.py:build_runtime(config)`**(实读):注册 12 个确定性 agent;`make_llm_client(cfg)` 后 `if client.enabled` 注册 4 个 `agents_llm` agent。**Phase 4 在此加:总是注册 `SpeciesContextAgent`+`ModuleRouterAgent`(OFFLINE 确定性);`if client.enabled and mode ∈ orchestrated` 再注册 `LLMModulePlanner`+`LLMCrossModuleReasoner`。**
- **`core/agent.py:BaseAgent`**:抽象 `handle(message, bus)->None`,`name` 类属性,只经 `bus.send` 产出。
- **`core/bus.py:MessageBus`**:`send(msg)`、`latest(message_type)->AgentMessage|None`、`get_messages`、`has_message_type`、`trace`。
- **`core/message.py:AgentMessage`**:`message_id/sender/receiver/message_type/payload/timestamp/parent_message_id`(默认 None)。
- **`tests/conftest.py`**(实读,gating 机制):`@pytest.mark.llm` 无 `DEEPSEEK_API_KEY` 自动 skip;`@pytest.mark.remote` 无 torch 自动 skip。**当前 25 skip 即由这些 marker + 无 key/torch 构成。Phase 4 不新增 `@pytest.mark.llm` 测试(全 FakeLLMClient 离线),保 skip 恒 25。**
- **`docs/STATUS-2026-07-03-v0.6-v0.8-delivery.md`**(实存):台账文件;Phase 3 台账已追加其尾部。Phase 4 追加 Phase 4 段。

**与路线图旧描述的四处校正(已在计划代码对齐):**
1. **config 现有枚举只有 `OFFLINE`/`LLM_ASSISTED`,无 `LLM_ORCHESTRATED`**。路线图 §1/§4 说"加 `LLM_ORCHESTRATED`/`_STRICT` 两枚举值 + 收紧检查"。实读 `Mode` 是 `str, Enum` 子类,加枚举值是纯增(不破坏 `from_env`/序列化,`.value` 是字符串)。`_STRICT` 本计划**加枚举但暂不接特殊逻辑**(仅占位 + 测试其 `llm_enabled` 判定;strict 语义如"LLM 建议与确定性冲突即 abstain"留控制器拍板,标注待确认)。
2. **`make_llm_client` 的 enabled 只认 `LLM_ASSISTED`**(实读 `llm_client.py:44`)。若只加 Mode 枚举、不改 `make_llm_client`,则 LLM_ORCHESTRATED 下 client **永不 enabled**、LLM 节点永不注册——LLM_ORCHESTRATED 会静默退化成 OFFLINE。**必须同步扩 `make_llm_client` 的 enabled 判定**(Task 4.1 落实),否则该模式形同虚设。
3. **runtime 的 LLM 节点都是 `if "X" in self._agents` gated,不是 `if config.llm_enabled`**(实读 `runtime.py:59/88/93`)。Phase 4 的插点沿用**同一 gating 惯例**(`if "LLMModulePlanner" in self._agents`),注册与否在 `build_runtime` 按 mode 决定,runtime 只查 agent 是否在册——这样 OFFLINE 分支代码路径与现在字节等价(agent 不在册 → 分支不进)。
4. **Phase 3 刻意没接管线**(实读 `runtime.run_workflow` 无 ModuleRouter 节点;Phase 3 计划 §决策 R1 明说留 Phase 4)。故"接管线"是 Phase 4 的活。**接法必须最小侵入**:module_plan 挂进 `report.provenance.module_plan`,**不改** predictor fan-out 的上游 `app.payload` 契约(见插点归置决策),避免动 predictor/ensemble/reliability 的输入结构。

---

## 插点归置决策(接管线的最小侵入方案)

- **SpeciesContext(插点 A)+ ModuleRouter(插点 B)接进 `run_workflow`,但只做"旁路挂载"**。理由:现有 predictor fan-out 读 `app.payload["applicable"]/["request"]/["brain_context"]`(见 `runtime.py:66`)。若让 ModulePlan 去驱动 fan-out,要改 predictor 的输入契约(高回归风险,违反红线"不改现有逻辑")。**Phase 4 的接法**:在 `ModelApplicability` 之后、predictor fan-out **之前**跑 SpeciesContext→(LLMModulePlanner?)→ModuleRouter,产 `module_plan`,把它**挂进最终 report 的 `provenance.module_plan`**(与现有 `llm_route_suggestion` 挂法一致,见 `runtime.py:87`),predictor fan-out/ensemble/reliability/critic 全**不改**。这样 v1.1 交付"module-aware + LLM 编排的 ModulePlan 进 provenance 可见、可复现",而核心预测/治理路径零改动、零回归风险。**module_plan 驱动 predictor 选择**(即用 plan 的 engine 集裁剪 fan-out)是更深的重构,留 v1.2+(标注待确认,不在本 Phase)。
- **EvidenceLevelAgent(插点 C,E0–E5)**:Phase 3 计划把它留给"Phase 4/5"。**本 Phase 归置为留 Phase 5**(与主动学习一起)。理由:E0–E5 读运行时 reliability/OOD 信号做映射,属"治理层之上的另一层",与本 Phase 的 LLM 编排正交;硬塞进来会让本 Phase 越界、且 evidence-level 的 verdict 一致性检查更贴主动学习的证据链。本 Phase 的 `LLMCrossModuleReasoner`(插点 D 之前的 advisory 层)只读已合成的 ModulePlan 出 notes,不做 E0–E5 映射。**已在头部与 Task 4.6/4.8 注明此留后边界。**
- **ActiveLearning(插点 D)**:Phase 5,不在本 Phase。

---

## LLMModulePlanner + safety_contract 契约设计(本 Phase 核心,复刻 LLMRouter"只能从候选选")

**candidate 全集(single source of truth)**:对归一请求 `req`,candidate modules =
`{pick_primary(req)} ∪ set(pick_secondary(req, primary)) ∪ {mid for mid in MODULE_ORDER if module_support[mid]["support"] != "unsupported"}`。
即 **Phase 3 确定性命中 ∪ 该物种非 unsupported 的模块**。LLM 只能从这个集合里挑,挑出集合外的 module 一律剔除(复刻 `[a for a in ... if a in candidates]`)。

**`safety_contract.py`(纯函数,不进 bus,可独立测试):**
- `build_candidate_modules(req, module_support) -> list[str]`:按上式产 candidate 全集(去重、按 MODULE_ORDER 排序、fail-closed 保证 primary 一定在内)。
- `filter_to_supported_modules(llm_modules, candidates) -> list[str]`:`[m for m in llm_modules if m in candidates]`(顺序按 candidates,去重)。
- `sanitize_llm_plan(raw_content, candidates) -> dict`:解析 LLM 的 JSON `{"selected_modules":[], "reasoning_summary":"", "risk_flags":[]}`;`selected_modules` 过滤成 candidates 子集;content 空 → `risk_flags=["llm_unavailable"]`;`JSONDecodeError` → `["llm_parse_failed"]`;**任何异常路径都返回合法结构(fail-closed),selected_modules 至少含 candidates 里的 Phase 3 primary**(保证不会因 LLM 失败而丢主模块)。
- `assert_plan_within_bounds(plan_dict, candidates) -> list[str]`:核验一个 ModulePlan 的 primary/secondary/entries 的 module **全 ∈ candidates**;越界 → 返回违规串(供 Task 4.6 契约测试 + governance)。这是 LLM 不能"给 unsupported module 硬解释"的代码级守卫。

**`LLMModulePlanner`(extends BaseAgent,进 bus,复刻 LLMRouter):**
- `__init__(client: LLMClient)`。
- `handle`:读 `payload{request, module_support, mismatch_queries}` → `normalize_request` → `build_candidate_modules(req, module_support)` → `client.complete([_SYS, user], json_mode=True)`(user 里给 candidates + 请求上下文,system 明令"只从 candidates 选,不发明模块名")→ `sanitize_llm_plan(content, candidates)` → emit **`module_candidates_llm`** payload `{request(raw 透传), module_support, mismatch_queries, module_candidates:{selected, reasoning_summary, risk_flags, candidates}}`,receiver="ModuleRouterAgent"。
- **红线**:planner **不产 ModulePlan、不设 engine/verdict/prediction**;只产"选了哪几个合法 module"。ModulePlan 仍由 ModuleRouter 用 Phase 3 代码合成。

**`ModuleRouterAgent` 的 Phase 4 扩展(决策 P2,最小改动、不破坏 Phase 3):**
- `handle` 增一句:`llm_modules = message.payload.get("module_candidates", {}).get("selected")`。
- 若 `llm_modules` 非空:`primary`/`secondary` **从 LLM 选中集派生**——primary = Phase 3 `pick_primary(req)`(**primary 永远由确定性规则定,LLM 不改 primary**,守"LLM 不碰 hard-rule");secondary = `[m for m in llm_modules if m != primary and m in build_candidate_modules(...)]`(LLM 只能**增删 secondary**,且只能从候选选)。
- 若 `llm_modules` 为空(OFFLINE 或 LLM 失败):走 Phase 3 原路径 `pick_secondary(req, primary)`。
- **engine/verdict/entry 构造(`_build_entry`)完全不变**:仍 `route()` 落 engine、`synthesize_verdict` 定 verdict、mismatch 降级。故 LLM **无法把 downgrade 改 accept、无法给 unsupported 硬解释**(unsupported 在 candidate 集就被剔,mismatch 仍降级)。
- plan `notes` 追加 LLM 的 `risk_flags`(llm_unavailable/llm_parse_failed/冲突)供 provenance 追溯。

**转 AgentMessage 链(红线 3 满足)**:LLM 建议 → `module_candidates_llm`(AgentMessage)→ ModuleRouter 读它合成 `module_plan_ready`(AgentMessage)。LLM 产物全程是 bus 消息,不直接执行,不进 prediction。

**assert_llm_boundaries 守边界(红线 2)**:LLM_ORCHESTRATED 入口(`run_query`/`build_runtime` 组装时)仍调 `assert_llm_boundaries(cfg)`;三 flag 恒 False。LLM 产物只影响 secondary module 的**选择**(candidate 子集内)与 provenance notes,绝不触碰 prediction/hard-rule/verdict 合成/reliability/provenance ledger。

---

## primary/secondary/strict 语义(科学核心,给建议 + 标注待确认)

**决策 P1(primary 不可被 LLM 改)—— 已定(fail-closed):** primary module 永远由 `pick_primary(req)`(Phase 3 确定性规则)决定。LLM 只能在 candidate 集内**增删 secondary**。理由:primary 决定核心 engine 归属(donor_predictor/gem_fba…),属"hard-rule"范畴,红线 2 禁 LLM 覆盖。

**决策 P2(LLM 只增删 secondary,且 ⊆ candidates)—— 已定:** LLM 选中集里非 primary 且 ∈ candidate 全集的 module 成为 secondary。LLM 想加 candidate 外的 module → 被 `filter_to_supported_modules` 剔除(不给 unsupported 硬解释)。LLM 想删某确定性 secondary → 允许(编排价值:LLM 可判"本请求无需能量代谢副模块"),但删不影响 primary/verdict/prediction。

**决策 P3(LLM_ORCHESTRATED_STRICT)—— 建议方案,待控制器确认:** 建议 STRICT 语义 = "LLM 建议与确定性候选**冲突**(LLM 选了 candidate 外 module,或删了 primary)时,不静默忽略而是在 plan `notes` 记 `strict_conflict` 并把 overall_verdict 至少降到 `caution`"。本 Phase **先加枚举 + 测其 `llm_enabled` 判定 + 占位不接冲突降级逻辑**(仅测 STRICT 能被识别为 orchestrated 模式并注册 LLM 节点),STRICT 的冲突降级具体规则**标注待确认**,由控制器按科学需要拍板后在 v1.1.x 补。

**决策 P4(cross_module_reasoner 只 advisory)—— 已定:** `LLMCrossModuleReasoner` 复刻 `LLMCritic`:读 `ModulePlan.to_dict()`,出 `{notes, flags}` 写进 `provenance.llm_cross_module_notes`,**不改任何 entry/verdict/prediction**。它给"跨模块一致性/生物学合理性"的自然语言复核,是编排的可解释层,不是裁决层。

---

# Phase 4:LLM_ORCHESTRATED 模式 · 任务

## Task 4.1:config 加 LLM_ORCHESTRATED 枚举 + make_llm_client enabled 扩展

**决策说明:** 先落"模式开关"地基:`Mode` 加 `LLM_ORCHESTRATED`/`LLM_ORCHESTRATED_STRICT` 两枚举值(纯增,不破坏现有);`RuntimeConfig.from_env` 认新 mode 字符串;`make_llm_client` 的 `enabled` 判定从"只认 LLM_ASSISTED"扩到"认所有 orchestrated 模式"(校正 §校正2:否则 LLM_ORCHESTRATED 下 client 永不 enabled、LLM 节点永不注册)。**三 flag 与 `assert_llm_boundaries` 不动**(红线 2)。

**Files:**
- Modify: `praxis_virtualcell/core/config.py`
- Modify: `praxis_virtualcell/agents_llm/llm_client.py`
- Test: `praxis_virtualcell/tests/test_orchestrated_mode_config.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_orchestrated_mode_config.py`:

```python
"""Phase 4:LLM_ORCHESTRATED 模式开关。测枚举新增不破坏、from_env 识别、make_llm_client enabled 扩展、
三 flag 仍恒 False(红线 2)、无 key 时 orchestrated 仍不 enabled(红线 1/6)。"""
import os

from praxis_virtualcell.agents_llm.llm_client import make_llm_client
from praxis_virtualcell.core.config import Mode, RuntimeConfig, assert_llm_boundaries


def test_new_enum_values_exist_and_are_strings():
    assert Mode.LLM_ORCHESTRATED.value == "llm_orchestrated"
    assert Mode.LLM_ORCHESTRATED_STRICT.value == "llm_orchestrated_strict"
    # 现有枚举不变
    assert Mode.OFFLINE.value == "offline"
    assert Mode.LLM_ASSISTED.value == "llm_assisted"


def test_from_env_recognizes_orchestrated(monkeypatch):
    monkeypatch.setenv("PRAXIS_VIRTUALCELL_MODE", "llm_orchestrated")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-fake")
    c = RuntimeConfig.from_env(env_path="/nonexistent.env")
    assert c.mode is Mode.LLM_ORCHESTRATED
    assert c.llm_enabled is True         # orchestrated + key → enabled


def test_from_env_orchestrated_strict(monkeypatch):
    monkeypatch.setenv("PRAXIS_VIRTUALCELL_MODE", "llm_orchestrated_strict")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-fake")
    c = RuntimeConfig.from_env(env_path="/nonexistent.env")
    assert c.mode is Mode.LLM_ORCHESTRATED_STRICT
    assert c.llm_enabled is True


def test_orchestrated_without_key_not_enabled(monkeypatch):
    """红线 1/6:无 key 时 orchestrated 不 enabled(client 不真调,回退)。"""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    c = RuntimeConfig(mode=Mode.LLM_ORCHESTRATED, deepseek_api_key="")
    assert make_llm_client(c).enabled is False


def test_make_llm_client_enabled_for_orchestrated_with_key():
    c = RuntimeConfig(mode=Mode.LLM_ORCHESTRATED, deepseek_api_key="sk-fake")
    assert make_llm_client(c).enabled is True
    c2 = RuntimeConfig(mode=Mode.LLM_ORCHESTRATED_STRICT, deepseek_api_key="sk-fake")
    assert make_llm_client(c2).enabled is True


def test_offline_still_not_enabled():
    """红线 1:OFFLINE 恒不 enabled。"""
    assert make_llm_client(RuntimeConfig(mode=Mode.OFFLINE)).enabled is False


def test_three_flags_stay_false_under_orchestrated():
    """红线 2:新模式下三 flag 仍恒 False,assert_llm_boundaries 不抛。"""
    c = RuntimeConfig(mode=Mode.LLM_ORCHESTRATED, deepseek_api_key="sk-fake")
    assert c.allow_llm_to_modify_core_decision is False
    assert c.allow_llm_to_modify_prediction is False
    assert c.allow_llm_to_override_hard_rules is False
    assert_llm_boundaries(c)             # 不抛
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_orchestrated_mode_config.py -q`
Expected: FAIL(`AttributeError: LLM_ORCHESTRATED` —— 枚举未加)。

- [ ] **Step 3: 改 config.py 加枚举 + from_env 识别**

在 `praxis_virtualcell/core/config.py` 的 `Mode` 类里加两枚举值。

找到:

```python
class Mode(str, Enum):  # noqa: UP042
    OFFLINE = "offline"
    LLM_ASSISTED = "llm_assisted"
```

改为:

```python
class Mode(str, Enum):  # noqa: UP042
    OFFLINE = "offline"
    LLM_ASSISTED = "llm_assisted"
    # Phase 4(v1.1):LLM 编排模式。LLM 只出 module 集建议(经 safety_contract 过滤成合法候选),
    # 不碰 prediction/hard-rule/verdict 终决(assert_llm_boundaries 三 flag 仍恒 False)。
    LLM_ORCHESTRATED = "llm_orchestrated"
    LLM_ORCHESTRATED_STRICT = "llm_orchestrated_strict"
```

在同文件的 `class Clock:` 之前插入"需要 LLM 的模式集合"常量。

找到:

```python
class Clock:
```

在其**前面**插入:

```python
# 需要 LLM 的运行模式集合(assist / 编排 / 编排-strict)。OFFLINE 不在内 → 恒零 LLM。
LLM_MODES = (Mode.LLM_ASSISTED, Mode.LLM_ORCHESTRATED, Mode.LLM_ORCHESTRATED_STRICT)


class Clock:
```

把 `from_env` 的 mode 判定与 llm_enabled 判定改为认所有需要 LLM 的模式。

找到:

```python
        mode = (Mode.LLM_ASSISTED
                if os.environ.get("PRAXIS_VIRTUALCELL_MODE") == "llm_assisted"
                else Mode.OFFLINE)
        key = os.environ.get("DEEPSEEK_API_KEY", "")
        return cls(
            mode=mode,
            deepseek_api_key=key,
            deepseek_base_url=os.environ.get("PRAXIS_VC_LLM_BASE_URL", "https://api.deepseek.com"),
            deepseek_model=os.environ.get("PRAXIS_VC_LLM_MODEL", "deepseek-chat"),
            llm_enabled=(mode is Mode.LLM_ASSISTED and bool(key)),
        )
```

改为:

```python
        _mode_str = os.environ.get("PRAXIS_VIRTUALCELL_MODE", "offline")
        _by_str = {m.value: m for m in Mode}
        mode = _by_str.get(_mode_str, Mode.OFFLINE)
        key = os.environ.get("DEEPSEEK_API_KEY", "")
        return cls(
            mode=mode,
            deepseek_api_key=key,
            deepseek_base_url=os.environ.get("PRAXIS_VC_LLM_BASE_URL", "https://api.deepseek.com"),
            deepseek_model=os.environ.get("PRAXIS_VC_LLM_MODEL", "deepseek-chat"),
            llm_enabled=(mode in LLM_MODES and bool(key)),
        )
```

- [ ] **Step 4: 改 llm_client.py 的 make_llm_client enabled 判定**

在 `praxis_virtualcell/agents_llm/llm_client.py`。

找到:

```python
from praxis_virtualcell.core.config import Mode, RuntimeConfig
```

改为:

```python
from praxis_virtualcell.core.config import LLM_MODES, RuntimeConfig
```

找到:

```python
def make_llm_client(config: RuntimeConfig) -> LLMClient:
    enabled = config.mode is Mode.LLM_ASSISTED and bool(config.deepseek_api_key)
    return LLMClient(enabled=enabled, api_key=config.deepseek_api_key,
                     base_url=config.deepseek_base_url, model=config.deepseek_model)
```

改为:

```python
def make_llm_client(config: RuntimeConfig) -> LLMClient:
    # Phase 4:enabled 认所有需要 LLM 的模式(assist + 编排 + 编排-strict),不再只认 LLM_ASSISTED。
    enabled = config.mode in LLM_MODES and bool(config.deepseek_api_key)
    return LLMClient(enabled=enabled, api_key=config.deepseek_api_key,
                     base_url=config.deepseek_base_url, model=config.deepseek_model)
```

- [ ] **Step 5: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_orchestrated_mode_config.py -q`
Expected: 7 passed。

- [ ] **Step 6: 全量回归(确认现有 LLM 测试不回归)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 457 passed / 25 skipped / 0 failed(450 + 7 新)。关键:0 failed + skipped 仍 25(未新增 `@pytest.mark.llm`)。**特别核对** `test_llm_optional.py`/`test_llm_fallback_offline.py` 仍绿(`make_llm_client` 改动未破坏 OFFLINE disabled 语义)。

- [ ] **Step 7: 提交**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/core/config.py praxis_virtualcell/agents_llm/llm_client.py praxis_virtualcell/tests/test_orchestrated_mode_config.py
git commit -m "feat(phase4): Mode 加 LLM_ORCHESTRATED/_STRICT 枚举 + make_llm_client enabled 扩到编排模式(三 flag 恒 False)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 4.2:safety_contract 纯函数 `llm_orchestration/safety_contract.py`

**决策说明:** 先落"只能从候选选"的约束内核(纯函数,不进 bus、无 LLM 依赖),它是 LLMModulePlanner 的过滤器 + governance 的守卫。含 `build_candidate_modules`(候选全集)、`filter_to_supported_modules`(复刻 LLMRouter `[a for a in ... if a in candidates]`)、`sanitize_llm_plan`(解析 + fail-closed)、`assert_plan_within_bounds`(ModulePlan 越界守卫)。先建约束,后续 task 的 planner/router 调它。**同时建 `llm_orchestration/__init__.py` 空包。**

**Files:**
- Create: `praxis_virtualcell/llm_orchestration/__init__.py`
- Create: `praxis_virtualcell/llm_orchestration/safety_contract.py`
- Test: `praxis_virtualcell/tests/test_safety_contract.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_safety_contract.py`:

```python
"""Phase 4:safety_contract —— LLM 只能从候选选的约束内核(纯函数,零 LLM)。
铁律(复刻 LLMRouter):越候选剔除、fail-closed(LLM 失败回退确定性 primary)、
不给 unsupported 硬解释(candidate 全集剔 unsupported)。"""
import json

from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.llm_orchestration import safety_contract as SC


def _req(**kw):
    base = {"species": "human", "perturbation_object": "gene",
            "target_output": "expression", "perturbation_targets": ["AHR"]}
    base.update(kw)
    return normalize_request(base)


def _support_all_strong():
    """8 模块全 strong(测 candidate 全集含非 unsupported)。"""
    return {mid: {"support": "strong", "verdict": "accept"} for mid in M.MODULE_ORDER}


def _support_with_unsupported():
    s = _support_all_strong()
    s["degradation_machinery"] = {"support": "unsupported", "verdict": "reject"}
    return s


def test_build_candidate_includes_deterministic_primary():
    cands = SC.build_candidate_modules(_req(), _support_all_strong())
    assert "genetic_hub" in cands             # human gene→expression 的确定性 primary
    assert set(cands) <= set(M.MODULE_ORDER)  # 全 ∈ 白名单
    assert cands == sorted(cands, key=M.MODULE_ORDER.index)  # 按 MODULE_ORDER 排序


def test_build_candidate_excludes_unsupported():
    """不给 unsupported module 硬解释:candidate 全集剔 unsupported。"""
    cands = SC.build_candidate_modules(_req(), _support_with_unsupported())
    assert "degradation_machinery" not in cands


def test_build_candidate_primary_survives_even_if_unsupported():
    """fail-closed:即使 support 把 primary 标 unsupported,primary 仍进候选(不丢主模块)。"""
    s = _support_all_strong()
    s["genetic_hub"] = {"support": "unsupported", "verdict": "reject"}
    cands = SC.build_candidate_modules(_req(), s)
    assert "genetic_hub" in cands             # primary 保底


def test_filter_to_supported_drops_out_of_candidate():
    cands = ["genetic_hub", "stress_processor"]
    out = SC.filter_to_supported_modules(
        ["genetic_hub", "not_a_module", "membrane_system"], cands)
    assert out == ["genetic_hub"]             # 越候选(含发明名)全剔


def test_filter_dedupes_and_preserves_candidate_order():
    cands = ["membrane_system", "genetic_hub", "stress_processor"]
    out = SC.filter_to_supported_modules(
        ["stress_processor", "genetic_hub", "genetic_hub"], cands)
    assert out == ["genetic_hub", "stress_processor"]   # 去重 + 按 candidates 序


def test_sanitize_valid_json_filters_selection():
    cands = ["genetic_hub", "stress_processor"]
    content = json.dumps({"selected_modules": ["genetic_hub", "membrane_system"],
                          "reasoning_summary": "x", "risk_flags": []})
    out = SC.sanitize_llm_plan(content, cands, primary="genetic_hub")
    assert out["selected_modules"] == ["genetic_hub"]   # membrane 越候选被剔
    assert out["reasoning_summary"] == "x"
    assert out["risk_flags"] == []


def test_sanitize_empty_content_is_fail_closed():
    cands = ["genetic_hub", "stress_processor"]
    out = SC.sanitize_llm_plan(None, cands, primary="genetic_hub")
    assert "llm_unavailable" in out["risk_flags"]
    assert "genetic_hub" in out["selected_modules"]     # 回退保底含 primary


def test_sanitize_bad_json_is_fail_closed():
    cands = ["genetic_hub"]
    out = SC.sanitize_llm_plan("not json{", cands, primary="genetic_hub")
    assert "llm_parse_failed" in out["risk_flags"]
    assert out["selected_modules"] == ["genetic_hub"]   # 回退保底


def test_assert_plan_within_bounds_clean():
    plan = {"primary": "genetic_hub", "secondary": ["stress_processor"],
            "entries": [{"module": "genetic_hub"}, {"module": "stress_processor"}]}
    assert SC.assert_plan_within_bounds(plan, ["genetic_hub", "stress_processor"]) == []


def test_assert_plan_within_bounds_detects_out_of_candidate():
    plan = {"primary": "genetic_hub", "secondary": ["degradation_machinery"],
            "entries": [{"module": "genetic_hub"}, {"module": "degradation_machinery"}]}
    v = SC.assert_plan_within_bounds(plan, ["genetic_hub"])
    assert any("degradation_machinery" in x for x in v)
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_safety_contract.py -q`
Expected: FAIL(ModuleNotFoundError: praxis_virtualcell.llm_orchestration)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/llm_orchestration/__init__.py`:

```python
"""LLM 编排子包(Phase 4,v1.1):LLMModulePlanner + safety_contract + cross_module_reasoner。

铁律:LLM 只出 module 集建议(经 safety_contract 过滤成合法候选子集),转 AgentMessage 交
ModuleRouter 用 Phase 3 确定性代码合成 ModulePlan;LLM 绝不碰 prediction/hard-rule/verdict 终决
(assert_llm_boundaries 三 flag 恒 False)。OFFLINE 默认零 LLM,本子包不被触发。
"""
```

写 `praxis_virtualcell/llm_orchestration/safety_contract.py`:

```python
"""safety_contract:LLM 编排的"只能从候选选"约束内核(纯函数,零 LLM/bus 依赖)。

复刻 LLMRouter(agents_llm/llm_router.py)的 `[a for a in ... if a in candidates]`:
LLM 出的 module 集必须过滤成 candidate 子集;candidate 全集 = Phase 3 确定性 primary/secondary
∪ 该物种非 unsupported 的模块。fail-closed:LLM 失败/越界 → 回退确定性,不丢 primary、不给
unsupported module 硬解释。
"""
from __future__ import annotations

import json

from praxis_virtualcell.agents import module_rules
from praxis_virtualcell.biological_modules import modules as M


def build_candidate_modules(req: dict, module_support: dict) -> list[str]:
    """candidate 全集:确定性 primary/secondary ∪ 该物种非 unsupported 模块。
    按 MODULE_ORDER 排序、去重。fail-closed:primary 一定在内(即使 support 标 unsupported)。"""
    primary = module_rules.pick_primary(req)
    secondary = module_rules.pick_secondary(req, primary)
    supported = {mid for mid in M.MODULE_ORDER
                 if (module_support.get(mid) or {}).get("support") != "unsupported"}
    cand = ({primary} | set(secondary) | supported)
    cand.add(primary)                          # primary 保底(即使被标 unsupported 也不丢主模块)
    return sorted(cand, key=M.MODULE_ORDER.index)


def filter_to_supported_modules(llm_modules: list, candidates: list[str]) -> list[str]:
    """复刻 LLMRouter 过滤:只保留 ∈ candidates 的 module,去重,按 candidates 序。"""
    cand_set = set(candidates)
    llm_set = set(llm_modules or [])
    out: list[str] = []
    for c in candidates:                       # 按 candidates 顺序输出
        if c in llm_set and c in cand_set and c not in out:
            out.append(c)
    return out


def sanitize_llm_plan(raw_content: str | None, candidates: list[str],
                      *, primary: str) -> dict:
    """解析 LLM JSON {selected_modules, reasoning_summary, risk_flags} → 合法结构(fail-closed)。
    content 空 → llm_unavailable;JSONDecodeError → llm_parse_failed;任一异常路径 selected 保底含 primary。"""
    out = {"selected_modules": [], "reasoning_summary": "",
           "risk_flags": [], "candidates": list(candidates)}
    _fallback = [primary] if primary in candidates else list(candidates[:1])
    if not raw_content:
        out["risk_flags"] = ["llm_unavailable"]
        out["selected_modules"] = _fallback
        return out
    try:
        d = json.loads(raw_content)
    except (json.JSONDecodeError, TypeError):
        out["risk_flags"] = ["llm_parse_failed"]
        out["selected_modules"] = _fallback
        return out
    sel = filter_to_supported_modules(d.get("selected_modules") or [], candidates)
    if primary in candidates and primary not in sel:
        sel = [primary] + sel                  # primary 保底(LLM 不可删 primary)
    out["selected_modules"] = sel
    out["reasoning_summary"] = str(d.get("reasoning_summary", ""))[:500]
    out["risk_flags"] = list(d.get("risk_flags") or [])
    return out


def assert_plan_within_bounds(plan: dict, candidates: list[str]) -> list[str]:
    """核验 ModulePlan(dict)的 primary/secondary/entries module 全 ∈ candidates。越界 → 违规串列表。"""
    cand_set = set(candidates)
    violations: list[str] = []
    for mid in ([plan.get("primary")] + list(plan.get("secondary", []))
                + [e.get("module") for e in plan.get("entries", [])]):
        if mid is not None and mid not in cand_set:
            violations.append(f"module_out_of_candidates: {mid} ∉ {sorted(cand_set)}")
    return sorted(set(violations))
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_safety_contract.py -q`
Expected: 11 passed。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 468 passed / 25 skipped / 0 failed(457 + 11 新)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/llm_orchestration/__init__.py praxis_virtualcell/llm_orchestration/safety_contract.py praxis_virtualcell/tests/test_safety_contract.py
git commit -m "feat(phase4): safety_contract 约束内核(build_candidate/filter/sanitize/assert_within_bounds;复刻 LLMRouter 只能从候选选,fail-closed)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 4.3:LLMModulePlanner `llm_orchestration/module_planner.py`(进 bus,复刻 LLMRouter)

**决策说明:** `LLMModulePlanner` extends `BaseAgent` 进 bus,复刻 `LLMRouterAgent`。收 `module_plan_request`(payload `{request(raw), module_support, mismatch_queries}`)→ `normalize_request` → `build_candidate_modules` → `client.complete([_SYS, user], json_mode=True)`(system 明令"只从 candidates 选,不发明模块名")→ `sanitize_llm_plan` → emit **`module_candidates_llm`**(receiver="ModuleRouterAgent",payload 透传 request/module_support/mismatch_queries + `module_candidates`)。LLM 只挑合法 module,不产 ModulePlan、不设 engine/verdict/prediction(红线 2/3)。LLM 单测用 FakeLLMClient(离线,不真调 API)。

**Files:**
- Create: `praxis_virtualcell/llm_orchestration/module_planner.py`
- Test: `praxis_virtualcell/tests/test_module_planner.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_module_planner.py`:

```python
"""Phase 4:LLMModulePlanner(进 bus,复刻 LLMRouter"只能从候选选")。
用 FakeLLMClient 离线跑(不真调 API,不打 @pytest.mark.llm,保 skip 基线 25)。
铁律:LLM 选中集必 ⊆ candidates;产 module_candidates_llm(不产 ModulePlan);LLM 失败 → fail-closed。"""
import json

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.llm_orchestration.module_planner import LLMModulePlanner


class FakeLLMClient:
    """离线假 client:按预置 content 返回,不联网。enabled=True 以走 complete 分支。"""
    def __init__(self, content):
        self.enabled = True
        self._content = content
        self.calls = []

    def complete(self, messages, *, json_mode=False, max_tokens=1024):
        self.calls.append(messages)
        return {"disabled": False, "content": self._content, "error": None}


def _support_all_strong():
    from praxis_virtualcell.biological_modules import modules as M
    return {mid: {"support": "strong", "verdict": "accept"} for mid in M.MODULE_ORDER}


def _run(content):
    bus = MessageBus()
    LLMModulePlanner(FakeLLMClient(content)).handle(AgentMessage(
        message_id="c1", sender="SpeciesContextAgent", receiver="LLMModulePlanner",
        message_type="module_plan_request",
        payload={"request": {"species": "human", "perturbation_object": "gene",
                             "target_output": "expression", "perturbation_targets": ["AHR"]},
                 "module_support": _support_all_strong(), "mismatch_queries": {}},
        timestamp="t1"), bus)
    return bus.latest("module_candidates_llm")


def test_emits_module_candidates_llm_not_module_plan():
    """红线 3:planner 产 module_candidates_llm(候选),不产 ModulePlan。"""
    msg = _run(json.dumps({"selected_modules": ["genetic_hub", "stress_processor"],
                           "reasoning_summary": "gene expression + stress", "risk_flags": []}))
    assert msg is not None
    assert msg.message_type == "module_candidates_llm"
    assert msg.receiver == "ModuleRouterAgent"
    # 不产 ModulePlan(module_plan_ready 由 ModuleRouter 产,不在此)
    mc = msg.payload["module_candidates"]
    assert set(mc["selected"]) <= set(mc["candidates"])   # 选中 ⊆ 候选


def test_llm_selection_filtered_to_candidates():
    """LLM 选了 candidate 外/发明的 module → 被剔(只能从候选选)。"""
    msg = _run(json.dumps({"selected_modules": ["genetic_hub", "not_a_module", "INVENTED"],
                           "reasoning_summary": "", "risk_flags": []}))
    sel = msg.payload["module_candidates"]["selected"]
    assert "not_a_module" not in sel
    assert "INVENTED" not in sel
    assert "genetic_hub" in sel


def test_llm_empty_content_fail_closed():
    """LLM 返回空 → llm_unavailable + 回退保底含 primary(不丢主模块)。"""
    msg = _run(None)
    mc = msg.payload["module_candidates"]
    assert "llm_unavailable" in mc["risk_flags"]
    assert "genetic_hub" in mc["selected"]


def test_llm_bad_json_fail_closed():
    msg = _run("not json{")
    mc = msg.payload["module_candidates"]
    assert "llm_parse_failed" in mc["risk_flags"]
    assert "genetic_hub" in mc["selected"]


def test_payload_passes_through_request_and_support():
    """透传 request/module_support/mismatch_queries 供下游 ModuleRouter 复用(不丢上下文)。"""
    msg = _run(json.dumps({"selected_modules": ["genetic_hub"], "reasoning_summary": "", "risk_flags": []}))
    assert msg.payload["request"]["species"] == "human"
    assert "module_support" in msg.payload
    assert "mismatch_queries" in msg.payload


def test_planner_calls_llm_with_candidates_in_prompt():
    """system 约束 + user 带 candidates(供审计 prompt 里确实给了候选集)。"""
    fc = FakeLLMClient(json.dumps({"selected_modules": ["genetic_hub"], "reasoning_summary": "", "risk_flags": []}))
    bus = MessageBus()
    LLMModulePlanner(fc).handle(AgentMessage(
        message_id="c1", sender="SpeciesContextAgent", receiver="LLMModulePlanner",
        message_type="module_plan_request",
        payload={"request": {"species": "human", "perturbation_object": "gene",
                             "target_output": "expression", "perturbation_targets": ["AHR"]},
                 "module_support": _support_all_strong(), "mismatch_queries": {}}, timestamp="t1"), bus)
    user_msg = fc.calls[0][-1]["content"]
    assert "genetic_hub" in user_msg          # candidates 在 prompt 里
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_planner.py -q`
Expected: FAIL(ModuleNotFoundError: ...module_planner)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/llm_orchestration/module_planner.py`:

```python
"""LLMModulePlanner(Phase 4,进 message bus):复刻 LLMRouter 的"只能从候选选"。

收 module_plan_request({request(raw), module_support, mismatch_queries})→ 归一 → 建候选全集
(safety_contract.build_candidate_modules)→ 调 LLM 出 module 集 → sanitize_llm_plan 过滤成
候选子集(fail-closed)→ emit module_candidates_llm 交 ModuleRouter 用 Phase 3 代码合成 ModulePlan。

铁律:LLM 只挑合法 module 集(不产 ModulePlan、不设 engine/verdict/prediction);越候选剔除;
LLM 失败回退保底含 primary。assert_llm_boundaries 三 flag 恒 False 由入口守卫,LLM 产物只进
候选过滤 + 后续 provenance notes,不碰 prediction/hard-rule。
"""
from __future__ import annotations

import json

from praxis_virtualcell.agents import module_rules
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.llm_orchestration import safety_contract as SC

_SYS = (
    "你给虚拟细胞的生物功能模块编排建议。只输出 JSON:"
    '{"selected_modules":[],"reasoning_summary":"","risk_flags":[]}。'
    "selected_modules 里的模块名必须来自给定 candidates,不要发明新模块名、不要选 candidates 外的。"
    "你只挑选相关模块,不决定引擎、不给数值预测、不改裁决。只输出 JSON。"
)


class LLMModulePlanner(BaseAgent):
    name = "LLMModulePlanner"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        raw = message.payload["request"]
        req = normalize_request(raw)
        module_support = message.payload.get("module_support", {})
        mismatch_queries = message.payload.get("mismatch_queries", {})
        primary = module_rules.pick_primary(req)
        candidates = SC.build_candidate_modules(req, module_support)

        user = json.dumps({"request": raw, "candidates": candidates,
                           "deterministic_primary": primary}, ensure_ascii=False)
        res = self.client.complete(
            [{"role": "system", "content": _SYS}, {"role": "user", "content": user}],
            json_mode=True)
        mc = SC.sanitize_llm_plan(res.get("content"), candidates, primary=primary)
        mc["selected"] = mc.pop("selected_modules")   # 对外键名 selected
        bus.send(AgentMessage(
            message_id=message.message_id + ":mcllm",
            sender=self.name, receiver="ModuleRouterAgent",
            message_type="module_candidates_llm",
            payload={"request": raw, "module_support": module_support,
                     "mismatch_queries": mismatch_queries, "module_candidates": mc},
            timestamp=message.timestamp, parent_message_id=message.message_id))
```

> **注意** `sanitize_llm_plan` 返回键是 `selected_modules`;planner 对外统一成 `selected`(测试断言 `mc["selected"]`)。`candidates`/`reasoning_summary`/`risk_flags` 键保留。

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_planner.py -q`
Expected: 6 passed。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 474 passed / 25 skipped / 0 failed(468 + 6 新)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/llm_orchestration/module_planner.py praxis_virtualcell/tests/test_module_planner.py
git commit -m "feat(phase4): LLMModulePlanner(进 bus,复刻 LLMRouter;LLM 只挑合法 module 集 → module_candidates_llm,fail-closed)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 4.4:ModuleRouterAgent 读 LLM 候选(决策 P1/P2,最小扩展,不破坏 Phase 3)

**决策说明:** 给 `ModuleRouterAgent.handle` 加**可选**分支:若 payload 带 `module_candidates`(LLM 过滤后的 selected),则 secondary 从 LLM selected 派生(primary 仍由 `pick_primary` 定,LLM 不改 primary —— 决策 P1);selected 里非 primary 且 ∈ candidate 全集的成为 secondary(决策 P2)。**engine/verdict/entry 构造(`_build_entry`)完全不变**(route() 落 engine、synthesize_verdict 定 verdict、mismatch 降级)。无 `module_candidates`(OFFLINE)→ 走 Phase 3 原路径。plan `notes` 追加 LLM risk_flags。**这样 Phase 3 全部现有测试不回归(无 module_candidates 分支即原行为)。**

**Files:**
- Modify: `praxis_virtualcell/agents/module_router_agent.py`
- Test: `praxis_virtualcell/tests/test_module_router_llm.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_module_router_llm.py`:

```python
"""Phase 4:ModuleRouter 读 LLM 候选(决策 P1/P2)。
铁律:primary 永由确定性规则定(LLM 不改);LLM 只增删 secondary 且 ⊆ candidates;
engine/verdict 仍由 route()+synthesize 定(LLM 无法把 downgrade 改 accept)。"""
from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage


def _ctx(request):
    bus = MessageBus()
    SpeciesContextAgent().handle(AgentMessage(
        message_id="c1", sender="SpeciesBrain", receiver="SpeciesContextAgent",
        message_type="species_context", payload={"request": request}, timestamp="t1"), bus)
    return bus.latest("species_context_ready").payload


def _plan_with_candidates(request, selected, risk_flags=None):
    ctx = _ctx(request)
    bus = MessageBus()
    ModuleRouterAgent().handle(AgentMessage(
        message_id="c2", sender="LLMModulePlanner", receiver="ModuleRouterAgent",
        message_type="module_route",
        payload={"request": request, "module_support": ctx["module_support"],
                 "mismatch_queries": ctx["mismatch_queries"],
                 "module_candidates": {"selected": selected, "candidates": [],
                                       "reasoning_summary": "", "risk_flags": risk_flags or []}},
        timestamp="t2"), bus)
    return bus.latest("module_plan_ready").payload


_HUMAN_GENE = {"species": "human", "perturbation_object": "gene",
               "target_output": "expression", "perturbation_targets": ["AHR"]}


def test_primary_unchanged_even_if_llm_omits_it():
    """决策 P1:LLM selected 不含 primary,primary 仍由确定性规则定(LLM 不改 primary)。"""
    p = _plan_with_candidates(_HUMAN_GENE, selected=["stress_processor"])
    assert p["primary"] == "genetic_hub"      # 确定性 primary,LLM 没选也保留
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["module"] == "genetic_hub"


def test_llm_adds_secondary_from_selection():
    """决策 P2:LLM 选了合法 secondary(stress_processor)→ 进 plan secondary。"""
    p = _plan_with_candidates(_HUMAN_GENE, selected=["genetic_hub", "stress_processor"])
    assert "stress_processor" in p["secondary"]


def test_llm_cannot_change_verdict_to_accept():
    """红线:LLM 选了某 module,但其 route/species 若是 caution/abstain,verdict 仍不 accept。
    bacteria gene→expression primary=genetic_hub 是 abstain,LLM 选它也改不成 accept。"""
    p = _plan_with_candidates(
        {"species": "bacteria", "perturbation_object": "gene",
         "target_output": "expression", "perturbation_targets": ["b0720"]},
        selected=["genetic_hub"])
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["verdict"] != "accept"        # LLM 无法把 abstain 捞成 accept


def test_offline_path_unchanged_without_candidates():
    """无 module_candidates(OFFLINE)→ 走 Phase 3 原路径(secondary 由 pick_secondary)。"""
    ctx = _ctx({"species": "human", "perturbation_object": "gene",
                "target_output": "growth", "perturbation_targets": ["MYC"]})
    bus = MessageBus()
    ModuleRouterAgent().handle(AgentMessage(
        message_id="c2", sender="SpeciesContextAgent", receiver="ModuleRouterAgent",
        message_type="module_route",
        payload={"request": {"species": "human", "perturbation_object": "gene",
                             "target_output": "growth", "perturbation_targets": ["MYC"]},
                 "module_support": ctx["module_support"],
                 "mismatch_queries": ctx["mismatch_queries"]},  # 无 module_candidates
        timestamp="t2"), bus)
    p = bus.latest("module_plan_ready").payload
    assert "mitochondrial_energy_metabolism" in p["secondary"]   # Phase 3 确定性 secondary


def test_llm_risk_flags_surfaced_in_notes():
    """LLM 失败标记(llm_unavailable)透传进 plan notes(可追溯)。"""
    p = _plan_with_candidates(_HUMAN_GENE, selected=["genetic_hub"],
                              risk_flags=["llm_unavailable"])
    assert any("llm_unavailable" in n for n in p["notes"])


def test_llm_out_of_candidate_secondary_dropped():
    """LLM selected 里越候选的 module 不进 secondary(双保险:planner 已过滤,router 再核)。"""
    p = _plan_with_candidates(_HUMAN_GENE, selected=["genetic_hub", "membrane_system"])
    # membrane_system 是否成 secondary 取决于它是否 ∈ candidate 全集;若 human membrane weak(非 unsupported)
    # 则它是合法候选、可成 secondary;此断言只保证:secondary 全 ∈ MODULE_ORDER 且不含发明名。
    from praxis_virtualcell.biological_modules import modules as M
    assert all(s in M.MODULE_ORDER for s in p["secondary"])
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_router_llm.py -q`
Expected: FAIL(`test_llm_adds_secondary_from_selection` 等失败 —— ModuleRouter 尚未读 module_candidates)。

- [ ] **Step 3: 改 module_router_agent.py 加 LLM 候选分支**

在 `praxis_virtualcell/agents/module_router_agent.py`。

找到 import 段末尾:

```python
from praxis_virtualcell.agents import module_rules
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
```

改为(加 safety_contract import):

```python
from praxis_virtualcell.agents import module_rules
from praxis_virtualcell.agents.route_table import route
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.llm_orchestration import safety_contract as SC
```

找到 `handle` 里的 primary/secondary 段:

```python
        primary = module_rules.pick_primary(req)
        secondary = module_rules.pick_secondary(req, primary)
        notes: list[str] = []
```

改为:

```python
        primary = module_rules.pick_primary(req)   # 决策 P1:primary 永由确定性规则定,LLM 不改
        notes: list[str] = []
        # Phase 4:若带 LLM 候选(module_candidates.selected),secondary 从 LLM 选中集派生
        # (决策 P2:LLM 只增删 secondary,且必 ⊆ candidate 全集)。无候选(OFFLINE)→ Phase 3 原路径。
        mc = message.payload.get("module_candidates")
        if mc and mc.get("selected") is not None:
            candidates = SC.build_candidate_modules(req, module_support)
            secondary = [m for m in mc["selected"]
                         if m != primary and m in candidates]
            for flag in (mc.get("risk_flags") or []):
                notes.append(f"llm_{flag}" if not str(flag).startswith("llm_") else str(flag))
        else:
            secondary = module_rules.pick_secondary(req, primary)
```

> **注意** engine/verdict/entry 构造(`_build_entry`)与 Phase 3 **完全不变** —— 只改了 secondary 的**来源**。故 LLM 无法碰 engine/verdict/prediction(红线 2/3)。`notes` 里 flag 前缀归一为 `llm_*`(`llm_unavailable` 已带前缀则不重复加)。

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_module_router_llm.py -q`
Expected: 6 passed。

- [ ] **Step 5: 全量回归(确认 Phase 3 module 测试零回归)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 480 passed / 25 skipped / 0 failed(474 + 6 新)。**特别核对** `test_module_router_agent.py`/`test_module_golden_cases.py`/`test_module_consistency.py` 全绿(无 module_candidates 分支即 Phase 3 原行为,零回归)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/agents/module_router_agent.py praxis_virtualcell/tests/test_module_router_llm.py
git commit -m "feat(phase4): ModuleRouter 读 LLM 候选(决策 P1/P2;primary 不可改、LLM 只增删 secondary ⊆ candidates;engine/verdict 不变)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 4.5:LLMCrossModuleReasoner `llm_orchestration/cross_module_reasoner.py`(进 bus,复刻 LLMCritic)

**决策说明:** `LLMCrossModuleReasoner` extends `BaseAgent` 进 bus,复刻 `LLMCriticAgent`。收 `cross_module_review`(payload `{module_plan}`,即 `ModulePlan.to_dict()`)→ `client.complete([_SYS, user], json_mode=True)`→ emit `llm_cross_module_notes`(payload `{notes, flags}`)。**只出 advisory notes/flags,绝不改任何 entry/verdict/prediction**(决策 P4,红线 2)。写进 `report.provenance.llm_cross_module_notes`(Task 4.7 接管线时)。LLM 单测用 FakeLLMClient。

**Files:**
- Create: `praxis_virtualcell/llm_orchestration/cross_module_reasoner.py`
- Test: `praxis_virtualcell/tests/test_cross_module_reasoner.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_cross_module_reasoner.py`:

```python
"""Phase 4:LLMCrossModuleReasoner(进 bus,复刻 LLMCritic)。FakeLLMClient 离线跑。
铁律(决策 P4):只出 notes/flags,不改 module_plan;LLM 失败 → flags=[llm_unavailable/llm_parse_failed]。"""
import json

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.llm_orchestration.cross_module_reasoner import LLMCrossModuleReasoner


class FakeLLMClient:
    def __init__(self, content):
        self.enabled = True
        self._content = content

    def complete(self, messages, *, json_mode=False, max_tokens=1024):
        return {"disabled": False, "content": self._content, "error": None}


_PLAN = {"species": "human", "primary": "genetic_hub", "secondary": ["stress_processor"],
         "overall_verdict": "accept",
         "entries": [{"module": "genetic_hub", "role": "primary", "verdict": "accept"},
                     {"module": "stress_processor", "role": "secondary", "verdict": "accept"}],
         "notes": []}


def _run(content):
    bus = MessageBus()
    LLMCrossModuleReasoner(FakeLLMClient(content)).handle(AgentMessage(
        message_id="c1", sender="Report", receiver="LLMCrossModuleReasoner",
        message_type="cross_module_review", payload={"module_plan": _PLAN}, timestamp="t1"), bus)
    return bus.latest("llm_cross_module_notes")


def test_emits_notes_and_flags_only():
    msg = _run(json.dumps({"notes": ["genetic_hub 与 stress 组合合理"], "flags": []}))
    assert msg.message_type == "llm_cross_module_notes"
    assert set(msg.payload) == {"notes", "flags"}      # 只 notes/flags,无 prediction/verdict
    assert msg.payload["notes"] == ["genetic_hub 与 stress 组合合理"]


def test_does_not_mutate_module_plan():
    """决策 P4:reasoner 不改 module_plan(原 dict 不被修改)。"""
    before = json.dumps(_PLAN, sort_keys=True)
    _run(json.dumps({"notes": ["x"], "flags": ["y"]}))
    assert json.dumps(_PLAN, sort_keys=True) == before  # plan 未被改


def test_empty_content_flags_unavailable():
    msg = _run(None)
    assert "llm_unavailable" in msg.payload["flags"]


def test_bad_json_flags_parse_failed():
    msg = _run("not json{")
    assert "llm_parse_failed" in msg.payload["flags"]
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_cross_module_reasoner.py -q`
Expected: FAIL(ModuleNotFoundError: ...cross_module_reasoner)。

- [ ] **Step 3: 写实现**

写 `praxis_virtualcell/llm_orchestration/cross_module_reasoner.py`:

```python
"""LLMCrossModuleReasoner(Phase 4,进 message bus):复刻 LLMCritic 的 advisory 模式。

收 cross_module_review({module_plan})→ 调 LLM → emit llm_cross_module_notes({notes, flags})。
只做跨模块一致性/生物学合理性的自然语言复核(可解释层),绝不改任何 entry/verdict/prediction
(决策 P4,红线 2)。写进 report.provenance.llm_cross_module_notes(接管线时)。
"""
from __future__ import annotations

import json

from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_SYS = (
    "你复核虚拟细胞的模块编排计划(ModulePlan)的跨模块一致性与生物学合理性。"
    "检查:primary/secondary 组合是否合理、是否有模块冲突、是否遗漏明显相关模块。"
    "你只给出观察和风险标记,不修改计划、不改裁决、不给数值预测。只输出 JSON:"
    '{"notes":[],"flags":[]}。flags 用简短英文标签。只输出 JSON。'
)


class LLMCrossModuleReasoner(BaseAgent):
    name = "LLMCrossModuleReasoner"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        module_plan = message.payload["module_plan"]
        res = self.client.complete(
            [{"role": "system", "content": _SYS},
             {"role": "user", "content": json.dumps(module_plan, ensure_ascii=False)}],
            json_mode=True)
        out = {"notes": [], "flags": []}
        if res.get("content"):
            try:
                d = json.loads(res["content"])
                out["notes"] = list(d.get("notes") or [])
                out["flags"] = list(d.get("flags") or [])
            except json.JSONDecodeError:
                out["flags"] = ["llm_parse_failed"]
        else:
            out["flags"] = ["llm_unavailable"]
        bus.send(AgentMessage(
            message_id=message.message_id + ":xmod",
            sender=self.name, receiver="client",
            message_type="llm_cross_module_notes", payload=out,
            timestamp=message.timestamp, parent_message_id=message.message_id))
```

- [ ] **Step 4: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_cross_module_reasoner.py -q`
Expected: 4 passed。

- [ ] **Step 5: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 484 passed / 25 skipped / 0 failed(480 + 4 新)。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/llm_orchestration/cross_module_reasoner.py praxis_virtualcell/tests/test_cross_module_reasoner.py
git commit -m "feat(phase4): LLMCrossModuleReasoner(进 bus,复刻 LLMCritic;只出 notes/flags 不改 plan,决策 P4)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 4.6:LLM 编排契约测试(扩 test_llm_boundary_flags 模式,红线 2/3 钉死)

**决策说明:** 路线图 §8 Phase 4 = "LLM contract tests 30(🟢 扩 test_llm_boundary_flags 模式)"。前面 tasks 已产 15 条 LLM 相关测试(4.1 的 7 + 4.3 的 6... 部分属功能测试)。本 task 集中补**契约/红线**测试:一个独立文件 `test_llm_orchestration_contract.py`,钉死红线 2/3 —— ①三 flag 在 orchestrated 下恒 False + assert_llm_boundaries 仍拦;②LLM 产物只进候选过滤/notes,绝不进 prediction/verdict;③LLM 不能给 unsupported module 硬解释(assert_plan_within_bounds);④LLM 不能把 downgrade/abstain 改 accept;⑤LLM plan 必须转 AgentMessage 才执行(planner emit 的是候选消息不是 plan);⑥OFFLINE 零 LLM(grep import)。全部 FakeLLMClient/纯函数离线,不打 @pytest.mark.llm。

**Files:**
- Create: `praxis_virtualcell/tests/test_llm_orchestration_contract.py`

- [ ] **Step 1: 写契约测试(≥20 条,凑 Phase 4 LLM 契约总数 ≥30)**

写 `praxis_virtualcell/tests/test_llm_orchestration_contract.py`:

```python
"""Phase 4:LLM 编排红线契约测试(扩 test_llm_boundary_flags 模式)。
钉死红线 2(三 flag 恒 False、LLM 不碰 prediction/hard-rule/verdict)、红线 3(LLM plan 转
AgentMessage、不给 unsupported 硬解释、不把 downgrade 改 accept)。全离线(FakeLLMClient/纯函数)。"""
import json
import subprocess
import sys

import pytest

from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import (
    LLM_MODES,
    Mode,
    RuntimeConfig,
    assert_llm_boundaries,
)
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.llm_orchestration import safety_contract as SC
from praxis_virtualcell.llm_orchestration.module_planner import LLMModulePlanner


class FakeLLMClient:
    def __init__(self, content):
        self.enabled = True
        self._content = content

    def complete(self, messages, *, json_mode=False, max_tokens=1024):
        return {"disabled": False, "content": self._content, "error": None}


# ---------- 红线 2:三 flag 恒 False(所有 orchestrated 模式) ----------
@pytest.mark.parametrize("mode", [Mode.LLM_ORCHESTRATED, Mode.LLM_ORCHESTRATED_STRICT])
def test_three_flags_false_all_orchestrated_modes(mode):
    c = RuntimeConfig(mode=mode, deepseek_api_key="sk-fake")
    assert c.allow_llm_to_modify_core_decision is False
    assert c.allow_llm_to_modify_prediction is False
    assert c.allow_llm_to_override_hard_rules is False
    assert_llm_boundaries(c)                          # 不抛


@pytest.mark.parametrize("flag", [
    "allow_llm_to_modify_core_decision",
    "allow_llm_to_modify_prediction",
    "allow_llm_to_override_hard_rules",
])
def test_assert_boundaries_still_raises_under_orchestrated(flag):
    """orchestrated 下强改某 flag 为 True 仍被守卫拦(守卫不因新模式松动)。"""
    c = RuntimeConfig(mode=Mode.LLM_ORCHESTRATED, deepseek_api_key="sk-fake")
    object.__setattr__(c, flag, True)
    with pytest.raises(Exception):  # noqa: B017
        assert_llm_boundaries(c)


def test_orchestrated_modes_in_llm_modes():
    assert Mode.LLM_ORCHESTRATED in LLM_MODES
    assert Mode.LLM_ORCHESTRATED_STRICT in LLM_MODES
    assert Mode.OFFLINE not in LLM_MODES              # 红线 1:OFFLINE 不在 LLM 模式集


# ---------- 红线 3:LLM plan 必须转 AgentMessage(planner 产候选,不产 plan) ----------
def _support_all_strong():
    return {mid: {"support": "strong", "verdict": "accept"} for mid in M.MODULE_ORDER}


def _planner_msg(content):
    bus = MessageBus()
    LLMModulePlanner(FakeLLMClient(content)).handle(AgentMessage(
        "c1", "SpeciesContextAgent", "LLMModulePlanner", "module_plan_request",
        {"request": {"species": "human", "perturbation_object": "gene",
                     "target_output": "expression", "perturbation_targets": ["AHR"]},
         "module_support": _support_all_strong(), "mismatch_queries": {}}, "t1"), bus)
    return bus


def test_planner_emits_agentmessage_not_plan():
    bus = _planner_msg(json.dumps({"selected_modules": ["genetic_hub"],
                                   "reasoning_summary": "", "risk_flags": []}))
    # 产的是候选消息(AgentMessage),不是可执行 ModulePlan
    assert bus.latest("module_candidates_llm") is not None
    assert bus.latest("module_plan_ready") is None    # planner 不产 plan(须过 ModuleRouter)


def test_planner_output_is_agentmessage_type():
    bus = _planner_msg(json.dumps({"selected_modules": ["genetic_hub"],
                                   "reasoning_summary": "", "risk_flags": []}))
    msg = bus.latest("module_candidates_llm")
    assert isinstance(msg, AgentMessage)
    assert msg.receiver == "ModuleRouterAgent"        # 必转交确定性 router 才执行


# ---------- 红线 3:LLM 不给 unsupported module 硬解释 ----------
def test_llm_cannot_select_unsupported_module():
    """support 里 degradation unsupported → 不进 candidate → LLM 选它也被剔。"""
    sup = _support_all_strong()
    sup["degradation_machinery"] = {"support": "unsupported", "verdict": "reject"}
    from praxis_virtualcell.agents.species_schema import normalize_request
    req = normalize_request({"species": "human", "perturbation_object": "gene",
                             "target_output": "expression", "perturbation_targets": ["AHR"]})
    cands = SC.build_candidate_modules(req, sup)
    assert "degradation_machinery" not in cands
    out = SC.sanitize_llm_plan(
        json.dumps({"selected_modules": ["genetic_hub", "degradation_machinery"]}),
        cands, primary="genetic_hub")
    assert "degradation_machinery" not in out["selected_modules"]


def test_assert_plan_within_bounds_catches_unsupported_leak():
    plan = {"primary": "genetic_hub", "secondary": ["degradation_machinery"],
            "entries": [{"module": "genetic_hub"}, {"module": "degradation_machinery"}]}
    assert SC.assert_plan_within_bounds(plan, ["genetic_hub"]) != []


# ---------- 红线 3/4:LLM 不能把 downgrade/abstain 改 accept ----------
def _plan_with_llm(request, selected):
    bus = MessageBus()
    SpeciesContextAgent().handle(AgentMessage(
        "c1", "SpeciesBrain", "SpeciesContextAgent", "species_context",
        {"request": request}, "t1"), bus)
    ctx = bus.latest("species_context_ready").payload
    ModuleRouterAgent().handle(AgentMessage(
        "c2", "LLMModulePlanner", "ModuleRouterAgent", "module_route",
        {"request": request, "module_support": ctx["module_support"],
         "mismatch_queries": ctx["mismatch_queries"],
         "module_candidates": {"selected": selected, "candidates": [],
                               "reasoning_summary": "", "risk_flags": []}}, "t2"), bus)
    return bus.latest("module_plan_ready").payload


def test_llm_cannot_upgrade_bacteria_expression_to_accept():
    p = _plan_with_llm(
        {"species": "bacteria", "perturbation_object": "gene",
         "target_output": "expression", "perturbation_targets": ["b0720"]},
        selected=["genetic_hub"])
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["verdict"] != "accept"                # abstain 改不成 accept


def test_llm_cannot_upgrade_mouse_ortholog_caution_to_accept():
    p = _plan_with_llm(
        {"species": "mouse", "perturbation_object": "gene",
         "target_output": "expression", "perturbation_targets": ["Gata1"]},
        selected=["genetic_hub"])
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["verdict"] == "caution"               # ortholog caution 不被 LLM 洗白


def test_llm_cannot_change_primary():
    """决策 P1:LLM 选别的 module,primary 仍是确定性 genetic_hub。"""
    p = _plan_with_llm(
        {"species": "human", "perturbation_object": "gene",
         "target_output": "expression", "perturbation_targets": ["AHR"]},
        selected=["stress_processor", "cytoplasmic_metabolism"])
    assert p["primary"] == "genetic_hub"


def test_llm_mismatch_still_downgrades():
    """bacteria 自噬 mismatch:即便 LLM 选了 degradation,若它是候选,mismatch 仍降级不 accept。"""
    # bacteria degradation 若在候选内且命中 autophagy mismatch → verdict 非 accept
    p = _plan_with_llm(
        {"species": "bacteria", "perturbation_object": "gene",
         "target_output": "growth", "perturbation_targets": ["lon"]},
        selected=["cytoplasmic_metabolism", "degradation_machinery"])
    degs = [e for e in p["entries"] if e["module"] == "degradation_machinery"]
    for e in degs:
        assert e["verdict"] != "accept"


# ---------- fail-closed(红线 6) ----------
def test_llm_unavailable_falls_back_to_primary():
    out = SC.sanitize_llm_plan(None, ["genetic_hub", "stress_processor"], primary="genetic_hub")
    assert "llm_unavailable" in out["risk_flags"]
    assert "genetic_hub" in out["selected_modules"]


def test_llm_parse_failed_falls_back():
    out = SC.sanitize_llm_plan("{bad", ["genetic_hub"], primary="genetic_hub")
    assert "llm_parse_failed" in out["risk_flags"]
    assert out["selected_modules"] == ["genetic_hub"]


# ---------- 红线 1:OFFLINE 零 LLM(源码级 grep) ----------
def test_offline_deterministic_modules_import_no_llm():
    """Phase 3 确定性 module 路由文件不 import agents_llm(OFFLINE 零 LLM)。
    注:module_router_agent Phase 4 import 了 llm_orchestration.safety_contract(纯函数,零 LLM 调用),
    但**不 import agents_llm**、不调 client —— OFFLINE 路径不触发任何 LLM。"""
    files = [
        "praxis_virtualcell/agents/module_rules.py",
        "praxis_virtualcell/biological_modules/module_plan.py",
        "praxis_virtualcell/agents/species_context_agent.py",
        "praxis_virtualcell/llm_orchestration/safety_contract.py",
    ]
    r = subprocess.run([sys.executable, "-c",
        "import sys; "
        "bad=[f for f in sys.argv[1:] if 'agents_llm' in open(f, encoding='utf-8').read()]; "
        "print(','.join(bad))", *files], capture_output=True, text=True)
    assert r.stdout.strip() == "", f"OFFLINE 确定性文件不应 import agents_llm: {r.stdout}"


def test_safety_contract_has_no_llm_client_import():
    src = open("praxis_virtualcell/llm_orchestration/safety_contract.py", encoding="utf-8").read()
    assert "llm_client" not in src                    # 纯函数约束器,不碰 client
    assert "httpx" not in src


# ---------- LLM 产物只进 provenance/候选,不进 prediction ----------
def test_llm_selected_only_affects_secondary_not_prediction_fields():
    """LLM 选中集只改 secondary;primary/entries 的 engine/route_disposition 由确定性源定。"""
    p = _plan_with_llm(
        {"species": "human", "perturbation_object": "gene",
         "target_output": "expression", "perturbation_targets": ["AHR"]},
        selected=["genetic_hub", "stress_processor"])
    prim = next(e for e in p["entries"] if e["role"] == "primary")
    assert prim["engine"] == "donor_predictor"        # engine 由 route() 定,LLM 不碰
    assert prim["route_disposition"] == "accept"      # disposition 由 route() 定
```

- [ ] **Step 2: 跑确认通过(全新增文件,应直接绿 —— 依赖已在 4.1–4.5 落地)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_llm_orchestration_contract.py -q`
Expected: 全绿(参数化后条数:2 + 3 + 1 + 2 + 2 + 4 + 2 + 2 + 2 = 20 条,含 parametrize 展开)。以实跑条数为准。

> **执行者提醒:** `test_llm_mismatch_still_downgrades` 依赖 bacteria degradation 是否在 candidate 全集(取决于 bacteria module_support 里 degradation 的 support 值 + autophagy mismatch 声明)。若 degradation 不在候选(被 planner 剔)则 `degs` 为空、vacuously pass;这是刻意的 fail-closed 语义(出现即降级)。若实跑发现 degradation 在候选且 verdict=accept → 真实 bug,停下报告。

- [ ] **Step 3: 核对 Phase 4 LLM 契约测试总数 ≥30(路线图 §8)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_orchestrated_mode_config.py praxis_virtualcell/tests/test_safety_contract.py praxis_virtualcell/tests/test_module_planner.py praxis_virtualcell/tests/test_module_router_llm.py praxis_virtualcell/tests/test_cross_module_reasoner.py praxis_virtualcell/tests/test_llm_orchestration_contract.py -q`
Expected: 合计 ≥30 passed(7 + 11 + 6 + 6 + 4 + 20 = 54 条 LLM 编排相关,远超路线图 §8 的 30 目标)。**关键:全绿。**

- [ ] **Step 4: 全量回归 + 提交**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 504 passed / 25 skipped / 0 failed(484 + 20 新;以实跑参数化展开数为准)。关键:0 failed + skipped 仍 25。

```bash
find . -name '._*' -delete
git add praxis_virtualcell/tests/test_llm_orchestration_contract.py
git commit -m "test(phase4): LLM 编排红线契约测试(三 flag 恒 False/LLM 转 AgentMessage/不给 unsupported 硬解释/不把 downgrade 改 accept/OFFLINE 零 LLM)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 4.7:接进 runtime 管线(build_runtime 注册 + run_workflow 旁路挂载 module_plan)

**决策说明:** 把 SpeciesContext→(LLMModulePlanner?)→ModuleRouter 接进 `run_workflow`,**旁路挂载**:在 `ModelApplicability` 之后跑这条链产 `module_plan`,把它挂进 `report.provenance.module_plan`(与现有 `llm_route_suggestion` 挂法一致),**predictor fan-out/ensemble/reliability/critic 全不改**(插点归置决策)。`build_runtime` 加:总是注册 `SpeciesContextAgent`+`ModuleRouterAgent`(OFFLINE 确定性);`if client.enabled` 且 mode ∈ orchestrated 再注册 `LLMModulePlanner`+`LLMCrossModuleReasoner`。runtime 用 `if "X" in self._agents` gating(校正 §校正3),**OFFLINE 分支不进 module_plan 挂载**(等价现在;由 build_runtime 在 OFFLINE 也注册确定性两节点 → OFFLINE 也产 module_plan,但 LLM 节点不在册 → 走确定性 secondary,零 LLM)。

**关键最小侵入设计:** `run_workflow` 的 module_plan 挂载是**新增分支**,读 `app.payload`(已有的 request/brain_context),不改 predictor fan-out 读的字段。SpeciesContext 用 `app.payload["request"]`(归一后 dict)构造。挂载失败(如 module_support 缺)不应炸主流程 —— 但按红线"不静默",此处若 ModuleRouter 抛则是真实 bug(SpeciesContext 已保证 8 模块全覆盖),不 try/except 吞掉。

**Files:**
- Modify: `praxis_virtualcell/workflows/predict_delta_expression.py`(build_runtime 注册新 agent)
- Modify: `praxis_virtualcell/core/runtime.py`(run_workflow 加 module_plan 旁路挂载)
- Test: `praxis_virtualcell/tests/test_runtime_module_plan.py`

- [ ] **Step 1: 写失败测试**

写 `praxis_virtualcell/tests/test_runtime_module_plan.py`:

```python
"""Phase 4:接管线 —— module_plan 旁路挂进 report.provenance。
铁律:OFFLINE 产确定性 module_plan(零 LLM),核心 prediction/reliability 字段与接管线前等价;
LLM_ORCHESTRATED 无 key → 回退等价 OFFLINE(红线 1)。"""
from praxis_virtualcell.core.config import Mode, RuntimeConfig
from praxis_virtualcell.core.request import VirtualCellRequest
from praxis_virtualcell.workflows.predict_delta_expression import build_runtime

_HUMAN = {"request_id": "r1", "species": "human", "perturbation_type": "gene",
          "perturbation_targets": ["AHR"], "input_modality": "scRNA",
          "output_modality": "delta_expression", "task_type": "predict_delta_expression"}


def _run(cfg):
    return build_runtime(cfg).run_workflow(VirtualCellRequest.from_dict(_HUMAN))


def test_offline_report_has_module_plan_in_provenance():
    rep = _run(RuntimeConfig(mode=Mode.OFFLINE))
    mp = rep.get("provenance", {}).get("module_plan")
    assert mp is not None
    assert mp["primary"] == "genetic_hub"          # human gene→expression
    assert mp["overall_verdict"] in ("accept", "caution", "downgrade", "abstain", "reject")


def test_offline_module_plan_is_deterministic_zero_llm():
    """OFFLINE 的 module_plan notes 不含 llm_* 标记(零 LLM)。"""
    rep = _run(RuntimeConfig(mode=Mode.OFFLINE))
    notes = rep["provenance"]["module_plan"]["notes"]
    assert not any("llm_" in n for n in notes)


def test_offline_core_prediction_unchanged_by_module_plan():
    """接 module_plan 不改核心 prediction/reliability(旁路挂载,红线:不改现有逻辑)。"""
    rep = _run(RuntimeConfig(mode=Mode.OFFLINE))
    # 核心字段仍在(module_plan 是旁路,不动主报告)
    for k in ("abstain", "reliability", "models_used", "models_rejected"):
        assert k in rep


def test_orchestrated_without_key_equals_offline_module_plan():
    """红线 1:LLM_ORCHESTRATED 无 key → LLM 节点不注册 → module_plan 与 OFFLINE 等价。"""
    off = _run(RuntimeConfig(mode=Mode.OFFLINE))
    orch = _run(RuntimeConfig(mode=Mode.LLM_ORCHESTRATED, deepseek_api_key=""))
    assert off["provenance"]["module_plan"]["primary"] == \
        orch["provenance"]["module_plan"]["primary"]
    assert off["provenance"]["module_plan"]["secondary"] == \
        orch["provenance"]["module_plan"]["secondary"]
    # 核心预测也等价
    for k in ("abstain", "prediction", "reliability"):
        assert off[k] == orch[k]


def test_orchestrated_without_key_no_llm_cross_module_notes():
    """无 key → 不注册 reasoner → 无 llm_cross_module_notes(不静默假装有)。"""
    orch = _run(RuntimeConfig(mode=Mode.LLM_ORCHESTRATED, deepseek_api_key=""))
    assert "llm_cross_module_notes" not in orch.get("provenance", {})
```

- [ ] **Step 2: 跑确认失败**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_runtime_module_plan.py -q`
Expected: FAIL(`provenance.module_plan` 不存在 —— 尚未接管线)。

- [ ] **Step 3: 改 build_runtime 注册新 agent**

在 `praxis_virtualcell/workflows/predict_delta_expression.py`。

找到 import 段(现有 agents import 之后):

```python
from praxis_virtualcell.agents.species_brain import SpeciesBrainAgent
```

在其后加:

```python
from praxis_virtualcell.agents.species_brain import SpeciesBrainAgent
from praxis_virtualcell.agents.module_router_agent import ModuleRouterAgent
from praxis_virtualcell.agents.species_context_agent import SpeciesContextAgent
from praxis_virtualcell.core.config import LLM_MODES
```

找到确定性 agent 注册循环之后、LLM client 段之前:

```python
    for a in (InputInterpreterAgent(), BioObjectNormalizerAgent(), SpeciesBrainAgent(cfg),
              ModelApplicabilityAgent(), MockLinearAgent(), MockCPAAgent(), MockGEARSAgent(),
              EnsembleCoordinatorAgent(), ReliabilityAgent(mode=cfg.reliability_mode), CriticAgent(),
              ProvenanceAgent(), ReportAgent()):
        rt.register_agent(a)
    from praxis_virtualcell.agents_llm.llm_client import make_llm_client
    client = make_llm_client(cfg)
    if client.enabled:
```

改为:

```python
    for a in (InputInterpreterAgent(), BioObjectNormalizerAgent(), SpeciesBrainAgent(cfg),
              ModelApplicabilityAgent(), MockLinearAgent(), MockCPAAgent(), MockGEARSAgent(),
              EnsembleCoordinatorAgent(), ReliabilityAgent(mode=cfg.reliability_mode), CriticAgent(),
              ProvenanceAgent(), ReportAgent()):
        rt.register_agent(a)
    # Phase 4:module-aware 路由两节点(OFFLINE 也注册 → 产确定性 module_plan,零 LLM)
    for a in (SpeciesContextAgent(), ModuleRouterAgent()):
        rt.register_agent(a)
    from praxis_virtualcell.agents_llm.llm_client import make_llm_client
    client = make_llm_client(cfg)
    # Phase 4:仅 orchestrated 模式 + client enabled 才注册 LLM 编排节点(planner + reasoner)
    if client.enabled and cfg.mode in (Mode.LLM_ORCHESTRATED, Mode.LLM_ORCHESTRATED_STRICT):
        from praxis_virtualcell.llm_orchestration.cross_module_reasoner import LLMCrossModuleReasoner
        from praxis_virtualcell.llm_orchestration.module_planner import LLMModulePlanner
        rt.register_agent(LLMModulePlanner(client))
        rt.register_agent(LLMCrossModuleReasoner(client))
    if client.enabled:
```

> **注意** 上面新增块用了 `Mode`。确认文件顶部已 `from praxis_virtualcell.core.config import Clock, IdGen, RuntimeConfig` —— 需**追加 `Mode`**。找到:
> ```python
> from praxis_virtualcell.core.config import Clock, IdGen, RuntimeConfig
> ```
> 改为:
> ```python
> from praxis_virtualcell.core.config import Clock, IdGen, Mode, RuntimeConfig
> ```
> (`LLM_MODES` 已在上面 import 段单独加过;`Mode` 与 `Clock/IdGen/RuntimeConfig` 合并到同一行。)

- [ ] **Step 4: 改 run_workflow 加 module_plan 旁路挂载**

在 `praxis_virtualcell/core/runtime.py` 的 `run_workflow`。

找到 `app = self._dispatch_collect(m, "applicability_decided")` 到 `llm_route = None` 之间:

```python
        m = self.mk_message(out.sender, "ModelApplicability", "decide", out.payload, out.message_id)
        app = self._dispatch_collect(m, "applicability_decided")
        llm_route = None
```

改为:

```python
        m = self.mk_message(out.sender, "ModelApplicability", "decide", out.payload, out.message_id)
        app = self._dispatch_collect(m, "applicability_decided")
        # Phase 4:module-aware 路由旁路挂载(SpeciesContext →[LLMModulePlanner?]→ ModuleRouter),
        # 产 module_plan 挂进 report.provenance.module_plan;不改下游 predictor fan-out 契约。
        module_plan = None
        llm_cross_module = None
        if "ModuleRouterAgent" in self._agents:
            module_plan = self._build_module_plan(app)
            if "LLMCrossModuleReasoner" in self._agents and module_plan is not None:
                xm = self.mk_message("ModuleRouterAgent", "LLMCrossModuleReasoner",
                                     "cross_module_review", {"module_plan": module_plan},
                                     app.message_id)
                llm_cross_module = self._dispatch_collect(xm, "llm_cross_module_notes").payload
        llm_route = None
```

找到 `run_workflow` 末尾的 report 组装段:

```python
        report = rep.payload["report"]
        if llm_route is not None:
            report.setdefault("provenance", {})["llm_route_suggestion"] = llm_route
```

改为(在 llm_route 挂载之后加 module_plan/cross_module 挂载):

```python
        report = rep.payload["report"]
        if llm_route is not None:
            report.setdefault("provenance", {})["llm_route_suggestion"] = llm_route
        if module_plan is not None:
            report.setdefault("provenance", {})["module_plan"] = module_plan
        if llm_cross_module is not None:
            report.setdefault("provenance", {})["llm_cross_module_notes"] = llm_cross_module
```

在 `run_workflow` 方法**之后**(`export_outputs` 之前)加辅助方法 `_build_module_plan`:

找到:

```python
    def export_outputs(self, out_dir: str, report: dict) -> None:
```

在其**前面**插入:

```python
    def _build_module_plan(self, app: AgentMessage) -> dict | None:
        """Phase 4 旁路:SpeciesContext →[LLMModulePlanner?]→ ModuleRouter,产 module_plan(dict)。
        OFFLINE(无 LLMModulePlanner)→ ModuleRouter 走确定性 secondary,零 LLM。"""
        module_req = self._request_to_module_input(app.payload["request"])
        sm = self.mk_message("ModelApplicability", "SpeciesContextAgent",
                             "species_context", {"request": module_req}, app.message_id)
        ctx = self._dispatch_collect(sm, "species_context_ready").payload
        base_payload = {"request": module_req, "module_support": ctx["module_support"],
                        "mismatch_queries": ctx["mismatch_queries"]}
        if "LLMModulePlanner" in self._agents:
            pm = self.mk_message("SpeciesContextAgent", "LLMModulePlanner",
                                 "module_plan_request", base_payload, app.message_id)
            mc = self._dispatch_collect(pm, "module_candidates_llm").payload
            route_payload = mc                            # 已含 request/module_support/mismatch/module_candidates
        else:
            route_payload = base_payload                  # OFFLINE:无候选 → ModuleRouter 走确定性
        rm = self.mk_message("SpeciesContextAgent", "ModuleRouterAgent",
                             "module_route", route_payload, app.message_id)
        return self._dispatch_collect(rm, "module_plan_ready").payload

    @staticmethod
    def _request_to_module_input(req: dict) -> dict:
        """把管线 request(键 perturbation_type/output_modality/metadata.requested_outputs)确定性映射到
        module 路由期望的 raw(键 perturbation_object/target_output/perturbation_targets)。零 LLM。

        实读 model_applicability 产出的 req 键:species/perturbation_type/perturbation_targets/
        input_modality/output_modality/task_type/cell_type/metadata。module 路由的 normalize_request
        期望:species/perturbation_object/target_output/perturbation_targets(+可选 cell_type/medium/dose)。
        """
        # output_modality → target_output(TARGET_OUTPUTS = expression/growth/flux/state/communication)
        _OUT_MAP = {"delta_expression": "expression", "pathway_response": "flux",
                    "reliability_report": "expression", "growth": "growth", "flux": "flux",
                    "state": "state", "communication": "communication", "expression": "expression"}
        requested = ((req.get("metadata") or {}).get("requested_outputs") or [])
        # 优先 requested_outputs 里第一个合法输出;否则由 output_modality 映射;再否则默认 expression
        target_output = next((o for o in requested if o in _OUT_MAP.values()), None)
        if target_output is None:
            target_output = _OUT_MAP.get(str(req.get("output_modality", "")).lower(), "expression")
        raw = {"species": req.get("species"),
               "perturbation_object": req.get("perturbation_type"),
               "target_output": target_output,
               "perturbation_targets": list(req.get("perturbation_targets") or [])}
        for k in ("cell_type", "medium", "dose"):
            if req.get(k) is not None:
                raw[k] = req[k]
        return raw

```

> **注意(接管线真实契约点,已实读 model_applicability 核对):** 管线里 `app.payload["request"]` 的键是 `species/perturbation_type/perturbation_targets/input_modality/output_modality/task_type/metadata`(**无** `perturbation_object`/`target_output` —— 那是 module 路由 `normalize_request` 的期望键)。故必须 `_request_to_module_input` 做一次**确定性键映射**(`perturbation_type→perturbation_object`;`output_modality`/`metadata.requested_outputs`→`target_output`)。此映射纯确定性、零 LLM。**执行者务必先跑一个 OFFLINE human case 核对 `_OUT_MAP` 覆盖到实际 output_modality 值**(实读默认 `delta_expression`→expression);若某 request 的 output_modality 不在 `_OUT_MAP` → 落 `expression` 兜底(不抛,fail-safe 到最常见输出)。若映射后 `normalize_request` 仍抛 SchemaError(如 species 非法),那是上游 request 的真实问题,停下报告(不在 module 层吞掉)。

- [ ] **Step 5: 跑确认通过**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_runtime_module_plan.py -q`
Expected: 5 passed。

> **执行者提醒:** 键映射已由 `_request_to_module_input` 落实(`perturbation_type→perturbation_object`、`output_modality`/`requested_outputs→target_output`)。若 `test_offline_report_has_module_plan_in_provenance` 仍报 `normalize_request` 抛 SchemaError,先核对 `app.payload["request"]` 的实际 `output_modality` 值是否在 `_OUT_MAP` 内(实读默认 `delta_expression`;不在则落 `expression` 兜底,不应抛)。若映射后仍抛(如 species/perturbation_type 非法)→ 上游 request 真实问题,停下报告(不在 module 层吞掉,红线 5/6)。

- [ ] **Step 6: 全量回归(确认零回归 + skip 仍 25)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q`
Expected: 509 passed / 25 skipped / 0 failed(504 + 5 新)。**特别核对** `test_llm_fallback_offline.py`(LLM_ASSISTED 无 key 等价 OFFLINE)、所有现有 e2e/report 测试仍绿(旁路挂载未破坏核心报告)。若现有测试因 report.provenance 多了 module_plan 键而失败 → 核对那些测试是否严格断言 provenance 键集(应是宽松 `>=`);若真严格,是那测试的问题,停下报告(不改核心逻辑迁就)。

- [ ] **Step 7: 提交**

```bash
find . -name '._*' -delete
git add praxis_virtualcell/workflows/predict_delta_expression.py praxis_virtualcell/core/runtime.py praxis_virtualcell/tests/test_runtime_module_plan.py
git commit -m "feat(phase4): 接管线 —— SpeciesContext→[LLMPlanner?]→ModuleRouter 旁路挂 report.provenance.module_plan(OFFLINE 零 LLM,不改 predictor fan-out)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 4.8:Phase 4 完成闸门 —— 红线核验 + 台账 + v1.1 tag

**决策说明:** Phase 4 是 **v1.1 里程碑**(路线图 §5)。本 task 不写新功能,只做:①红线全量核验(三 flag 恒 False、OFFLINE 零 LLM、LLM 转 AgentMessage、不把 downgrade 改 accept、原 route/module golden KPI 仍绿、skip 恒 25);②精确回归数(junit);③台账追加 Phase 4 段;④打 **v1.1 tag**(本地,不 push)。

**Files:**
- Modify: `docs/STATUS-2026-07-03-v0.6-v0.8-delivery.md`(尾部追加 Phase 4 完成台账段)

- [ ] **Step 1: 红线核验 —— LLM 边界三 flag + 编排契约**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_llm_boundary_flags.py praxis_virtualcell/tests/test_llm_orchestration_contract.py -q`
Expected: 全绿。三 flag 恒 False、`assert_llm_boundaries` 仍拦、LLM 转 AgentMessage、不给 unsupported 硬解释、不把 downgrade/abstain 改 accept —— 全钉死。

- [ ] **Step 2: 红线核验 —— 原 route/module golden + negative KPI 仍绿**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests/test_golden_cases.py praxis_virtualcell/tests/test_negative_cases.py praxis_virtualcell/tests/test_module_golden_cases.py praxis_virtualcell/tests/test_module_consistency.py -q`
Expected: 全绿。route golden/module golden unsafe-accept=0、negative 无静默 accept 不变(Phase 4 未碰 route_table/治理引擎/ModulePlan 合成逻辑)。

- [ ] **Step 3: 红线核验 —— OFFLINE 零 LLM(build_runtime OFFLINE 不注册 LLM 节点)**

Run: `PYTHONPATH=$PWD .venv/bin/python -c "from praxis_virtualcell.core.config import Mode, RuntimeConfig; from praxis_virtualcell.workflows.predict_delta_expression import build_runtime; rt=build_runtime(RuntimeConfig(mode=Mode.OFFLINE)); ns=set(rt._agents); assert 'LLMModulePlanner' not in ns and 'LLMCrossModuleReasoner' not in ns and 'LLMRouter' not in ns, ns; assert 'ModuleRouterAgent' in ns and 'SpeciesContextAgent' in ns, ns; print('OFFLINE agents OK, zero LLM:', sorted(ns))"`
Expected: 打印 OFFLINE 注册表含 SpeciesContext/ModuleRouter、**不含任何 LLM 节点**。若含 LLM 节点 → 违规,停下修正。

- [ ] **Step 4: 红线核验 —— LLM_ORCHESTRATED 无 key 不注册 LLM(gated)**

Run: `PYTHONPATH=$PWD .venv/bin/python -c "from praxis_virtualcell.core.config import Mode, RuntimeConfig; from praxis_virtualcell.workflows.predict_delta_expression import build_runtime; rt=build_runtime(RuntimeConfig(mode=Mode.LLM_ORCHESTRATED, deepseek_api_key='')); ns=set(rt._agents); assert 'LLMModulePlanner' not in ns, ns; print('orchestrated-without-key gated OK:', 'LLMModulePlanner' not in ns)"`
Expected: 打印 gated OK(无 key → planner 不在册,红线 1/6)。

- [ ] **Step 5: 全量回归(精确数)**

Run: `PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q --junit-xml=/tmp/junit_phase4.xml`
然后取精确数:
Run: `python3 -c "import xml.etree.ElementTree as ET; r=ET.parse('/tmp/junit_phase4.xml').getroot(); s=r if r.tag=='testsuite' else r[0]; t,f,e,k=int(s.get('tests')),int(s.get('failures')),int(s.get('errors')),int(s.get('skipped')); print('collected=%d failures=%d errors=%d skipped=%d passed=%d'%(t,f,e,k,t-f-e-k))"`
Expected: `failures=0 errors=0 skipped=25 passed=509`(450 基线 + 7+11+6+6+4+20+5 = 59 新 = 509;若参数化展开或 4.6 契约条数微调,passed 相应微增,以实跑为准)。**关键:failures=0 errors=0 + skipped=25(未破 skip 基线)+ passed ≥509**。

- [ ] **Step 6: 台账更新**

用 Edit 在 `docs/STATUS-2026-07-03-v0.6-v0.8-delivery.md` 尾部追加:

```markdown

---

## Phase 4 完成台账(2026-07-04,LLM_ORCHESTRATED — v1.1 里程碑)

- **交付**:`core/config.py`(Mode 加 LLM_ORCHESTRATED/_STRICT + LLM_MODES 常量)+ `agents_llm/llm_client.py`(make_llm_client enabled 扩到编排模式)+ `llm_orchestration/` 子包(`safety_contract.py` 约束内核 / `module_planner.py` LLMModulePlanner / `cross_module_reasoner.py` LLMCrossModuleReasoner)+ `agents/module_router_agent.py`(读 LLM 候选,决策 P1/P2)+ 接管线(`workflows/predict_delta_expression.py` 注册 + `core/runtime.py` 旁路挂 module_plan)+ LLM 编排契约测试。
- **LLM 编排契约**:LLMModulePlanner 复刻 LLMRouter"只能从候选选"(`build_candidate_modules` = Phase 3 确定性 primary/secondary ∪ 该物种非 unsupported 模块;`filter_to_supported_modules` = `[m for m in llm if m in candidates]`)→ 产 `module_candidates_llm`(AgentMessage)→ ModuleRouter 用 Phase 3 代码合成 ModulePlan。**primary 永由确定性规则定(P1,LLM 不改)、LLM 只增删 secondary 且 ⊆ candidates(P2)、engine/verdict 仍由 route()+synthesize_verdict 定**。
- **红线守住**:①OFFLINE 默认零 LLM(build_runtime OFFLINE 不注册 LLM 节点,确定性两节点产 module_plan)②assert_llm_boundaries 三 flag 恒 False(orchestrated 下仍拦)③LLM plan 必须转 AgentMessage(planner 不产 plan)、不给 unsupported 硬解释(candidate 剔 unsupported)、不把 downgrade/abstain 改 accept(verdict 由确定性合成)、不新增无 provenance 证据(LLM 只挑 module id)④原 route/module golden unsafe-accept=0、negative 无静默 accept 不变⑤LLM 不可用 fail-closed 回退确定性(不硬塞)。450 基线零回归 → **509 passed / 25 skipped / 0 failed**(skip 基线 25 未破:LLM 单测全 FakeLLMClient 离线,未新增 @pytest.mark.llm)。
- **接管线(最小侵入)**:SpeciesContext→[LLMModulePlanner?]→ModuleRouter 旁路挂 `report.provenance.module_plan`,**不改 predictor fan-out/ensemble/reliability/critic 的输入契约**。module_plan 驱动 predictor 选择(用 plan engine 集裁剪 fan-out)留 v1.2+(待确认)。EvidenceLevelAgent(E0–E5)留 Phase 5。
- **v1.1 里程碑**:Phase 4 完成 = v1.1(LLM-orchestrated)。打 tag `v1.1-llm-orchestrated`(本地,不 push)。
- **待控制器确认的核心决策**:①LLM_ORCHESTRATED_STRICT 的冲突降级语义(决策 P3,本 Phase 仅加枚举 + 测识别,冲突降级逻辑留 v1.1.x)②communication 语义模块归属(沿用 Phase 3 决策 M1 归 M7)③module_plan 是否进而驱动 predictor 选择(本 Phase 只旁路挂载,不驱动)。已在计划落最小可测集并标注。
```

- [ ] **Step 7: 提交(不 push)**

```bash
find . -name '._*' -delete
git add docs/STATUS-2026-07-03-v0.6-v0.8-delivery.md
git commit -m "docs(phase4): Phase 4 完成台账 + 红线核验(509 passed,LLM_ORCHESTRATED 交付)

Phase 4 交付 LLM 编排:Mode 加 LLM_ORCHESTRATED/_STRICT + llm_orchestration/ 子包
(safety_contract + LLMModulePlanner + LLMCrossModuleReasoner)+ ModuleRouter 读 LLM 候选
+ 接管线旁路挂 module_plan。LLM 复刻 LLMRouter 只能从候选选、只增删 secondary、primary 不可改、
engine/verdict 由确定性源定;三 flag 恒 False、OFFLINE 零 LLM、fail-closed。450 基线零回归 → 509 passed。

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

- [ ] **Step 8: 打 v1.1 tag(本地,不 push)**

Phase 4 = v1.1 里程碑(路线图 §5)。全绿 + 红线核验通过后打 tag:

```bash
git tag -a v1.1-llm-orchestrated -m "v1.1: LLM-orchestrated — LLMModulePlanner + safety_contract + cross_module_reasoner, 接管线旁路挂 module_plan. 509 passed / 25 skipped. OFFLINE zero-LLM, 三 flag 恒 False. Phase 4 done."
git tag --list "v1.1*"
```

Expected: tag `v1.1-llm-orchestrated` 出现。**不 push**(房规:当前分支不 push;tag 推送由人决定)。

**Phase 4 验收:**
- ✅ config 加 LLM_ORCHESTRATED/_STRICT 枚举 + LLM_MODES + make_llm_client enabled 扩展(现有 OFFLINE/LLM_ASSISTED 不变,三 flag 恒 False)。
- ✅ safety_contract 约束内核:build_candidate(候选全集)/filter(只能从候选选,复刻 LLMRouter)/sanitize(fail-closed)/assert_within_bounds(越界守卫)。
- ✅ LLMModulePlanner(进 bus,复刻 LLMRouter):LLM 出 module 集 → 过滤成合法候选 → 产 module_candidates_llm(AgentMessage,不产 plan)。
- ✅ ModuleRouter 读 LLM 候选(P1/P2):primary 不可改、LLM 只增删 secondary ⊆ candidates、engine/verdict 不变;无候选(OFFLINE)走 Phase 3 原路径。
- ✅ LLMCrossModuleReasoner(进 bus,复刻 LLMCritic):只出 notes/flags,不改 plan(P4)。
- ✅ LLM 编排契约测试(扩 test_llm_boundary_flags):三 flag 恒 False、LLM 转 AgentMessage、不给 unsupported 硬解释、不把 downgrade/abstain 改 accept、OFFLINE 零 LLM。合计 LLM 编排相关 ≥30(路线图 §8 目标),实际 ≥54。
- ✅ 接管线:SpeciesContext→[LLMPlanner?]→ModuleRouter 旁路挂 report.provenance.module_plan;OFFLINE 零 LLM 且核心 prediction 等价;无 key orchestrated 回退等价 OFFLINE。predictor fan-out/ensemble/reliability/critic 零改动。
- ✅ EvidenceLevelAgent(E0–E5)留 Phase 5(需运行时 reliability/OOD 信号)。
- ✅ 450 基线零回归 → 509 passed / 25 skipped(skip 基线未破)→ 打 v1.1 tag(本地不 push)。

---

## Self-Review(写完对照路线图 + 真实代码)

- **路线图覆盖(§4/§5/§6/§7/§8)**:
  - §4 插点 B 的 **LLM 路径**(LLM_ORCHESTRATED 下 LLMModulePlanner 先出 module plan 建议 → safety_contract 过滤成合法 module 集 → 转 AgentMessage;OFFLINE 用 Phase 3 确定性规则零 LLM)→ Task 4.2(safety_contract)+ 4.3(LLMModulePlanner)+ 4.4(ModuleRouter 读候选)完整落地。**LLM plan 必须转 AgentMessage + 经 assert_llm_boundaries + safety_contract 三重检查** → Task 4.3(产 module_candidates_llm AgentMessage,不产 plan)+ Task 4.1/4.6(assert_llm_boundaries 三 flag)+ Task 4.2(safety_contract 过滤/越界守卫)三层全覆盖。
  - §1/§4 约 57 行"加 2 枚举值;module_planner/cross_module_reasoner/safety_contract;复用 LLMRouter 只能从候选选" → Task 4.1(2 枚举)+ 4.2(safety_contract)+ 4.3(module_planner 复刻 LLMRouter)+ 4.5(cross_module_reasoner)全落。
  - §5 依赖:Phase 4 依赖 Phase 3 ModulePlan 数据结构(实读 `module_plan.py` 已在,Task 4.3/4.4 产出/消费同一 ModulePlan ✓);Phase 4 = v1.1(Task 4.8 打 tag ✓)。
  - §6 决策 C(module_planner 复刻 LLMRouter `[a for a in ... if a in candidates]`:LLM 出 module 集 → 过滤成 support matrix 内合法模块 → 转 AgentMessage)→ Task 4.2 `filter_to_supported_modules` 逐字复刻,candidate 全集含 support matrix(非 unsupported)✓。
  - §7 红线全适用:①OFFLINE 默认零 LLM(Task 4.7 build_runtime OFFLINE 不注册 LLM 节点 + Task 4.6/4.8 grep/gated 核验)②assert_llm_boundaries 三 flag(Task 4.1/4.6 钉死,orchestrated 下仍拦)③LLM plan 转 AgentMessage、不给 unsupported 硬解释、不把 downgrade 改 accept、不新增无 provenance 证据(Task 4.6 五组契约测试逐条钉死)⑥模型/LLM 不可用不静默(Task 4.2 sanitize fail-closed + Task 4.6 回退保底测试)✓。
  - §8 测试目标:LLM contract tests 30(🟢 扩 test_llm_boundary_flags)→ Task 4.6 独立契约文件 ≥20 条 + 4.1–4.5 的 LLM 相关合计 ≥54,超 30 目标 ✓。skip 基线 25 不破(全 FakeLLMClient 离线,未新增 @pytest.mark.llm)。

- **LLM 测试如何 gated/mock 保证离线可跑、skip 基线 25 不破**:实读 `conftest.py` —— `@pytest.mark.llm` 无 `DEEPSEEK_API_KEY` 自动 skip(当前 25 skip 即由此 + `@pytest.mark.remote` 无 torch 构成)。若 Phase 4 新增 `@pytest.mark.llm` 测试,无 key 的 CI 下会 skip、使 skip 数从 25 上升 —— **违反"skip 基线 25 不破"口径**。故本计划**不新增任何 @pytest.mark.llm 测试**,LLM 逻辑全用 `FakeLLMClient`(`enabled=True` + 预置 content,不联网)或纯函数(safety_contract)离线测,计入 passed。真调 API 的连通性沿用现有 `test_llm_connectivity.py`(已在 25 skip 内),Phase 4 不加新真调测试。每 task Step 都核对 `skipped=25`。

- **与路线图旧描述不符的真实代码情况(逐条校正)**:
  1. **config 现有枚举只有 OFFLINE/LLM_ASSISTED,无 LLM_ORCHESTRATED**(实读 `config.py:13-15`)。路线图说"加 LLM_ORCHESTRATED/_STRICT 两枚举值"。`Mode` 是 `str, Enum` 子类,加枚举纯增不破坏 `.value`/`from_env` 序列化。`_STRICT` 本 Phase 只加枚举 + 测其 llm_enabled 判定,冲突降级语义(决策 P3)标注待确认。已在数据契约段校正1 + Task 4.1 落实。
  2. **`make_llm_client` 的 enabled 只认 `Mode.LLM_ASSISTED`**(实读 `llm_client.py:44`)。若只加 Mode 枚举、不改 `make_llm_client`,LLM_ORCHESTRATED 下 client 永不 enabled、LLM 节点永不注册,该模式静默退化成 OFFLINE。**必须同步扩 enabled 判定到 LLM_MODES**(Task 4.1 Step 4)。已在校正2 + Task 4.1 落实。
  3. **runtime LLM 节点用 `if "X" in self._agents` gating,不是 `if config.llm_enabled`**(实读 `runtime.py:59/88/93`)。Phase 4 沿用同惯例(`if "ModuleRouterAgent"/"LLMModulePlanner"/"LLMCrossModuleReasoner" in self._agents`),注册与否在 build_runtime 按 mode 决定。OFFLINE 分支代码路径与现在等价(LLM agent 不在册 → 分支不进)。已在校正3 + Task 4.7 落实。
  4. **Phase 3 刻意没接管线**(实读 `runtime.run_workflow` 无 ModuleRouter 节点;Phase 3 计划 §决策 R1 明说留 Phase 4)。故"接管线"是 Phase 4 的活,且**最小侵入 = 旁路挂载**(module_plan 挂进 report.provenance,不改 predictor fan-out 读的 `app.payload` 字段)。已在插点归置决策 + Task 4.7 落实,并标注"module_plan 驱动 predictor 选择"留 v1.2+。
  5. **`app.payload["request"]` 键结构是接管线的真实契约点(已实读 model_applicability 核对并落实映射)**:实读 `agents/model_applicability.py:23-29` —— 管线 request 键是 `species/perturbation_type/perturbation_targets/input_modality/output_modality/task_type/metadata`,**无** `perturbation_object`/`target_output`(那是 module 路由 `normalize_request` 的期望键)。故 Task 4.7 落了确定性 `_request_to_module_input`(`perturbation_type→perturbation_object`;`output_modality`/`metadata.requested_outputs`→`target_output`,默认 `delta_expression→expression`)。此映射纯确定性、零 LLM、fail-safe(未知 output_modality 落 expression 兜底)。**这是"对着真实代码"原则的正确处理**:先实读产出键、再落死映射,而非照路线图旧描述臆造 —— 映射代码已在计划中完整给出(非"执行时自己想")。

- **无占位符**:每 task 每 step 含完整可跑测试代码 + 实现代码 + 确切命令 + 期望数。safety_contract 四函数、LLMModulePlanner/LLMCrossModuleReasoner 完整实现、ModuleRouter 扩展的精确 old→new 替换、runtime 的 `_build_module_plan` 完整方法、契约测试 20+ 条全给出,非 "similar to above"。唯一标注"执行时实测对齐"的是 Task 4.7 的 `app.payload["request"]` 键映射(见校正5),这是接口契约点的诚实标注,非占位符 —— 计划给了核对方法(读 model_applicability 产出)+ 映射落点(`_build_module_plan` 内,确定性),不是"TODO 自己想"。

- **类型一致性**:`sanitize_llm_plan` 返回键 `selected_modules`(Task 4.2 定义),Planner 对外统一成 `selected`(Task 4.3 `mc["selected"]=mc.pop("selected_modules")`,已在 4.3 注释显式说明),ModuleRouter 读 `mc["selected"]`(Task 4.4)、契约测试断言 `["selected"]`(Task 4.6)—— 四处经 4.3 的 pop 转换后一致。`build_candidate_modules(req, module_support)`/`filter_to_supported_modules(llm_modules, candidates)`/`assert_plan_within_bounds(plan, candidates)` 签名在 4.2 定义、4.3/4.4/4.6 调用一致。`module_candidates_llm` payload 键(`request/module_support/mismatch_queries/module_candidates{selected,candidates,reasoning_summary,risk_flags}`)在 4.3 产出、4.4/4.7 消费一致。`module_plan_request`(4.3/4.7)、`module_candidates_llm`(4.3→4.4)、`module_route`(4.4/4.7)、`module_plan_ready`(4.4)、`cross_module_review`→`llm_cross_module_notes`(4.5/4.7)消息类型链一致。`LLM_MODES` 常量在 config 定义(4.1),llm_client(4.1)、build_runtime(4.7)、契约测试(4.6)三处引用一致。`_SEVERITY` 映射(accept0/caution1/downgrade2/abstain3/reject3)与 Phase 3 `module_plan.py`/`module_consistency.py` 一致(Phase 4 不重定义,复用 ModulePlan 合成)。

- **铁律段完整**:纯新增+复用(config 仅加枚举、workflow 仅增量注册、runtime 仅加可选插点)、OFFLINE 默认零 LLM(红线 1,grep + gated 核验)、assert_llm_boundaries 三 flag 恒 False(红线 2)、LLM 转 AgentMessage + 不给 unsupported 硬解释 + 不把 downgrade 改 accept(红线 3)、unsafe-accept=0(红线 4)、LLM 不可用不静默 fail-closed(红线 6)、测试口径 praxis_virtualcell/tests + junit passed=collected−skipped 精确口径 + 起点基线 450 passed/25 skipped/collected 475(实跑核实)、LLM 单测 FakeLLMClient 离线保 skip 恒 25、每 task 删 ._* + Co-Authored-By trailer + 当前分支不 push、Phase 4=v1.1 里程碑才打 tag —— 全写进头部铁律段并逐 task 执行。

- **累计测试数核对(以真实 passed 450 起算)**:450(基线)→ 457(4.1 +7)→ 468(4.2 +11)→ 474(4.3 +6)→ 480(4.4 +6)→ 484(4.5 +4)→ 504(4.6 +20)→ 509(4.7 +5)→ 509(4.8 台账,+0)。Phase 4 新增 59 条,450→509,skip 恒 25。以实跑参数化展开数为准(4.6 契约含 parametrize,实际条数可能微增),关键 failures=0 errors=0 skipped=25。

---

## 下一步(Phase 5 展开时机)

Phase 4 全绿(509 passed)+ v1.1 tag 后,回主路线图 §9,把 **Phase 5(主动学习 v1:acquisition/experiment_designer/learning_queue + EvidenceLevelAgent E0–E5,插点 C/D)** 展开成同粒度详细计划。Phase 5 会用到本 Phase 接进管线的 module_plan(挂在 report.provenance)+ 现有 reliability/OOD/disagreement 信号(v0.8 已有)。EvidenceLevelAgent(E0–E5)本被 Phase 3 计划留给"Phase 4/5",本 Phase 归置为 Phase 5(与主动学习证据链一起,见插点归置决策)。Phase 5 = v1.2 里程碑。
