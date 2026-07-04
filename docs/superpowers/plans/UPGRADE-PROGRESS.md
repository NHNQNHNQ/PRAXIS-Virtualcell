# PRAXIS-VirtualCell v0.9→v1.3 升级进度台账(autopilot ledger)

> autopilot 每次触发**先读本文件**定位当前工作单元;完成一个单元后**更新本文件**。
> 与 git log / tag / 测试计数三方对账,不一致时以**实跑结果**为准(本文件只是索引)。

## Autopilot 配置

```yaml
branch: feat/v0.9-phase0-module-core     # 当前工作分支(每到版本里程碑可换新分支)
push_authorized: false                   # 未经用户授权不 push
pause_at_milestones: true                # 每到 v0.x 里程碑结束 loop 等人工审;设 false 则全自动直穿 v1.3
paused_for_review: false                 # 用户 2026-07-04 重启 loop=继续,已清除暂停闸,进 Phase 2
test_scope: praxis_virtualcell/tests     # 唯一测试口径(永不碰根 tests/ 的 ~1398 继承测试)
test_cmd: "PYTHONPATH=$PWD .venv/bin/python -m pytest praxis_virtualcell/tests -q"
```

## 里程碑

| 里程碑 | 完成条件 | 状态 | tag |
|---|---|---|---|
| v0.9 module core | Phase 0 + 1 完成并回归绿 | ✅ 完成(暂停等审) | v0.9.0 |
| v1.0 model-controlled | Phase 2 + 3 | 🔵 Phase 2 完成,待 Phase 3 | —(v1.0 tag 等 Phase 3) |
| v1.1 LLM-orchestrated | Phase 4 | ⬜ | — |
| v1.2 active-learning | Phase 5 | ⬜ | — |
| v1.3 public release | Phase 6 + 7 + 8 | ⬜ | — |

## 相位进度

| Phase | 详细计划文件 | 状态 | 备注 |
|---|---|---|---|
| 0 冻结基线 | 2026-07-04-phase0-1-module-core.md | ✅ 完成 | 287 passed/0 failed;实现+复核两 subagent 均过;纯新增未动源码 |
| 1 八模块 core + species profile | 2026-07-04-phase0-1-module-core.md | ✅ 完成 | 319 passed/0 failed;5 task 全过;红线闸门全绿;v0.9.0 tag |
| 2 ModelBroker + model_zoo | 2026-07-04-phase2-model-broker.md | ✅ 完成 | 7 task 全过两审;352 passed/25 skipped/0 failed;闸门红线四件套全绿;纯新增未碰内核;非里程碑不打 tag |
| 3 module-aware router | 2026-07-04-phase3-module-router.md | 🔵 进行中 | 计划已展开(98d8c95,8 task,352→450);SpeciesContext+ModuleRouter+ModulePlan+golden 60;Phase 3 完成=v1.0 里程碑 |
| 4 LLM_ORCHESTRATED | (待展开) | ⬜ | 依赖 Phase 3 ModulePlan |
| 5 主动学习 v1 | (待展开) | ⬜ | 依赖 Phase 1 证据/模块结构 |
| 6 公开模型接入 | (待展开) | ⬜ | GEARS/scGPT 在 .53 真跑,收编进 ModelBroker(fail-closed) |
| 7 自训模型第一批 | (待展开) | ⬜ | 依赖 Phase 2 broker 契约,可与 6 并行 |
| 8 网站 + Linux release | (待展开) | ⬜ | 增量扩前后端 |

## 任务级台账(仅当前 Phase 展开)

### Phase 0 ✅
- [x] Task 0.1 基线架构文档(71a722f)
- [x] Task 0.2 离线报告特征化测试(34ab03a)
- [x] Task 0.3 路由快照测试(964dc1b)

### Phase 1(进行中)
- [x] Task 1.1 八模块规范定义 modules.py(94a8a60;292 passed;实现+审查双通过)
- [x] Task 1.2 4 物种 module_support.yaml(27cd40d;306 passed;审查 APPROVED)
- [x] Task 1.3 ModuleRegistry(1fb4edc;312 passed;审查 subagent flake→控制器亲验)
- [x] Task 1.4 物种特异错配守卫测试(c7a5522;319 passed;闸门审查 APPROVED)
- [x] Task 1.5 全量回归 319 passed + MANIFEST 已覆盖 yaml + v0.9.0 tag(控制器执行)

### Phase 2 ✅ 完成(起点 319 → 352 passed / 25 skipped / 0 failed;闸门红线全绿,不打 tag)
> ⚠️ 口径:计划文件里各 task 标的 "N passed" 实为 pytest **collected 总数(含 25 skipped)**,是笔误。真实 passed = collected − 25。下面用真实 passed 口径,验收关注 **0 failed / 0 errors + 新增测试条数正确**。
- [x] Task 2.1 ModelZooRegistry + registry.yaml(0aa4632;+6 → 325 passed;spec 审 + 质量审双 APPROVED)
- [x] Task 2.2 ModelWrapper 契约(97f9784;+5 → 330 passed;spec 审 + 质量审双 APPROVED)
- [x] Task 2.3 GemWrapper 真模型证明契约(0df5e15;cobra 真跑 KO;+4 → 334 passed;spec 审 + 质量审双 APPROVED)
- [x] Task 2.4 ModelCache 本地缓存 + sha256 版本锁(87c236c;fail-closed;+5 → 339 passed;spec 审 + 质量审双 APPROVED)
- [x] Task 2.5 downloader 下载契约(31b3c09;远端 gated → requires_manual_fetch;零网络请求;+4 → 343 passed;spec 审 + 质量审双 APPROVED)
- [x] Task 2.6 ModelBrokerAgent 进 message bus(f939457;available→wrapper;缺依赖→fail-closed;+5 → 348 passed;spec 审 + 质量审双 APPROVED)
- [x] Task 2.7 self_trained training_card 校验 + Phase 2 完成闸门(a414927;+4 → 352 passed / collected 377;双 APPROVED;闸门全绿,不打 tag)

### Phase 3(进行中,起点基线 352 passed / 25 skipped;计划 98d8c95,8 task,累计 +98 → 450 passed 达路线图地标)
> ⚠️ 口径同上:计划标 "N passed" 为 collected 含 skipped;真实 passed = collected − 25。验收认 0 failed/0 errors + 新增条数。
> 🔬 **v1.0 里程碑审查待确认(科学核心决策;规划 subagent 已落最小确定性集保证可测+fail-closed,不阻塞执行)**:M1 primary/secondary 模块选取规则(communication 暂归 M7;secondary 仅 growth/flux+human/mouse 加 M3,更细规则待定);M3 mismatch query 推导(bacteria+降解语境→自噬、yeast+niche/communication→组织 niche)。到 v1.0 pause 时连同跑通的 golden 结果一起交用户拍板。
- [x] Task 3.1 ModulePlan 数据结构(1b72c39;白名单校验 + verdict 保守合成 + to_dict;+7 → 359 passed;spec 审 + 质量审双 APPROVED)
- [x] Task 3.2 SpeciesContextAgent(7174bae;插点 A,进 bus;8 模块 support/verdict + mismatch;+6 → 365 passed;spec 审 + 质量审双 APPROVED)
- [x] Task 3.3 module_rules 确定性规则(e08cd3b;primary/secondary 选取 + mismatch query,零 LLM;+10 → 375 passed;spec 审 + 质量审双 APPROVED)
- [x] Task 3.4 ModuleRouterAgent(3d1da8a + 修复 78d6581;插点 B 产 ModulePlan;+7 → 382 passed;spec 审 APPROVED + 质量审 CHANGES_REQUESTED→修复→控制器亲验关闭 mismatch 降级盲区)
- [ ] Task 3.5 module routing golden representative(4 物种×代表应用)+ 独立 runner + unsafe-accept KPI(+34 → 416 passed)
- [ ] Task 3.6 module routing golden safety(mismatch/negative-transfer/fail-closed);总 golden ≥60(+28 → 444 passed)
- [ ] Task 3.7 cross-module consistency 校验(G4 铺路,纯函数;+6 → 450 passed)
- [ ] Task 3.8 Phase 3 完成闸门 — 红线核验 + 台账 + **v1.0 tag**(本地不 push;+0 → 450 passed)

## 当前状态:Phase 3 进行中 — Task 3.1–3.4 完成(3.4 经修复+亲验),连做 Task 3.5(golden representative +34)

## 事件日志(每次 loop 追加一行)

- 2026-07-04 台账初始化;Phase 0 实现 subagent 已派出;基线 = 277 passed / 25 skipped。
- 2026-07-04 Phase 0 完成:实现 subagent DONE(3 commit,无断言迁就)+ 复核 subagent APPROVED(独立重跑 287 passed/0 failed,纯新增未动源码)。下一个:Phase 1 Task 1.1。
- 2026-07-04 Phase 1 Task 1.1 完成(94a8a60):实现 DONE + 审查 APPROVED(独立重跑 292 passed/0 failed,engines⊆ENGINES,bacteria M3 别名守住,变异测试证明有效)。下一个:Task 1.2。
- 2026-07-04 Phase 1 Task 1.2 完成(27cd40d):实现 DONE + 审查 APPROVED(306 passed/0 failed,4 物种 8 模块齐,生物学守卫变异测试有效)。审查非阻塞观察:`mitochondria`/`mammalian_cell_communication` 两条 mismatch 数据在但 1.2 未单独断言——**由 Task 1.4 的 registry 守卫测试(_MISMATCH 4 条全测)关闭**。下一个:Task 1.3 registry。
- 2026-07-04 Phase 1 Task 1.3 完成(1fb4edc):实现 DONE(312 passed/0 failed;实现诚实指出计划 Step4 "7 passed" 是笔误、实为 6 测试,未编造凑数——已修计划为 6)。审查 subagent 异常返回(0 工具调用 flake)→ **控制器亲自独立核实**:junit 312 passed/0 failed、registry 契约逐条正确(verdict 映射/未知物种→unsupported→reject/未知模块→KeyError/matrix 4×8/mismatch/别名)、纯新增(仅 2 文件)。接受。下一个:Task 1.4。
- 2026-07-04 Phase 1 Task 1.4 完成(c7a5522):实现 DONE(319 passed;4 条 mismatch 守卫全测)。闸门审查 subagent APPROVED:Task 1.4 纯新增 + Phase 1 红线全绿(内核源码零改动、根 tests/ 未碰、LLM 边界 6 passed、golden+negative 38 passed、baseline 10 passed)。非阻断观察:test_unsupported_modules_reject 当前空转(4×8 矩阵暂无 unsupported 条目)。
- 2026-07-04 **Phase 1 完成 → v0.9 里程碑**:控制器执行 Task 1.5(最终回归 319 passed/0 failed/25 skipped;MANIFEST recursive-include *.yaml 已覆盖 module_support.yaml;打 v0.9.0 tag)。pause_at_milestones=true → **暂停等人工审查**。下一个:Phase 2(重启 loop 后先展开详细计划)。
- 2026-07-04 用户重启 loop=继续 → 清除 paused_for_review。派规划 subagent 展开 Phase 2(ModelBroker + model_zoo)详细计划,骨架 7 task:registry.yaml+loader / ModelWrapper(扩 PredictorAgent + declare_scope + estimate_uncertainty)/ GemWrapper(真模型)/ cache+版本锁 / downloader(远端 gated fail-closed)/ ModelBrokerAgent(bus,缺模型不静默 accept)/ training_card + 闸门。
- 2026-07-04 loop 再触发:确认 Phase 2 详细计划已提交(2a4a9a4,7 task 完整可执行,代码无占位符)。控制器实跑全量回归 junit `tests=344 failures=0 skipped=25`。台账填入 Phase 2 七 task 清单。派实现 subagent 执行 Task 2.1(ModelZooRegistry)。
- 2026-07-04 Task 2.1 实现完成(0aa4632):实现 subagent DONE(纯新增 4 文件 211 insertions/0 deletions,未碰内核)。**口径校正**:上一行的 junit `tests=344` 是 **collected 总数(含 25 skipped),非 passed**;真实基线 = **319 passed / 25 skipped**(与 commit 69a5cc7、里程碑表三方一致)。计划文件把 collected 误标成 "passed",实现 subagent 诚实指出并按真实值报数(+6 → 325 passed),未改代码凑数。台账各期望数已改回真实 passed 口径。派 spec 合规审 + 代码质量审(并发)。
- 2026-07-04 **Task 2.1 两审通过**:spec 合规审 APPROVED(独立重跑 325 passed/0 failed,6 断言点全覆盖无弱化,4 文件全 `A` 纯新增,`_validate` 全路径 raise);代码质量审 APPROVED(fail-closed 主路径逐条实测真拦得住无逻辑漏洞,6 测试非空转,风格与 biological_modules/registry.py 一致)。**质量审 4 条可选建议(非阻塞)**:①`_validate` 未防 entry 非 dict(int→TypeError 而非 ValueError)②models 顶层非 dict 未防 ③空文件静默加载 0 条(可接受)④by_module 用 MODULES、_validate 用 MODULE_ORDER(实测恒等,隐性耦合)。**处理决定**:②③④当前无实际问题,记为观察;**①留到 Task 2.7 扩 _validate 加 training_card 校验时顺带补一行 `isinstance(entry, dict)` 守卫 + 测试**(避免额外 commit,符合"不过度 error handling")。连做 Task 2.2(ModelWrapper 契约)。
- 2026-07-04 **Task 2.2 两审通过**(97f9784,+5 → 330 passed/0 failed):spec 合规审 APPROVED(3 文件全 `A` 与计划逐字节一致,5 断言点全覆盖,契约正确:declare_scope abstractmethod / uncertainty None→available=False / 越界 mouse→rejected+prediction=None 靠父类 handle);代码质量审 APPROVED(未破坏父类 fail-closed/retrieve-before-predict 契约,无 None 透传漏洞,5 测试真触发路径非空转)。**质量审 2 条非阻塞建议(记为观察)**:①`estimate_uncertainty` 默认实现忽略传入 `prediction` 参数、二次调 run_prediction(根因:契约里 prediction 子字典不含 uncertainty;真实高成本模型如 GEARS 会覆写此方法不走默认,实际影响小;Phase 3/6 接真模型时若成实际问题再重构契约)②一处测试断言偏宽松。均不在 Phase 2 改。连做 Task 2.3(GemWrapper 真模型)。做 chore commit 把 2.1/2.2 台账勾选 + 计划口径修正落盘(ca11b09)。
- 2026-07-04 **Task 2.3 两审通过**(0df5e15,+4 → 334 passed/0 failed;cobra 真跑非 skip):spec 合规审 APPROVED(2 文件逐字一致纯新增 +96 行,4 断言点全覆盖,GemWrapper 真 extends ModelWrapper);代码质量审 APPROVED(round(None) 崩溃点已守、estimate_uncertainty 覆写诚实标 deterministic_fba、缺 cobra/SBML 不静默变可用、4 测试真跑真断言非空转)。真跑 KO 实证:b0720 essential=True、ZZZ_notagene in_model=False/growth=None 不虚构。**质量审 2 条非阻塞建议(记为观察)**:①run_prediction 与 estimate_uncertainty 的 uncertainty 结构不同构(两条独立契约路径,非 bug)②test_uncertainty_contract 断言偏弱(只断 "available" in unc,未断 method)。均不在 Phase 2 改。连做 Task 2.4(ModelCache + sha256 版本锁);台账 2.3/2.4 勾选留待一起 chore commit。
- 2026-07-04 **Task 2.4 两审通过**(87c236c,+5 → 339 passed/0 failed):spec 合规审 APPROVED(2 文件逐字节一致纯新增,5 断言点全覆盖含 sha256_mismatch 铁律,未改 config);代码质量审 APPROVED(sha256 分块读/大小写一致/None 跳过,fail-closed 无漏洞:目录/断链符号链接/空文件/篡改/缺失全判不可用,5 测试纯 tmp_path 非空转)。**质量审 2 条非阻塞建议(记为观察)**:①路径穿越(model_name/asset 含 `..` 或绝对路径逃逸 root,但来自白名单校验的 registry 非外部输入,风险低)②test_missing_asset 断言 "missing" 分支永不命中(非 bug,可收紧)。均不在 Phase 2 改(符合"不过度防御")。连做 Task 2.5(downloader 下载契约);做 chore commit 落盘 2.3/2.4 台账勾选(a504e91)。
- 2026-07-04 **Task 2.5 两审通过**(31b3c09,+4 → 343 passed/0 failed):spec 合规审 APPROVED(2 文件逐字节一致纯新增,4 断言点全覆盖含 remote gated 核心,grep 确认零真实网络请求);代码质量审 APPROVED(四 scheme 互斥、split maxsplit=1 无坑、_REPO_ROOT parents[2] 实证指向 repo 根、fail-closed 无漏洞、local 资产 iMM904.xml.gz 真实存在故非空转)。**1 条非阻塞建议(记为观察)**:local: 分支对 rel 未防空/绝对路径——与 Task 2.4 路径穿越建议**同源**(cache.py + downloader.py 都从受控 registry 拼路径,过 schema 校验非外部输入),归并为一条:Phase 6 若引入不可信 source 再统一加路径守卫。连做 Task 2.6(ModelBrokerAgent 进 bus);台账 2.5/2.6 勾选留待一起 chore commit。
- 2026-07-04 **Task 2.6 两审通过**(f939457,+5 → 348 passed/0 failed):spec 合规审 APPROVED(2 文件逐字一致纯新增,5 断言点全覆盖,_resolve fail-closed 五步顺序正确);代码质量审 APPROVED(默认 available=False + 四分支短路 return + source 双重保险无漏洞,_dep_available gpu 恒判缺失、模块级可 monkeypatch,进 bus 契约规范 receiver=EnsembleCoordinator,5 测试非空转)。**1 条非阻塞建议(记观察)**:payload 缺 model_name 键时 get(None)→KeyError→"unknown model: None" 仍 fail-closed 安全,可单列 reason。**Task 2.1 建议① 重新评估**:此前记"留到 2.7 顺带补 entry 非 dict 守卫",重新权衡后**改为不做**(边缘情况:手写坏 yaml 裸标量仍会 fail、仅异常类型不统一;加它偏离 2.7 spec 且属额外 error handling,与"不过度防御"冲突)。Task 2.7 严格照计划做 training_card 校验(+4)。连做 Task 2.7;chore commit 落盘 2.5/2.6 台账勾选。
- 2026-07-04 **Phase 完成闸门分工说明**:Task 2.7 代码部分(training_card 校验 test + 扩 _validate + commit)由实现 subagent 做 + 两审;Phase 2 完成闸门核验(协议 §STEP 4:全量回归 + 红线核验 LLM 边界/golden/negative/baseline + MANIFEST + STATUS 文档 + 里程碑判断)由**控制器亲自**做。Phase 2 非里程碑 → 不打 tag,闸门后继续 Phase 3 展开。
- 2026-07-04 **Task 2.7 两审通过 + Phase 2 完成闸门(控制器亲验)**(a414927,+4 → 352 passed):spec 合规审 + 代码质量审均 APPROVED(_validate 纯 +9 追加未破坏现有逻辑,Task 2.1 六测试仍绿,training_card 校验 fail-closed 正确无漏洞)。**控制器独立闸门核验全绿**:①全量回归 352 passed/25 skipped/**0 failed/0 errors**(collected 377);②红线四件套(LLM 边界三 flag 恒 False + golden unsafe-accept=0 + negative 无静默 accept + baseline OFFLINE 零 LLM 产 report.md)共 54 tests 0 failed;③提交范围 v0.9.0→HEAD **根 tests/ 零触碰、core/predictors 零触碰、现有 agents 未改**(agents/ 仅新增 model_broker_agent.py)。STATUS 文档已追加 Phase 2 完成台账段。**Phase 2 非里程碑 → 不打 tag**(v1.0 tag 等 Phase 3)。**下一工作单元 = 用 writing-plans 展开 Phase 3(module-aware router,把 model_zoo/broker 接进 runtime 管线)详细 TDD 计划**,严格对着 Phase 1 modules.py + Phase 2 ModelBrokerAgent/ModelZooRegistry 真实接口。
- 2026-07-04 **可选建议观察项汇总(Phase 2 全 task,均非阻塞、未在本 Phase 改)**:①registry _validate 未防 entry 非 dict(边缘坏 yaml,重新评估决定不做);②estimate_uncertainty 默认实现忽略传入 prediction 参数二次推理(真实高成本模型覆写此方法规避);③cache/downloader 路径穿越守卫(source 来自受控 registry 非外部输入,Phase 6 接不可信源再加);④broker payload 缺 model_name 键当未知模型处理(仍 fail-closed 安全);⑤若干测试断言可收紧(uncertainty_contract/missing_asset 的 or 分支)。留待 Phase 3/6 需要时统一处理。
- 2026-07-04 **Phase 3 计划展开完成**(规划 subagent DONE,98d8c95,1569 行,8 task):module-aware router = SpeciesContextAgent(插点 A)+ ModuleRouterAgent(插点 B,产 ModulePlan)+ golden 扩到 60 + cross-module consistency,起点 352 → 累计 +98 → 450 passed(达路线图地标)。**质检亮点**:规划 subagent 用真实 route()+ModuleRegistry 预演全部 60 条 golden expect,发现并修正自己写错的 5 条期望值(human/mouse growth/flux 先命中代谢分支,ligand 不改结果),60/60 与真实代码一致;校正 5 处路线图旧描述(RouteDecision 有第 5 字段 reason、route() 需先 normalize_request、module→engine 在 MODULES[mid].engines、ModuleRegistry 真实方法名、broker 已存在留 Phase 4)。**归置决策**:SpeciesContextAgent 归 Phase 3(与 router 强耦合);EvidenceLevelAgent(E0–E5)留 Phase 4/5(需管线运行时 reliability/OOD 信号,Phase 3 刻意不接管线降低 v1.0 回归风险)。**待确认**:M1/M3 科学决策已落最小确定性集,标 v1.0 里程碑审查项(见 Phase 3 task 清单上方 🔬)。控制器核实计划头部铁律 + 数据契约 + Task 3.1 完整可执行。台账填入 Phase 3 8-task 清单。连做 Task 3.1(ModulePlan 数据结构,纯 dataclass 不涉 M1/M3 争议,安全起步)。
- 2026-07-04 **Task 3.1 两审通过**(1b72c39,+7 → 359 passed/0 failed):spec 合规审 APPROVED(2 文件逐行一致纯新增,7 断言点全覆盖,sys.modules 探测确认纯 dataclass 无 bus/LLM/torch/cobra 依赖);代码质量审 APPROVED(verdict 合成保守优先级无放宽漏洞、未知值兜底当最保守、白名单校验 __post_init__ fail-closed 无绕过、可变默认 field(default_factory)、to_dict 手写注入 overall_verdict 正确)。**2 条非阻塞建议(记观察)**:species_support/route_disposition/species_verdict 字段未做值域枚举校验(纯透传或 _SEVERITY.get(v,3) 兜底当最保守,fail-closed 安全非缺陷)——防御性增强留后统一。连做 Task 3.2(SpeciesContextAgent 插点 A);台账勾选累积待一起 chore commit。
- 2026-07-04 **Task 3.2 两审通过**(7174bae,+6 → 365 passed/0 failed):spec 合规审 APPROVED(2 文件逐字符一致纯新增,6 断言点全覆盖,进 bus + fail-closed 三红线落实);代码质量审 APPROVED(进 bus 契约规范与 ModelBrokerAgent 风格一致,8 模块 support/verdict/mismatch/display_name 全来自 ModuleRegistry 不自造,独立补测未知/空物种全 reject 不崩不静默,6 测试真读 yaml 有效)。**1 条非阻塞建议(记观察)**:`_reg._load()` 私有访问取 mismatch 表(registry 无枚举全部 mismatch 的公开 API 属合理权衡)——将来给 ModuleRegistry 加公开 mismatch_table(species) 收敛(需改 Phase 1 现有文件,留 Phase 3 之后)。连做 Task 3.3(module_rules,涉 M1/M3 最小确定性集);做 chore commit 落盘 3.1/3.2 台账勾选(3a6a1cb)。
- 2026-07-04 **Task 3.3 两审通过**(e08cd3b,+10 → 375 passed/0 failed):spec 合规审 APPROVED(2 文件逐字节一致纯新增,10 断言点全覆盖,M1/M3 规则表逐字照落地,6 module id 全∈MODULE_ORDER);代码质量审 APPROVED(pick_primary 穷举全组合合法+兜底完备、pick_secondary 排除 primary 正确、mismatch query 键在 yaml 真实声明链路闭合、AST 确认零 LLM、纯函数无副作用、10 测试有效)。**实现 subagent 诚实标注 2 个疑问(计划内、留 v1.0 里程碑审)**:①communication 归 M7(计划 M1 表自标待确认)②mismatch_query_for 只按 (species,module) 推导未看请求语义(与计划措辞略出入但属计划给定实现)——归入 M1/M3 待确认项。**1 条非阻塞建议(记观察)**:test_all_primaries_are_legal_modules 可扩穷举(已由审查穷举证明合法)。连做 Task 3.4(ModuleRouterAgent 插点 B,组装 ModulePlan);台账 3.3/3.4 勾选累积待一起 chore commit。
- 2026-07-04 **Task 3.4 实现 + spec 审 APPROVED,但代码质量审 CHANGES_REQUESTED(本会话首个非 APPROVED,控制器采纳)**(3d1da8a,382 passed):spec 合规审 APPROVED(2 文件逐字一致纯新增,7 断言点全在,组装链 + fail-closed 三链落实,零 LLM)。**代码质量审发现阻塞盲区**:`test_bacteria_autophagy_mismatch_downgrades` 空转——bacteria+growth 的 primary=cytoplasmic_metabolism,而 pick_primary/pick_secondary **从不产 M8(degradation_machinery)**,degradation entry 不在 plan、degs=[]、断言从不执行;更深:**bacteria autophagy mismatch 在当前 M1 规则下端到端不可达**,导致 **mismatch 降级(本 Phase 核心 fail-closed 红线)在 ModuleRouterAgent 端到端零有效覆盖**。两审分歧(spec 审认 vacuous 是计划明示 / 质量审认 fail-closed 盲区必修)→ **控制器裁决采纳质量审**(底层 synthesize/mismatch_query_for 各有单元测但集成路径无覆盖,计划注释接受了盲区不可接受)。**修复**:把空转的 bacteria autophagy 测试替换成可达的 **yeast niche state** 端到端 mismatch 降级测试(primary=M6→mismatch tissue_spatial_niche→verdict 非 accept;实现 subagent 端到端例子已证实可达),测试数保持 7、skip 保持 25;bacteria autophagy(M8)不可达归入 **M1/M3 v1.0 里程碑待确认项**(印证 Task 3.3 疑问②:mismatch 应按请求语义推导才能让 M8 可达)。质量审 2 条可选建议(记观察):route(req) 请求级不区分 mid 致 secondary 复用 primary 路由结果(当前不误 accept,建议 docstring 说明)、漂移检查排除 reject 无 note。派实现 subagent 修复后重审。
- 2026-07-04 **Task 3.4 修复完成 + 控制器亲验(盲区关闭)**(78d6581):修复 subagent 核实 M8 确不产(pick_primary/secondary 只产 M2/M3/M4/M6/M7)→ bacteria autophagy mismatch 端到端不可达属实;把空转测试替换成可达的 `test_yeast_niche_mismatch_downgrades`(yeast+niche state→primary M6→mismatch tissue_spatial_niche reject→verdict=abstain 实跑真实值,前置守卫防空转),测试数保持 7、skip 保持 25、全量 382 passed。**控制器亲验**:git diff 确认 module_router_agent.py 仅加注释(route() 请求级说明)无逻辑改动、新测试真断言(mismatch/verdict/overall 强断言 + 前置守卫)、独立重跑单文件 7 passed + 全量 382/25/0——盲区关闭,接受。**Task 3.4 达两审通过等价(spec APPROVED + 质量审问题已修复+亲验)**。修复 subagent 诚实校正:降级值是 abstain(engine=reject→route abstain 叠 species caution)非我描述的 caution,按实跑写断言未改源码。连做 Task 3.5(golden representative +34);做 chore commit 落盘 3.3/3.4 台账勾选。
