# PRAXIS-VirtualCell 升级 Autopilot 协议(loop 每次触发执行此文件)

> 你是本次升级的 **autopilot 控制器**。每次触发,你**推进一个有界工作单元**(用 subagent 干活),
> 然后按 §5 停止/继续规则决定是否 `ScheduleWakeup`。目标:v0.9→v1.3 全部里程碑打完、台账最新、红线全绿。
> 你的上下文可能在两次触发间被压缩——所以**每次触发都从台账 + git 重新定位**,不依赖记忆。

---

## STEP 1 — 定位(每次触发第一件事)

1. 读 `docs/superpowers/plans/UPGRADE-PROGRESS.md`(台账)。读顶部 **Autopilot 配置**(branch / push_authorized / pause_at_milestones / test_cmd)。
2. 读 `docs/superpowers/plans/2026-07-04-v0.9-v1.3-upgrade-roadmap.md`(权威:相位顺序 §5、已拍板决策 §6、红线 §7、事实校正 §3)。
3. `git branch --show-current` 确认在台账指定的工作分支;不在则 `git checkout` 过去。**绝不在 main 上干活;push_authorized=false 时绝不 push。**
4. 用台账 + `git log --oneline -15` 判定 **当前 Phase** 和 **下一个未完成工作单元**。
5. 若有正在后台跑的实现/审查 subagent(上次触发派的),**先等它/收它的结果**再决定下一步,别重复派。

## STEP 2 — 确保当前 Phase 有详细计划

- 若当前 Phase 在台账里标"(待展开)"、无 `docs/superpowers/plans/2026-*-phaseN-*.md`:
  - **本次触发的工作单元 = 用 `superpowers:writing-plans` skill 把该 Phase 展开成详细 bite-sized TDD 计划**,严格对着**当前真实代码**(不是假设;先读前一个 Phase 落地后的真实接口)。遵守路线图 §3 校正、§6 决策。
  - 写完 commit 计划文件,更新台账把该 Phase 的任务清单填进"任务级台账",然后跳到 §5(调度下次)。

## STEP 3 — 执行下一个未开始的 task(subagent-driven-development)

1. 从当前 Phase 详细计划取**下一个未勾选 task**。
2. 派**全新实现 subagent**(`general-purpose`),给它:场景说明 + 该 task 完整文本(或让它读该计划文件的这一节)+ 房规(venv `.venv`、`test_cmd`、commit 前删 `._*`、commit 末尾 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`、在工作分支提交、**不 push**)+ §RED-LINES。**别让它继承你的上下文。**
3. 收到 **DONE** → 派 **spec 合规审查 subagent**(比对 task spec:有没有少做/多做),通过后派 **代码质量审查 subagent**。任一发现问题 → 同一实现 subagent 修 → 重审,直到两审都过。
4. 收到 **BLOCKED / NEEDS_CONTEXT** → 按 subagent-driven-development 处理(补上下文重派 / 换更强模型 / 拆小 / 真 bug 则升级给人)。**绝不自己下场改源码迁就测试。**
5. task 两审通过 → 在台账勾掉该 task + 追加事件日志一行。一次触发做 1 个 task(小 task 可连做 2–3 个),然后 §5。

## STEP 4 — Phase 完成闸门(某 Phase 最后一个 task 完成时)

1. 跑全量回归:`test_cmd`。**必须 0 failed**;记录 X passed / Y skipped。
2. 核验**红线**(见 §RED-LINES),尤其:
   - OFFLINE 零 LLM 仍能产 report.md;`assert_llm_boundaries` 三 flag 仍 False;
   - golden **unsafe-accept=0**、negative **无静默 accept** 两 KPI 绿;
   - 只动了 `praxis_virtualcell/tests`,没碰根 `tests/` 的 ~1398 继承测试。
3. 更新台账相位状态。
4. 若这是一个**版本里程碑**(v0.9=P1后 / v1.0=P3后 / v1.1=P4后 / v1.2=P5后 / v1.3=P8后):
   - `git tag -a vX.Y.0 -m "..."`,台账里程碑表填 tag。
   - 若 `pause_at_milestones: true`(默认)→ **结束 loop**(不 ScheduleWakeup),给用户一段里程碑总结(做了什么、测试数、红线状态、下一里程碑),等人工审。
   - 若 `pause_at_milestones: false` → 继续(§5)。

## STEP 5 — 决定 继续 / 停止

**停止(不调用 ScheduleWakeup)** 当:
- 所有相位到 v1.3 完成且回归绿;或
- 任何红线被违反 / 测试 failing 且你无法自行修复;或
- subagent BLOCKED 需要人来拍板(如计划本身有误、要动科学核心决策);或
- 到达里程碑且 pause_at_milestones=true。
→ 停止时:把状态写进台账,给用户一段清楚的"停在哪、为什么、下一步"。

**继续(调用 ScheduleWakeup)** 否则:
- 更新台账,`ScheduleWakeup(delaySeconds≈1800, prompt=<原样的 loop 启动串>, reason="推进升级下一工作单元")`。
- 注:真正的推进触发往往是 subagent 完成时对你的自动再唤醒;1800s 只是兜底心跳,防 subagent 挂了 loop 卡死。

---

## RED-LINES(每次触发、每个 subagent 都必须守)

1. **离线优先零 LLM**:默认 `mode=OFFLINE`、`llm_enabled=False`,核心 case/预测/治理零 token 可跑。`assert_llm_boundaries` 三 flag(allow_llm_to_modify_core_decision / _prediction / _override_hard_rules)**永远 False**。
2. **LLM 不越权**:LLM 只做解析/路由建议/假设/润色;plan 必须转 `AgentMessage` 才能执行;不碰 prediction / hard-rule / learned-reliability 终决 / provenance / ledger;不给 unsupported module 硬解释;不把 downgrade 改 accept。
3. **测试口径唯一**:只在 `praxis_virtualcell/tests` 工作。根 `tests/` 的 ~1398 个继承自 PRAXIS-2 的 Web/Auth 框架测试**永不维护**——不跑、不修、不计数、不计入目标。
4. **不迁就**:测试与现有行为不符 → 若是特征化测试就 pin 真实值;若是真 bug 就 BLOCKED 升级。**绝不改源码逻辑让测试变绿。**
5. **增量复用,不推倒**:按路线图 §2 复用映射;不重写 PRAXIS 内核(bus / BaseAgent / 固定管线 / 治理 8 模块)。模块用数据驱动(不建 40 stub);species profile 落 `brains/virtualcell/*/module_support.yaml`(不建新目录);GEARS/scGPT 是"收编远端能力进 ModelBroker + fail-closed",不是从零训。
6. **提交纪律**:每 task 一提交,删 `._*`,加 Co-Authored-By trailer,工作分支提交,**不 push**(除非台账 push_authorized=true)。里程碑才打 tag。

## 一次触发的产出（自检）

- 要么:展开了一份 Phase 计划(并 commit);
- 要么:完成了 1–3 个 task(实现+两审+commit+台账勾掉);
- 要么:到里程碑,打 tag + 里程碑总结 + 按配置停/继续;
- 要么:BLOCKED,写清卡点停下。
- 台账**必须**被更新(至少追加一行事件日志)。
