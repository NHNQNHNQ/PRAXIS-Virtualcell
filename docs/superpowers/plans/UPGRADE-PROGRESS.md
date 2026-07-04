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
| v1.0 model-controlled | Phase 2 + 3 | ⬜ 未开始 | — |
| v1.1 LLM-orchestrated | Phase 4 | ⬜ | — |
| v1.2 active-learning | Phase 5 | ⬜ | — |
| v1.3 public release | Phase 6 + 7 + 8 | ⬜ | — |

## 相位进度

| Phase | 详细计划文件 | 状态 | 备注 |
|---|---|---|---|
| 0 冻结基线 | 2026-07-04-phase0-1-module-core.md | ✅ 完成 | 287 passed/0 failed;实现+复核两 subagent 均过;纯新增未动源码 |
| 1 八模块 core + species profile | 2026-07-04-phase0-1-module-core.md | ✅ 完成 | 319 passed/0 failed;5 task 全过;红线闸门全绿;v0.9.0 tag |
| 2 ModelBroker + model_zoo | 2026-07-04-phase2-model-broker.md | 🔵 进行中 | 计划已展开(7 task,起点基线 319 passed / 25 skipped 实跑核实);逐 task 实现+两审 |
| 3 module-aware router | (待展开) | ⬜ | 依赖 Phase 1 modules.py |
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

### Phase 2(进行中,起点基线 319 passed / 25 skipped / 0 failed)
> ⚠️ 口径:计划文件里各 task 标的 "N passed" 实为 pytest **collected 总数(含 25 skipped)**,是笔误。真实 passed = collected − 25。下面用真实 passed 口径,验收关注 **0 failed / 0 errors + 新增测试条数正确**。
- [x] Task 2.1 ModelZooRegistry + registry.yaml(0aa4632;+6 → 325 passed;spec 审 + 质量审双 APPROVED)
- [x] Task 2.2 ModelWrapper 契约(97f9784;+5 → 330 passed;spec 审 + 质量审双 APPROVED)
- [x] Task 2.3 GemWrapper 真模型证明契约(0df5e15;cobra 真跑 KO;+4 → 334 passed;spec 审 + 质量审双 APPROVED)
- [x] Task 2.4 ModelCache 本地缓存 + sha256 版本锁(87c236c;fail-closed;+5 → 339 passed;spec 审 + 质量审双 APPROVED)
- [ ] Task 2.5 downloader 下载契约(远端 gated → requires_manual_fetch;+4 → 343 passed)
- [ ] Task 2.6 ModelBrokerAgent 进 message bus(available→wrapper;缺依赖→fail-closed;+5 → 348 passed)
- [ ] Task 2.7 self_trained training_card 校验 + Phase 2 完成闸门(+4 → 352 passed / collected 377;不打 tag)

## 当前状态:Phase 2 进行中 — Task 2.1–2.4 两审通过,连做 Task 2.5(downloader 下载契约)

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
- 2026-07-04 **Task 2.4 两审通过**(87c236c,+5 → 339 passed/0 failed):spec 合规审 APPROVED(2 文件逐字节一致纯新增,5 断言点全覆盖含 sha256_mismatch 铁律,未改 config);代码质量审 APPROVED(sha256 分块读/大小写一致/None 跳过,fail-closed 无漏洞:目录/断链符号链接/空文件/篡改/缺失全判不可用,5 测试纯 tmp_path 非空转)。**质量审 2 条非阻塞建议(记为观察)**:①路径穿越(model_name/asset 含 `..` 或绝对路径逃逸 root,但来自白名单校验的 registry 非外部输入,风险低)②test_missing_asset 断言 "missing" 分支永不命中(非 bug,可收紧)。均不在 Phase 2 改(符合"不过度防御")。连做 Task 2.5(downloader 下载契约);做 chore commit 落盘 2.3/2.4 台账勾选。
