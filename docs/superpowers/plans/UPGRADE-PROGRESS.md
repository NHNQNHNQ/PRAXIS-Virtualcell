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
| v0.9 module core | Phase 0 + 1 完成并回归绿 | ⏳ 进行中 | — |
| v1.0 model-controlled | Phase 2 + 3 | ⬜ 未开始 | — |
| v1.1 LLM-orchestrated | Phase 4 | ⬜ | — |
| v1.2 active-learning | Phase 5 | ⬜ | — |
| v1.3 public release | Phase 6 + 7 + 8 | ⬜ | — |

## 相位进度

| Phase | 详细计划文件 | 状态 | 备注 |
|---|---|---|---|
| 0 冻结基线 | 2026-07-04-phase0-1-module-core.md | ✅ 完成 | 287 passed/0 failed;实现+复核两 subagent 均过;纯新增未动源码 |
| 1 八模块 core + species profile | 2026-07-04-phase0-1-module-core.md | 🟡 待执行(下一个) | 计划已就绪,Phase 0 已绿,可开始 |
| 2 ModelBroker + model_zoo | (待展开) | ⬜ | 需先 writing-plans 展开详细计划 |
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

### Phase 1(下一个,计划已就绪)
- [ ] Task 1.1 八模块规范定义 modules.py
- [ ] Task 1.2 4 物种 module_support.yaml
- [ ] Task 1.3 ModuleRegistry
- [ ] Task 1.4 物种特异错配守卫测试
- [ ] Task 1.5 全量回归 + 打包核对 + v0.9 tag

## 事件日志(每次 loop 追加一行)

- 2026-07-04 台账初始化;Phase 0 实现 subagent 已派出;基线 = 277 passed / 25 skipped。
- 2026-07-04 Phase 0 完成:实现 subagent DONE(3 commit,无断言迁就)+ 复核 subagent APPROVED(独立重跑 287 passed/0 failed,纯新增未动源码)。下一个:Phase 1 Task 1.1。
