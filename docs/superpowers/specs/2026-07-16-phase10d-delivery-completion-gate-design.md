# P10.D 端到端 + 前端 e2e + 交付物 + 完成闸门 设计 spec

**定位**:Phase 10 收官单元。不是堆新功能,而是**把 A/B/C/C4 已建成的能力封装成可复现的端到端证据 + 论文/答辩交付物 + 一次诚实的完成闸门核验**。

**基线**:main = HEAD = `259266b`(C4 收官),分支 `feat/v0.9-phase0-module-core`。稳定基线 `-m "not llm"` = **896 passed / 40 skipped / 9 deselected / 0 failed**;裸口径(含 9 条 `@pytest.mark.llm` 真实网络测试)= **905 / 40 / 0**;phase10 单跑 = **247**。

**用户 2026-07-16 四拍板**:①一份大 spec 盖全 D(不分解);②门槛表照原表逐条核验 + 偏差单独记;③T10.7 前端 playwright 本周期一起做;④.53 远端项纳入本轮。

**权威来源**:roadmap `docs/superpowers/plans/2026-07-08-phase10-deep-validation-roadmap.md`(第六节 G2 五类 / 第七节 13 指标门槛 / 第八节目录 / 第九节六交付物 / 第十节红线)。⚠️ **roadmap 是 2026-07-08 写的,C1/C3/C4 执行期把好几条能力诚实收窄了** —— 见 §2.3,这是 D 最大的诚实性风险。

---

## 0. 当前状态摘要(READ FIRST —— 收官文档 / paper 作者从这里开始)

> **本节是摘要,非原始记录。** D 完成后此处更新为最终真相。§1–§9 是设计;执行期修正走末尾 §10(append-only,同 C4 惯例)。**冲突时以本节 + §10 最新修正为准。**

D 交付四部分(一份 spec,四个 task 组):

| 部分 | 内容 | 落位 | 本地/远端 |
|---|---|---|---|
| **D-A** | T10.3 后端端到端 16 case(8 单模块 + 8 跨模块) | `praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py` | 15 本地 + 1 `@remote`(.53) |
| **D-B** | T10.7 前端 playwright e2e(5 阶段 happy path + 6 tab) | `praxis_vc_react/e2e/*.spec.ts` + `playwright.config.ts` | 本地(不上 .53) |
| **D-C** | reports/phase10 六交付物 + 三脚本 | `scripts/phase10/*.py` + `reports/phase10/*.md` | 本地 |
| **D-D** | G2 门槛核验 + 完成闸门 + .53 远端亲验 | `reports/phase10/PHASE10_GATE.md` + 控制器 SSH | 本地核验 + .53 亲验 |

**D 的核心诚实性红线(贯穿全部)**:门槛表 13 指标里 **只有 ~7 条真达标**、**4 条被 C1-C4 收窄**、**2 条支撑不到**(`conflict detection ≥90%`、`LLM unsupported claim = 0`)、**3 条需 D 新建**(单模块正例率 / 多模块 workflow 率 / UI e2e)。**照原表逐条打绿勾 = 把 C4 抓了 11 次的过度声称搬进验收表。** 收窄项必须在验收表和 SUMMARY 里显著标为偏差,不打绿。

---

## 1. 目标与背景

### 1.1 D 要证明什么

roadmap 第二节四问:①确定性内核稳定?②系统会拒绝?③能跨模块组织?④知道自己不能做什么?D 用**可复现的端到端证据**回答,并封装成论文/答辩可引用的交付物。

**PRAXIS-VirtualCell 的论文主张边界(roadmap 第三节,D 必须守住)**:它**不是新的 SOTA 虚拟细胞预测模型**,而是**代码治理的多智能体操作层** —— 路由/schema 化 handoff/provenance/确定性重放/覆盖不足时 abstain。D 的交付物若把它写成"预测模型 benchmark"就是根本性过度声称。

### 1.2 为什么这是收官单元而非新工程

勘察(§2)证实:门槛表 13 指标 ~10 条已被 A/B/C/C4 落地。**D 真正的新建工程只有 2 块**:T10.3 后端跨模块 e2e(支撑"多模块 workflow 率")、T10.7 前端 playwright(支撑"UI e2e")。其余(六交付物、G2 核验、完成闸门)是**对既有证据的汇总 + 一次诚实核验**,不是新能力。这符合本项目"勘察挡下无收益工程"的传统(C1 证伪冲突检测方向、C3 证伪"40 条从零建")。

---

## 2. 勘察确立的事实地基(2026-07-16 四路并行勘察,全部实测/读码)

### 2.1 e2e harness 判断(D-A 的第一个坑)

`run_full_query(text)` 的 **OFFLINE 确定性解析无法设 `output_modality`/`requested_outputs`** → 只能路由到 `target_output=='expression'`,且只认**大写基因符号**(AHR/MYC/GATA1)。药名(小写 geldanamycin)、E.coli 位点(b0720)、growth/state/flux/communication 意图**全部 clarify-out 或落 mock**。

→ **决定:16 个 e2e case 用 `run_query(request_dict)` 或 `POST /api/jobs` 驱动**(先例:`tests/phase10/test_t10_5`)。`run_full_query(text)` 只保留 1-2 个 parse 集成 case(S2 human gene AHR + 一个 clarification_required 负例)。

### 2.2 16-case 可达性真相(诚实,不可粉饰)

**8 模块里只有 3 个有干净的单模块 primary 预测**(走完整管线 run_query):M2 genetic_hub、M4 cytoplasmic_metabolism、M7 stress_processor。其余:

| 模块 | 管线可达性 | e2e 断言对象 |
|---|---|---|
| M2 genetic_hub | ✅ mock donor accept(.53 才有真 GEARS) | prediction delta + module_plan primary accept |
| M4 cytoplasmic_metabolism | ✅ 真 cobra FBA(本地有 cobra) | prediction delta + gem_fba accept |
| M7 stress_processor | ✅ 真 state_scoring/embedding(IFN-β/drug) | prediction delta + accept |
| M3 mito_energy | ⚠️ **从不是 primary**,只作 mammalian growth/flux 的 secondary | module_plan secondary entry(2-entry plan) |
| M1/M5/M8 | ⚠️ **rule-based advisory**,基因集成员全 OOV → 请求自身**预测 abstain** | module_plan secondary advisory entry(caution_flags `rule_based:*` + `evidence_limited`,downgrade,**零 delta**)—— **不是**非 abstain 预测 |
| M6 cytoskeletal / communication / coculture | ❌ **run_query 完全不可达**(∉ REAL_ENGINES ∉ dispatch_runner,`_is_routable` 门掉 → module_plan=None + abstain) | 只能引擎级(run_spatial_niche_case)或 ModuleRouter 级测；管线级作**诚实 limitation**(module_plan=None) |

**两条 paper 级诚实事实(D 的 case 必须钉住)**:
1. **`module_plan.overall_verdict` 是路由级声明,可与引擎实际执行背离** —— 例:human gene→state 声明 `overall_verdict=='accept'` 但引擎 `abstain==True`(state_scoring 只 wire IFN-β ligand)。drug embedding 声明 `caution` 但引擎内部 CaseReport disposition 是 `accept`。**断言必须同时断路由声明与引擎结果,把背离本身文档化。**
2. **C1 跨模块一致性 gate 在自然输入上从不触发** —— `check_module_plan([])` 对所有确定性构造的 plan 返 `[]`(实测 `cross_module_consistency` 键在所有一致 plan 上缺席)。gate-触发 e2e **只能 monkeypatch `runtime.check_module_plan` 达成**(先例 test_t10_5)。诚实 e2e 断言 NO-OP 路径,**不得声称自然触发**。

**mock donor 词表(实测)**:IN-VOCAB(accept)= AHR/MYC/TP53/GATA1;OUT-OF-VOCAB(abstain)= SLC2A1/FASN/RPL5/PSMB5/KRAS/EGFR。M2 正例预测用 in-vocab。

**只有 1 个 case 需 .53**:S2b(M2 真实 GEARS，`models_used==['CaseRunner']`)。其余 15 个 Mac 全 offline 可跑(本地有 cobra+torch 但无 GEARS_CKPT)。

### 2.3 门槛表 13 指标真实状态(D 最重要的一张表)

| # | 指标 | 通过线 | 状态 | 偏差(照原表核验须单独记) |
|---|---|---|---|---|
| 1 | offline runtime tests | 100% | ✅ met | 隐含于 0 failed,无独立率计算 → D 补 junitxml 自动计 |
| 2 | message schema compliance | 100% | ✅ met | 无实质偏差(T10.1 固化) |
| 3 | provenance completeness | 100% | ⚠️ **narrowed** | C2:present-check(必需字段齐+per_call hash 齐),**非缺失率、非跨版本防篡改**;Gate B 防御断言罕触发 |
| 4 | trace replay success | 100% | ✅ met | "replay"=同请求重跑字节等价,**非从导出 bundle 回放** |
| 5 | 8 模块至少可运行 case | 8/8 | ✅ met(带限定) | **不得打"8/8 真实模型"**:引擎级真实仅 4 族(M2*/M3/M4/M7);M1/M5/M8=advisory;M6/emt/fate=limitation;M2 真实仅 .53 |
| 6 | 单模块正例成功率 | ≥90% | 🔨 **needs_new** | 无测得率;现为散点绝对通过 + 60 声明式路由 golden。D 建正例 corpus 计率,或诚实收窄为"4 真实引擎 e2e 全绿 + 60 路由 golden 全绿" |
| 7 | 多模块 workflow 成功率 | ≥90% | 🔨 **needs_new** | T10.3 未建;**且"多模块"须重定义**:C1 证伪多引擎 fan-out,route() 单出口一请求单 engine,"多模块"=module_plan primary+secondary **advisory 标注**(零 delta 纯路由),非多预测器证据链合并 |
| 8 | wrong accept rate | ≤5% | ✅ met(更严) | 实测 unsafe_accept **==0**(3 层拒绝 over 92 条 corpus);但 T10.4 原定 40 负例被 C2 挤占,corpus 来源须如实标 |
| 9 | unsupported abstain rate | ≥90% | ⚠️ **narrowed** | 绝对断言支撑、无测得率;T10.4 40 负例被 provenance gates 挤占 |
| 10 | **conflict detection** | ≥90% | ❌ **unsupported(最大收窄)** | 门槛表设想"5 类独立结果冲突检测";C1 证伪 → 实为 `module_plan` 内部一致性 gate、**罕触发、违规恒空靠 monkeypatch 触发**、无 20 条 conflict_cases。**paper 须明标非独立结果冲突检测,绝不打绿** |
| 11 | **LLM unsupported claim** | 0 | ❌ **unsupported** | memory 明记"C3 支撑不到须克制";narrative gate 仅 abstain 场景+仅浮点+hedge 词可绕、不验语境;**不得声称覆盖 §128 hypothesis→conclusion** |
| 12 | prompt injection bypass | 0 | ⚠️ **narrowed** | C3 结构性防御推论,非独立检测层、非测得 bypass 率;测试用 stub;对照组近乎恒真 |
| 13 | UI 5 阶段 e2e | 全通过 | 🔨 **needs_new** | 前端零测试栈;D-B 从零建 |

**G2 五类判据(第六节)**:①模型缺失 fallback ✅ met;②schema adapter ✅ met;③routing golden+confidence ⚠️ narrowed(**confidence 字段未实现**、每模块 20 条 routing examples 未严格达成);④per-call hash ✅ met;⑤critic claim-level + report 分层 ⚠️ narrowed(markdown 分节近似,非严格 4 路结构化字段)。

### 2.4 前端 5 阶段 + playwright 落地(D-B 地基)

**状态机宿主 = `AppShell.tsx`**:`Stage('ask'|'review'|'route'|'run'|'results')` + 集中 JobState。推进序列:Ask 点『解读任务 →』(**POST /api/parse**)→ Review 点『确认并继续 →』(纯前端组装)→ Route 点『下一步 →』(纯前端派生 expected plan)→ Run 点『开始运行 →』(**POST /api/jobs** 同步拿 job_id)→ Results(6 tab)。

- **无 `data-testid`** → 选择器走 `getByRole('heading'|'button'|'tab')` + `getByLabel('研究问题')` + `waitForResponse`(API 调用是阶段推进的硬证据)。
- **抗 CSS WIP**:e2e 零像素/CSS/视觉断言,只问"阶段标题出现 / 按钮可点 / API 发生 / tab 面板 h2 出现"。className/像素才受 CSS 改动影响,role/text/aria/id 不受。**WIP 冲突风险低**(用户只改 4 个 CSS,不动 .tsx 结构/文案/role)。固定 desktop 视口(1280×720)规避 StepperRail 响应式降级。
- **后端**:需真实后端(非 mock)—— `uvicorn praxis_vc_api.main:app` 单进程同源托管 `/api/*` + dist,offline 确定性,`PRAXIS_VC_RUNS` 指临时目录隔离 job 产物。playwright `webServer` 起它,`baseURL=http://127.0.0.1:8000`。
- 5 阶段的确切锚点/推进动作/playwright 步骤见 §4.B。

### 2.5 六交付物数据源(D-C 地基)

模块单一真源 = `biological_modules/modules.py::MODULE_ORDER`(M1..M8)。**机制:pytest 核心自带 `--junitxml`**(无需新插件)→ summarize 消费。**禁止从台账誊抄数字**(858 是误记孤例),summarize 必须实跑取数、显式标口径。

| 交付物 | 数据源 | 现可生成 | 依赖 |
|---|---|---|---|
| ① PHASE10_SUMMARY.md | junitxml + T10.2 + T10.4 + critic + UPGRADE-PROGRESS 事件日志 | 主体✅(UI/16case 段后填) | D-A/D-B |
| ② 8 模块覆盖表 | MODULE_ORDER + T10.2 + 台账定论 | ✅ | 无 |
| ③ 16 case 表 | D-A 的 T10.3 | ❌ | D-A |
| ④ 负例 abstain 表 | negative_cases/*.yaml + T10.4 + T10.2 abstain + T10.5 + T10.6 | ✅ | 无 |
| ⑤ trace/provenance audit bundle | export_trace_bundle 对代表请求调 run_query 导出 trace+provenance | ✅(基础版；权威 16 场景版依赖 D-A) | 部分 D-A |
| ⑥ UI 截图/录屏 | D-B playwright | ❌ | D-B |

### 2.6 .53 远端项(D-D 地基,用户拍板纳入本轮)

远端坐标 `zkyd@10.102.106.53`,项目 `/home/zkyd/data1/mzy/PRAXIS-virtualcell`,env `GEARS_CKPT` 门控。**6 个远端项**:

| 项 | 测试文件 | mark | .53 验什么 | 支撑门槛 |
|---|---|---|---|---|
| M2 GEARS 真 delta | `test_public_models_remote.py` | `@remote`×3 | GEARS-内部 delta 非 mock、scGPT==donor atol 1e-6 | #5 M2 真实腿 |
| norman_mean_baseline | `test_norman_mean_baseline_gated.py` | `@remote`×2 | ΔPearson pin 0.4615 复算、SelfTrained run_prediction | G2#1 自训真实性 |
| Linux/Docker smoke | `test_linux_docker_smoke.py` | `@integration`+skipif | docker build+run、/api/health、offline demo <60s | 部署可用性 |
| **MLBackedPredictor Gate A 不误伤** | `test_t10_4_provenance_gates.py` | 无独立 mark(端到端记 backlog) | 真 donor ML 跑 run_query 确认 Gate A 不 fail-closed 误伤真 ML | #3 provenance(C2 spec §5 风险2 预言实例) |
| donor ML 多智能体全链 | `test_ml_workflow_e2e.py` | `@remote` | MLBackedPredictor donor 真 ML e2e、norman score、abstain_gain | G2#1 真实预测器 |
| M2 fail-closed(反向) | `test_t10_2_module_contracts.py` | `skipif(_HAS_TORCH)` | .53 有 torch 时此条 skip,真推理改由 test_public_models_remote 承担 | #5 Mac fail-closed |

**M2 两端各半覆盖**:Mac 验 fail-closed、.53 验真推理。

---

## 3. 范围(用户 2026-07-16 四拍板)

**做**:
1. **D-A**:`test_t10_3_end_to_end_cases.py` —— 8 单模块 + 8 跨模块 e2e,`run_query` 驱动,断言诚实(§2.2 的可达性真相,advisory/limitation/背离逐条钉住)。
2. **D-B**:`praxis_vc_react/e2e/` + `@playwright/test` —— 5 阶段 happy path + 6 tab,role/text 选择器,uvicorn webServer。
3. **D-C**:三脚本(junitxml 编排 / SUMMARY 生成 / trace bundle 导出)+ 六交付物 `reports/phase10/`。
4. **D-D**:`PHASE10_GATE.md` 13 指标对账表(照原表 + 偏差单独记)+ 控制器 SSH .53 亲验 6 远端项。

**不做(明列)**:
- **不改内核/裁决/前端 WIP CSS**(红线 §6)。
- **不为凑门槛而伪造率**:无 corpus 的率(#6/#9)诚实收窄为绝对通过 + corpus 来源标注,不编百分比。
- **不建 benchmarks/phase10/*.yaml**(roadmap §8 设想的 5 个 case YAML)—— B/C 已把 case 写进 py 测试,回填 YAML 是重复劳动(同 C4 挡下无收益工程)。case 直接落 `test_t10_3`。
- （**grounding agent 一条声称已被控制器证伪,不列入不做项**:agent 报 `test_fate_case.py:49` 有 undefined `report` bug —— 实测该文件正常 collect 4 测试零 error,`report` 在 :28/:41 均 `report, dec = run_fate_case(...)` 正确赋值、:49 是 `report_lineages(db)` 正确调用。**bug 不存在**,D-A 复制 fate 真值无须避讳。此条留作"核实每条声称含自己 agent 的"示例。）
- **不上 .53 跑 playwright**(.53 node v12 build 不了;e2e 仅本地/CI)。

---

## 4. 架构设计

### 4.A｜D-A：T10.3 后端端到端 16 case

**落位**:`praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py`(t10_3 槽空;t10_7 已被 C4 占用,故前端 e2e 另落 §4.B)。

**harness**:`run_query(request_dict, config=RuntimeConfig(mode=Mode.OFFLINE))`(§2.1)+ 1 个 `run_full_query(text)` parse 集成正例(S2 AHR)+ 1 个 clarification_required 负例。

**8 单模块 case**(S1-S8,全部 grounded,§2.2 真相):

| case | 模块 | 输入(run_query) | 断言要点 | grounded_by | remote |
|---|---|---|---|---|---|
| S1 | M1 membrane advisory | human gene [FASN] expression | primary genetic_hub + membrane_system secondary advisory(rule_based+evidence_limited, downgrade)+ **请求 abstain**(FASN OOV) | membrane_system.json | no |
| S2 | M2 genetic_hub mock | human gene [AHR] expression | accept, reliability high, models_used==[Mock*], prediction delta, primary donor_predictor accept | test_module_router_agent | no |
| S2b | M2 real GEARS | human gene [AHR] expression **on .53** | models_used==['CaseRunner']（非 Mock）, gears delta 非 mock | test_gears_wrapper | **yes** |
| S3 | M3 mito secondary | human gene [MYC] growth | primary cytoplasmic_metabolism + M3 secondary(gem_fba downgrade)+ abstain(mammalian growth 未 wire) | test_mammalian_growth_has_m3_secondary | no |
| S4 | M4 cobra FBA | bacteria gene [b0720,b1136] growth | accept, models_used==[CaseRunner], prediction {'delta':[-1.0,-1.0]}(双 essential) | test_ecoli_gem_case | no |
| S5 | M5 biosynthetic advisory | human gene [RPL5] expression | primary genetic_hub + biosynthetic secondary advisory + abstain(OOV) | biosynthetic_network.json | no |
| S6 | M6 limitation | human medium [stromal_niche] state | **管线 limitation**:module_plan=None + abstain(spatial_niche 不可达)；引擎级另在 test_spatial_niche_case | test_spatial_niche_case | no |
| S7 | M7 state_scoring | human ligand [IFNB1] state | accept, models_used==[CaseRunner], prediction delta(ISG cohens_d ~2.5), state_scoring accept | test_cellstate_case | no |
| S8 | M8 degradation advisory+mismatch | bacteria gene [UBB] growth | primary cytoplasmic_metabolism + M8 secondary(mismatch=='caution' bacteria_autophagy + rule_based)+ abstain | degradation_machinery.json | no |

**8 跨模块 case**(X1-X8,§2.2):

| case | 场景 | 断言要点 | grounded_by |
|---|---|---|---|
| X1 | M4+M3 flux 正例 | human ligand [IFNB1] flux → 2-entry(cytoplasmic+mito, 均 pathway_scoring caution), prediction {'delta':[0.101,0.281]}, abstain=False | test_metabolic_tendency_case |
| X2 | M4+M3 growth 负例 | human gene_combination [MYC,KRAS] growth → 2-entry 均 downgrade, abstain, prediction None | module_safety.yaml |
| X3 | M2+M1+M5+M8 四模块 advisory | human gene [SLC2A1,RPL5,PSMB5] expression → 4-entry(primary+3 advisory secondary, MODULE_ORDER 序), 全 downgrade, abstain | 三个 gene_set json |
| X4 | M4+M8 bacteria mismatch | bacteria gene [UBB] growth → M4 primary + M8 secondary mismatch=='caution', abstain | mismatch_query_for |
| X5 | 负迁移 unroutable | bacteria gene [b0720] **expression** → abstain, models_used==[], **module_plan is None**(mammalian scRNA 禁用于 bacteria) | route_table negative_transfer |
| X6 | **C1 gate NO-OP** | human gene [MYC] growth ×3 → **`cross_module_consistency` 键缺席**(gate 不触发)+ 3 跑字节等价。**NOTE:gate 触发只能 monkeypatch,不可自然达成** | test_t10_5 + module_consistency |
| X7 | M2 跨物种 ortholog | mouse gene [GATA1] expression → primary genetic_hub caution(ortholog_required flag), mock prediction {'delta':[0.3]}, abstain=False | test_mouse_gene_expression_is_caution |
| X8 | **路由声明与引擎背离** | human gene [SNAI1] state → module_plan overall=='accept' **YET** abstain==True(state_scoring 只 wire IFN-β)。**同时断路由声明与引擎结果,文档化背离** | dispatch_runner state_scoring |

**共性断言**(每 case)：`llm_used_for_prediction is False`;返回结构走 §2.5 的 run_query 返回字段(structured_report/provenance/module_plan/reliability_decision)。**断言只用可观测的管线字段**(models_used、prediction.delta、module_plan.entries[*].engine/verdict),**不断引擎内部 CaseReport disposition**(run_query 顶层不暴露,§2.2)。

### 4.B｜D-B：T10.7 前端 playwright e2e

**落位**:`praxis_vc_react/e2e/*.spec.ts` + `praxis_vc_react/playwright.config.ts`(JS 栈,不进 pytest 的 phase10)。package.json 加 devDep `@playwright/test` + script `e2e`。

**setup**:`playwright.config.ts` → `baseURL=http://127.0.0.1:8000`,`testDir=./e2e`,`projects=[chromium]`,`webServer={command: uvicorn praxis_vc_api.main:app --port 8000(env PRAXIS_VC_RUNS=tmp), url, reuseExistingServer:!CI, timeout:120000}`。dist 过期时 webServer 前 `npm run build`。`npx playwright install chromium`。

**选择器策略(抗 WIP,§2.4)**:`getByRole('heading',{name})` 锚阶段标题、`getByRole('button',{name})` 锚推进按钮、`getByRole('tab',{name})` 锚 6 tab、`getByLabel('研究问题')` 锚 Ask 输入、`waitForResponse` 断 API 发生。零像素/CSS/className 断言。固定 1280×720。

**5 阶段 happy path**(1 条主 spec):

| 阶段 | 锚点(heading) | 推进动作 | API |
|---|---|---|---|
| Ask | `描述一次扰动实验` | `getByLabel('研究问题').fill('在 human 细胞敲 AHR')` → 点 `解读任务 →` | POST /api/parse |
| Review | `核对任务解读` | 点 `确认并继续 →`(species 已回填) | GET /api/options(失败静默降级) |
| Route | `预计涉及的功能模块`(+ amber 横幅 `这里是预期,不是实际结果。`) | 点 `下一步 →` | GET /api/modules |
| Run | `运行前确认` | 点 `开始运行 →` | POST /api/jobs |
| Results | `/^结果 · job/` | 6 tab 逐个点击断言面板 h2 | GET /api/reports/{id}[+/trace,/provenance,/module-plan] |

**6 tab 断言**(切换纯前端不发请求):报告→h2`概要`、预测→`结果可靠性`、模块路由→`路由摘要`、证据→`证据与审计`、运行轨迹→`运行轨迹`、溯源→`运行标识`。

**覆盖边界(诚实)**:e2e 只覆盖 5 阶段 happy path 推进 + 6 tab 可达;**不覆盖 abstain/failed 深层数值**(那是内核 pytest 的活)。完成门槛"UI 5 阶段 e2e 全通过"= 五跳全绿 + 6 tab 面板 h2 出现。可选补 1 条 `＋ 新建查询` 回 ask 的 spec。

### 4.C｜D-C：reports/phase10 六交付物 + 三脚本

**三脚本**(填 `scripts/phase10/` 骨架):
- `run_phase10_all.py`:编排全 `praxis_virtualcell/tests`(两口径 `-m "not llm"` + 裸口径,**显式标口径**),`--junitxml=reports/phase10/junit-*.xml`(pytest 核心自带),产机器可读指标。
- `summarize_phase10.py`:读 junitxml + MODULE_ORDER + T10.2/T10.4 → 生成 ①SUMMARY / ②8 模块覆盖表 / ④负例 abstain 表。**实跑取数,禁止誊抄台账数字。**
- `export_trace_bundle.py`:对代表请求集(D-A 的 16 case 请求 + 现有代表请求)调 `run_query` → dump trace+provenance+reliability → ⑤audit bundle 落 reports/phase10/。

**六交付物**(§2.5 数据源):落 `reports/phase10/{PHASE10_SUMMARY,PHASE10_FAILURES,PHASE10_TRACE_AUDIT,PHASE10_UI_E2E}.md` + 表格。**②④⑤① 主体先出,③⑥ 及 ①的 UI/16case 段待 D-A/D-B 完成回填。**

**SUMMARY 诚实叙事(强制)**:失败与修复叙事引 UPGRADE-PROGRESS 的 C1-C4 事件日志(含 C4 的 11 次过度声称、2 个新挖 500);§8 的 paper 明标 backlog 必须原样带上。

### 4.D｜D-D：G2 门槛核验 + 完成闸门 + .53 远端

**落 `reports/phase10/PHASE10_GATE.md`**:一张 §2.3 的 13 指标对账表(**原指标 → C1-C4 实际交付 → 状态[met/narrowed/unsupported/needs_new] → 偏差说明**)。**照原表逐条列(审计锚点),但状态列诚实标,收窄/支撑不到项绝不打绿勾。** 这是用户拍板"照原表核验 + 偏差单独记"的落地形式 —— 结构同 C4 的 §0(当前真相)+ §10(审计轨迹)。

**"多模块 workflow"重定义(写进 GATE)**:C1 证伪多引擎 fan-out → 指标 #7 语义 = "module_plan 多 entry 路由 + advisory 标注正确率",**不是多预测器证据链合并**。D-A 的 8 跨模块 case 全绿 = 该重定义指标达标。

**.53 远端亲验(控制器执行,同 M2 Task5 模式)**:SSH 到 .53,rsync 分支(不 push origin),设 GEARS_CKPT,跑 6 个远端项的 `@remote`/`@integration` 测试,亲验:M2 GEARS 真 delta 非 mock、MLBackedPredictor Gate A 不误伤真 ML、Docker smoke 10 passed、norman ΔPearson pin。**跑完 git checkout/rm 恢复 .53 干净,.53 生产 :8000 零扰动。** 结果落 GATE.md 远端段。

---

## 5. 关键风险与前置验证

### 5.1 风险:照原表打绿 = 过度声称(D 最大风险)

已由 §2.3 + §4.D 缓解:GATE.md 强制"状态列 + 偏差列",收窄项显著标注。**前置验证(D-D 第一步)**:控制器核对 GATE.md 的每条 met 声明是否有实测测试支撑,narrowed/unsupported 是否照 §8 措辞。**这是 D 的 opus final review 重点。**

### 5.2 风险:T10.3 断言写成"引擎内部"而非"管线可观测"

§2.2 已明:run_query 顶层不暴露 CaseReport disposition。**前置验证**:每个 case 的断言字段必须在 §2.5 的 run_query 返回结构里可查;引擎内部真值(cohens_d、disposition)只作 grounded_by 注释,不作断言。

### 5.3 风险:T10.7 被 CSS WIP 打红

§2.4 已明风险低(role/text 选择器不受 CSS 影响)。**前置验证**:D-B 首个 spec 跑通后,控制器在**当前 WIP CSS 状态**下复跑一次确认绿(证明选择器真抗 WIP)。

### 5.4 风险:.53 不可用阻塞 D 收官

**缓解**:15/16 后端 case + 全部前端 e2e + 六交付物主体本地可完成;.53 项做成独立 task(D-D 远端段),标 `@remote` 本地 skip,**不阻塞本地部分收官**。.53 段可延后单列(若远端不可用,GATE.md 标 pending + backlog)。

### 5.5 风险:summarize 誊抄台账数字(858 教训)

§4.C 已明:实跑 junitxml 取数。**前置验证**:summarize 产出的每个数字须能对上一次真实 pytest 运行,口径显式标(896 not-llm / 905 裸 / 247 phase10)。

---

## 6. 红线(全程不可破,继承 Phase 0-9 + C4)

1. 核心内核(`core/message.py`/`bus.py`/`agent.py`)+ 仓库根 `tests/` **零触碰**;`agents/reliability.py`/`critic.py` 裁决逻辑与数值**零改**。
2. **前端 WIP 全程隔离**:`praxis_vc_react/src/styles/{base,fonts,themes,tokens}.css`(M)+ `.claude/`、`.playwright-mcp/`、`string.jpeg`(??)**绝不 stage/touch/revert**。每次 `git add` 只显式列本 task 文件,禁 `git add -A`。**D-B 装 playwright 只改 package.json + 新建 e2e/ + playwright.config.ts,不碰 src/。**
3. 测试口径显式:`PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -p no:cacheprovider`,**绝不裸跑 pytest**。稳定基线 `-m "not llm"`。**报数必标口径**(858/859/850 与 238/239 两次血泪)。9 条 llm 网络测试挂时 FAIL 不 skip → 看退出码给假红。
4. OFFLINE 确定性字节等价;`llm_used_for_prediction` 恒 False。
5. **诚实不伪造**:门槛表收窄项绝不打绿;能力边界在交付物如实标(§8);不为凑率编百分比;实际与预期不符先报告。
6. 不 push origin;commit trailer 恒 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。里程碑 tag 本地不 push。
7. **.53 亲验**:rsync 分支不 push,跑完恢复 .53 干净,生产 :8000 零扰动(同 M2 Task5)。
8. **新依赖 `@playwright/test`**:仅前端 devDep,D2 已拍板;不进 python 依赖,不上 .53。

---

## 7. 测试与交付物落位

| 产物 | 路径 | 类型 |
|---|---|---|
| T10.3 后端 16 case | `praxis_virtualcell/tests/phase10/test_t10_3_end_to_end_cases.py` | pytest |
| T10.7 前端 e2e | `praxis_vc_react/e2e/*.spec.ts` + `playwright.config.ts` | playwright |
| 编排/汇总/导出脚本 | `scripts/phase10/{run_phase10_all,summarize_phase10,export_trace_bundle}.py` | 脚本 |
| 六交付物 | `reports/phase10/{PHASE10_SUMMARY,PHASE10_FAILURES,PHASE10_TRACE_AUDIT,PHASE10_UI_E2E,PHASE10_GATE}.md` + 表 | 报告 |

**变异要求**:T10.3 每个 case 的核心断言须证有牙(改坏路由/引擎则红)。**避免"路由声明 accept 就断言成功"的假绿** —— X8 专门钉背离,防这类空壳。

---

## 8. 诚实边界(交付物 / paper 引用须照此,继承 C1-C4 全部 backlog + D 新增)

**门槛表收窄项(GATE.md + SUMMARY 必须原样标)**:
- #3 provenance completeness = **present-check + 防御断言**,非缺失率/非跨版本防篡改。
- #7 多模块 workflow = **module_plan 多 entry 路由 + advisory**,非多预测器证据链合并(C1 证伪 fan-out)。
- #10 conflict detection = **module_plan 内部一致性 gate、罕触发、违规恒空**,**非独立结果冲突检测**;命名 `cross_module_inconsistency` 对外须加注。
- #11 LLM unsupported claim **不可打 =0**;narrative gate 仅 abstain + 仅浮点 + hedge 词可绕;**不得声称覆盖 §128 hypothesis→conclusion**。
- #12 prompt injection = **结构性防御推论**,非测得 bypass 率、非独立检测层。
- #5 8/8 可运行 = 带 advisory(M1/M5/M8)/ remote(M2)/ limitation(M6/emt/fate)限定,**非 8/8 真实模型**。
- #6/#9 无测得率 → 诚实收窄为绝对通过 + corpus 来源标注。
- G2#3 **confidence 字段未实现**;G2#5 report 分层是 markdown 近似非严格 4 路字段。

**C1-C4 累积 backlog(SUMMARY 叙事带上)**:per-call hash 非跨版本防篡改;Gate B 防御断言罕触发;Gate C cell_type 全越界窄门;narrative gate 第三类 gate;LLM 全入口守卫须表述为 grep 机械枚举核对(config 三 flag + 7 出口);抗注入结构性防御非独立层;C4 的 11 次过度声称 + 2 个新挖 500 + 两判据。

**D 主张边界**:PRAXIS-VirtualCell = 代码治理的多智能体操作层,**不是 SOTA 预测模型**;交付物不得写成"预测 benchmark"。真实引擎级覆盖 = M2(.53)/M3/M4/M7,其余 advisory 或 limitation。

**证伪记录**:grounding agent 曾报 `test_fate_case.py:49` undefined `report` bug —— 控制器实测证伪(文件正常 collect 4 测试),**bug 不存在**。留作"spec 事实声称须逐条核实、含自己 grounding agent 产出"的示例(本 Phase 已 11 次因未限定/未核实的声称栽跟头)。

---

## 9. Self-Review(占位符/一致性/范围/歧义)

- **占位符**:无 TBD。每个 case/阶段/交付物均落到具体文件+断言/锚点/数据源。
- **一致性**:§2.3 门槛状态与 §8 收窄清单逐条对应;§4.A 的 16 case 与 §2.2 可达性真相一致(M1/M5/M8 断 advisory entry 非预测、M6 断 limitation、X8 断背离、X6 断 NO-OP);§4.B 选择器与 §6.2 前端 WIP 红线一致(role/text 不碰 CSS);§4.C 禁誊抄与 §6.3 报数标口径一致。
- **范围**:四部分聚焦用户四拍板;benchmarks YAML / fate bug / .53 跑 playwright 明列不做。
- **歧义**:"多模块 workflow"已在 §2.3#7 + §4.D + §8 三处明确重定义为路由+advisory;"8/8 可运行"已明确带限定词;"conflict detection"已明确为 module_plan 内部一致性 gate。
- **诚实性**:D 最大风险(照原表打绿)由 §4.D 的强制偏差列 + §5.1 前置验证 + §8 收窄清单三重兜住。
