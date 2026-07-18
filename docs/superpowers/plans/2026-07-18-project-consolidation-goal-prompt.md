# PRAXIS-VirtualCell 项目整理 /goal 提示词

> 用法：把下面代码块整体复制为新的 `/goal`。若环境不识别 `/goal`，作为普通指令发送也可。
>
> 权威计划：`docs/superpowers/plans/2026-07-18-project-consolidation-test-improvement.md`

```text
/goal 持续执行 docs/superpowers/plans/2026-07-18-project-consolidation-test-improvement.md，按“Phase A 迁入 APFS 并整理项目 → Phase B 建立测试基线 → Phase C 依据证据完善 → Phase D 同步 GitHub/本地/.53”的顺序推进，直到最终完成闸门通过或撞到硬门。

启动时先完整阅读计划、reports/phase10/PHASE10_GATE.md、docs/superpowers/plans/2026-07-17-frontend-full-e2e-test-plan.md，以及当前 git status/log/branch/tag/stash；把审计锚点 24475f2 与现场状态对比。若状态有变化，先更新 PROJECT-STATE，不照抄旧数字。

执行协议：
1. 每轮只取权威计划中当前阶段第一个未勾选的任务；先复核范围与保护项，再做到验收完成。第一轮必须先完成 A0 的 APFS bundle/clone 恢复硬门；后续所有修改只在 APFS clone 进行，T7 原仓库只读留档。
2. 阶段不可穿越：A5 未写 PHASE_A_COMPLETE，不得跑全面基线或顺手修 bug；B5 未写 PHASE_B_COMPLETE，不得修 lint、CI、版本或功能。A 阶段只允许窄验证，B 阶段只测量和归因，C 阶段才修复。
3. 每项开始前运行 git status --short；结束后检查 git diff、git diff --check、git diff --cached --name-only。只显式 git add 本任务文件，禁止 git add -A 和 git add .。
4. A–C 每项完成后更新计划勾选、PROJECT-STATE、SYNC-STATE 或 BASELINE 报告，做一个边界清楚的本地提交；不 push、不打 tag、不创建 PR、不 amend 其他任务提交。D 阶段只有在展示 refs/SHA/回滚清单并得到用户明确同步授权后，才可按清单 push 和快进 `.53`。若任务尚未通过验收，不提交假完成。
5. 测试报数必须写命令、解释器、工作目录、退出码、passed/skipped/deselected/failed 和口径。核心权威口径是 praxis_virtualcell/tests -m "not llm"；根 tests 单列 legacy，前端单列 typecheck/lint/build/e2e，远端/GPU/Docker 单列 pending 或 remote。
6. 失败先最小复现和归因。不得弱化断言、吞异常、扩大 exclude/noqa、无条件 skip 或修改科学行为来凑绿。发现真 bug，在 C 阶段先补失败回归，再做最小实现并跑相关测试和核心全量。
7. 默认 OFFLINE、零 LLM。不得读取/输出 .env 密钥，不跑真实网络 LLM 测试；LLM 永不修改 prediction、hard rule、reliability 终决、provenance 或 ledger。
8. 每次恢复/自动续跑都重新读取计划和 git 状态，从第一个未勾选任务继续；不要依赖聊天记忆，不重复已完成工作。

必须保护：
- 4 个未提交 CSS：praxis_vc_react/src/styles/base.css、fonts.css、themes.css、tokens.css。除 C3 主题专项外只允许只读检查，不修改、不 stage、不回滚。
- 未跟踪的 .claude/、.playwright-mcp/、string.jpeg，以及 stash@{0}。先分类，未经用户批准不删、不覆盖、不 pop/drop。
- 本地 main=v1.5.0、全部 tag、远端 tracking refs 和提交历史。不得 reset --hard、checkout --、clean、gc、rebase、force、删除 branch/tag。
- .git 内 AppleDouble sidecar 只记录风险；本 goal 不编辑 .git、不清理 sidecar。需要清理时先给出已验证备份与迁盘方案并停下等批准。
- 三端角色：GitHub main 是已发布真相源，本地 APFS clone 是开发真相源，.53 是运行/验证镜像；不得在 .53 直接开发或留下未回传的权威 commit。
- feature_schema_v0.3.0 等治理 artifact/model 版本是独立契约，不随产品版本机械升级。
- Phase 10 诚实边界：真实引擎级覆盖仅 4 族；narrowed/unsupported 没有新证据不得改绿，不得声称 SOTA。

允许自主完成：
- 只读审计、创建 docs 索引/状态/版本设计/runbook/测试报告；
- 在 APFS clone、任何整理提交之前创建 codex/project-consolidation 分支；
- 维护 docs/status/SYNC-STATE.md；在本地 fetch GitHub refs，`.53` 在 D 阶段获授权前只做 status/ref 只读核对，不在 `.53` fetch/checkout/pull；
- A 闸门之后运行本地 lint、pytest、npm、Playwright、wheel 检查；
- C 阶段按基线修复 lint、pytest marker、CI、版本 metadata、README、CLI 安装、前端 E2E 和包体问题；
- 安装项目已声明的本地开发依赖，但不得引入新的重型/付费/私有依赖，依赖变更必须独立提交并说明理由。

只在以下硬门停下：
1. 没有可用 APFS 目标，或 bundle、refs/stash、WIP、APFS clone 任一恢复校验失败；
2. 任何删除/覆盖用户资产、stash、分支/tag、数据或 .git 的动作；
3. D 阶段之前需要 push/PR/远端修改；D 阶段已经准备同步但还没有用户明确授权；
4. GitHub、本地或 .53 存在 dirty、未知提交、非 fast-forward 或 SHA 无法解释；
5. git fsck 出现 missing/corrupt object；
6. 发现计划外工作树变化或与 CSS WIP 重叠；
7. 测试数字无法解释，或修复需要改变科学裁决/可靠性数值/LLM 红线；
8. 需要私有 checkpoint、付费服务或 API key；
9. 需要改变论文结论或把 narrowed/unsupported 改成 met；
10. 所有本地可做任务和最终完成闸门均已完成。

三端同步协议：本地 feature branch 完成本地闸门 → push GitHub branch → CI → 经批准合入 GitHub main → 本地 main 只做 fast-forward → .53 只从同一 GitHub origin fast-forward 到已批准 SHA → 同时记录 local main、git ls-remote origin/main、.53 deployed SHA 和 tag。工作分支 intentionally ahead 可以存在，但必须记入 SYNC-STATE；未记录的 main/deployed SHA 差异一律视为 drift。禁止直接在 .53 改代码；远端测试失败回到本地修复后重走 GitHub。

撞硬门时不要继续试探性修改：更新计划/PROJECT-STATE/SYNC-STATE 为 BLOCKED，写清已完成项、原始命令与输出摘要、未改动的保护项、三端 SHA，以及需要用户拍板的唯一问题。正常完成时给出 Phase A/B/C/D 的提交列表、最终测试矩阵、GitHub/本地/.53 一致性证明和仍 pending 的科学项；若 D 未获授权，状态只能写 READY_TO_SYNC，不能写已同步。
```
