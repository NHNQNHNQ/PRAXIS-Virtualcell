# PRAXIS-VirtualCell v0.9→v1.3 升级进度台账(autopilot ledger)

> autopilot 每次触发**先读本文件**定位当前工作单元;完成一个单元后**更新本文件**。
> 与 git log / tag / 测试计数三方对账,不一致时以**实跑结果**为准(本文件只是索引)。

## Autopilot 配置

```yaml
branch: feat/v0.9-phase0-module-core     # 当前工作分支(每到版本里程碑可换新分支)
push_authorized: false                   # 未经用户授权不 push
pause_at_milestones: true                # 每到 v0.x 里程碑结束 loop 等人工审;设 false 则全自动直穿 v1.3
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
| 2 ModelBroker + model_zoo | (待展开) | 🟡 待展开(下一个,需重启 loop) | 需先 writing-plans 展开详细计划 |
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

## ⏸ 当前状态:v0.9 里程碑完成,已暂停等人工审查
- pause_at_milestones=true 生效。重启 `/loop`(同一条启动串)即从 Phase 2 继续。
- 重启后 autopilot 会先用 writing-plans 把 Phase 2(ModelBroker + model_zoo)对着真实代码展开成详细计划,再逐 task 执行。

## 事件日志(每次 loop 追加一行)

- 2026-07-04 台账初始化;Phase 0 实现 subagent 已派出;基线 = 277 passed / 25 skipped。
- 2026-07-04 Phase 0 完成:实现 subagent DONE(3 commit,无断言迁就)+ 复核 subagent APPROVED(独立重跑 287 passed/0 failed,纯新增未动源码)。下一个:Phase 1 Task 1.1。
- 2026-07-04 Phase 1 Task 1.1 完成(94a8a60):实现 DONE + 审查 APPROVED(独立重跑 292 passed/0 failed,engines⊆ENGINES,bacteria M3 别名守住,变异测试证明有效)。下一个:Task 1.2。
- 2026-07-04 Phase 1 Task 1.2 完成(27cd40d):实现 DONE + 审查 APPROVED(306 passed/0 failed,4 物种 8 模块齐,生物学守卫变异测试有效)。审查非阻塞观察:`mitochondria`/`mammalian_cell_communication` 两条 mismatch 数据在但 1.2 未单独断言——**由 Task 1.4 的 registry 守卫测试(_MISMATCH 4 条全测)关闭**。下一个:Task 1.3 registry。
- 2026-07-04 Phase 1 Task 1.3 完成(1fb4edc):实现 DONE(312 passed/0 failed;实现诚实指出计划 Step4 "7 passed" 是笔误、实为 6 测试,未编造凑数——已修计划为 6)。审查 subagent 异常返回(0 工具调用 flake)→ **控制器亲自独立核实**:junit 312 passed/0 failed、registry 契约逐条正确(verdict 映射/未知物种→unsupported→reject/未知模块→KeyError/matrix 4×8/mismatch/别名)、纯新增(仅 2 文件)。接受。下一个:Task 1.4。
- 2026-07-04 Phase 1 Task 1.4 完成(c7a5522):实现 DONE(319 passed;4 条 mismatch 守卫全测)。闸门审查 subagent APPROVED:Task 1.4 纯新增 + Phase 1 红线全绿(内核源码零改动、根 tests/ 未碰、LLM 边界 6 passed、golden+negative 38 passed、baseline 10 passed)。非阻断观察:test_unsupported_modules_reject 当前空转(4×8 矩阵暂无 unsupported 条目)。
- 2026-07-04 **Phase 1 完成 → v0.9 里程碑**:控制器执行 Task 1.5(最终回归 319 passed/0 failed/25 skipped;MANIFEST recursive-include *.yaml 已覆盖 module_support.yaml;打 v0.9.0 tag)。pause_at_milestones=true → **暂停等人工审查**。下一个:Phase 2(重启 loop 后先展开详细计划)。
