# PRAXIS-VirtualCell 项目整理 /goal 提示词

> 用法：把下面代码块整体复制为新的 `/goal`。若环境不识别 `/goal`，作为普通指令发送也可。
>
> 权威计划：`docs/superpowers/plans/2026-07-18-project-consolidation-test-improvement.md`
>
> 当前重启点：`D0_READ_ONLY_AUDIT_COMPLETE`；首次加入 D0 proposal 的 commit 只是 report anchor。最终候选必须取当前 approval handoff 明示的 clean branch-tip 40-hex，并核其 post-commit artifact；随后硬门是用户是否授权 D1a 仅 push exact candidate SHA。

```text
/goal 持续执行 docs/superpowers/plans/2026-07-18-project-consolidation-test-improvement.md，按“Phase A 迁入 APFS 并整理项目 → Phase B 建立测试基线 → Phase C 依据证据完善 → Phase D 同步 GitHub/本地/.53”的顺序推进，直到最终完成闸门通过或撞到硬门。

启动时先完整阅读计划、docs/status/PHASE-D0-SYNC-PROPOSAL-2026-07-18.md、docs/status/PHASE-C5-GATE-2026-07-18.md、docs/status/PHASE-C4-GATE-2026-07-18.md、docs/status/SYNC-STATE.md、docs/runbooks/REMOTE-SCIENCE-VALIDATION.md、reports/phase10/PHASE10_GATE.md，以及当前 git status/log/branch/tag/stash；把整理起点 24475f2、C3 证据 4106403、C4 证据 8ce42fe、C5 实现 038e747、C5 文档 d39b4a9、D0 report anchor、当前 clean branch tip 和最新 approval handoff 对比。若状态有变化，先更新 PROJECT-STATE，不照抄旧数字。

执行协议：
1. 每轮只取权威计划中当前阶段第一个未勾选的任务；先复核范围与保护项，再做到验收完成。A0–C5 已有 gate 时不得重做，D0 fresh ledger/提案也不得无故重做。先核 approval handoff 的 40-hex 等于 clean branch tip；若缺该 SHA 的双 wheel/clean-install handoff，只补这一本地验证。任何新 commit 都使旧 handoff 失效。证据齐全后停在 D1a 外部写入授权门。所有修改只在 APFS clone 进行，T7 原仓库只读留档。
2. 阶段不可穿越：A5 未写 PHASE_A_COMPLETE，不得跑全面基线或顺手修 bug；B5 未写 PHASE_B_COMPLETE，不得修 lint、CI、版本或功能。A 阶段只允许窄验证，B 阶段只测量和归因，C 阶段才修复。
3. 每项开始前运行 git status --short；结束后检查 git diff、git diff --check、git diff --cached --name-only。只显式 git add 本任务文件，禁止 git add -A 和 git add .。
4. A–C 每项完成后更新计划勾选、PROJECT-STATE、SYNC-STATE 或 BASELINE 报告，做一个边界清楚的本地提交；不 push、不打 tag、不创建 PR、不 amend 其他任务提交。D 阶段只有在展示 refs/SHA/回滚清单并得到用户明确同步授权后，才可按清单 push 和快进 `.53`。若任务尚未通过验收，不提交假完成。
5. 测试报数必须写命令、解释器、工作目录、退出码、passed/skipped/deselected/failed 和口径。核心权威口径是 praxis_virtualcell/tests -m "not llm"；根 tests 单列 legacy，前端单列 typecheck/lint/build/e2e，远端/GPU/Docker 单列 pending 或 remote。
6. 失败先最小复现和归因。不得弱化断言、吞异常、扩大 exclude/noqa、无条件 skip 或修改科学行为来凑绿。发现真 bug，在 C 阶段先补失败回归，再做最小实现并跑相关测试和核心全量。
7. 默认 OFFLINE、零 LLM。不得读取/输出 .env 密钥，不跑真实网络 LLM 测试；LLM 永不修改 prediction、hard rule、reliability 终决、provenance 或 ledger。
8. 每次恢复/自动续跑都重新读取计划和 git 状态，从第一个未勾选任务继续；不要依赖聊天记忆，不重复已完成工作。

必须保护：
- 原 4 个主题 CSS 已经 C3 验收并在 92ab4ee 提交；原恢复 patch 2c300a...aff7e 继续保留。不得把 T7 旧 WIP 覆盖回当前主题，也不得把它误记为原样提交。
- 未跟踪的 .claude/、.playwright-mcp/、string.jpeg，以及 stash@{0}。先分类，未经用户批准不删、不覆盖、不 pop/drop。
- 本地 main=v1.5.0、已有 tag、远端 tracking refs 和提交历史在 D0/D1a 前保持不变；只有对应 D1b/D1c/D2 精确授权才可新增 `v1.6.0` 或 fetch 明示 ref。不得 reset --hard、checkout --、clean、gc、rebase、删除/移动 branch/tag；唯一窄例外是 D1a/D1b 提案内绑定 exact ref 与 expected old SHA 的 `--force-with-lease`，它只作 compare-and-swap，必须先通过 old→candidate ancestry，绝不授权 non-FF/改写。
- .git 内 AppleDouble sidecar 只记录风险；本 goal 不编辑 .git、不清理 sidecar。需要清理时先给出已验证备份与迁盘方案并停下等批准。
- 三端角色：GitHub main 是已发布真相源，本地 APFS clone 是开发真相源，.53 是运行/验证镜像；不得在 .53 直接开发或留下未回传的权威 commit。
- feature_schema_v0.3.0 等治理 artifact/model 版本是独立契约，不随产品版本机械升级。
- Phase 10 诚实边界：真实引擎级覆盖仅 4 族；narrowed/unsupported 没有新证据不得改绿，不得声称 SOTA。

允许自主完成：
- 只读审计、创建 docs 索引/状态/版本设计/runbook/测试报告；
- 在 APFS clone、任何整理提交之前创建 codex/project-consolidation 分支；
- 维护 docs/status/SYNC-STATE.md；D0/D1a 前 GitHub 仅用 `ls-remote`，不改 tracking refs/FETCH_HEAD。本地与 `.53` fetch 只可在对应 D1c/D2 明确授权后使用提案列出的精确 refspec；`.53` 获授权前只做 status/ref 只读核对；
- A 闸门之后运行本地 lint、pytest、npm、Playwright、wheel 检查；
- C 阶段按基线修复 lint、pytest marker、CI、版本 metadata、README、CLI 安装、前端 E2E 和包体问题；
- 安装项目已声明的本地开发依赖，但不得引入新的重型/付费/私有依赖，依赖变更必须独立提交并说明理由。

只在以下硬门停下：
1. 没有可用 APFS 目标，或 bundle、refs/stash、WIP、APFS clone 任一恢复校验失败；
2. 任何删除/覆盖用户资产、stash、分支/tag、数据或 .git 的动作；
3. D 阶段之前需要 push/PR/远端修改；D 阶段已经准备同步但还没有用户明确授权；
4. GitHub、本地或 .53 存在未知/未批准 dirty、未解释提交/非 fast-forward/tag 冲突或 SHA 无法解释；台账已登记的 `.claude/`、`.playwright-mcp/`、`string.jpeg`、`.53 vc_api.log` 不误判，但不得 clean/覆盖；
5. git fsck 出现 missing/corrupt object；
6. 发现计划外工作树变化或与 CSS WIP 重叠；
7. 测试数字无法解释，或修复需要改变科学裁决/可靠性数值/LLM 红线；
8. 需要私有 checkpoint、付费服务或 API key；
9. 需要改变论文结论或把 narrowed/unsupported 改成 met；
10. 所有本地可做任务和最终完成闸门均已完成。

三端同步协议：本地 clean feature tip 的 exact SHA → 用 exact-ref CAS lease push GitHub branch（先核 expected remote 与 ancestry；显式 `--no-follow-tags`）→ CI → 经批准以同样 CAS+ancestry 约束非强制快进 GitHub main → 精确 `v1.6.0` → 经独立 D1c 授权 fast-forward 本地 main → 经独立 D2 授权从同一 GitHub origin 原子精确 fetch main+tag。若 `.53` 已部署提交是祖先才 fast-forward；已登记 sibling `b9abdbd` 只允许保留旧 refs 后新建 `codex/deploy-v1.6.0` 指向批准 SHA，绝不 merge/reset。随后记录 local main、live GitHub main、.53 deployed SHA 和 tag。工作分支 intentionally ahead/受保护例外必须记入 SYNC-STATE；未记录差异才是 drift。禁止在 .53 直接改代码；远端测试失败回本地新 commit，并重绑 artifact/approval 后重走 GitHub。

撞硬门时不要继续试探性修改：更新计划/PROJECT-STATE/SYNC-STATE 为 BLOCKED，写清已完成项、原始命令与输出摘要、未改动的保护项、三端 SHA，以及需要用户拍板的唯一问题。正常完成时给出 Phase A/B/C/D 的提交列表、最终测试矩阵、GitHub/本地/.53 一致性证明和仍 pending 的科学项；只有全部本地 C4/C5 闸门以及 D0 都完成——最终文档 SHA 已冻结、最终 release artifact 已绑定验证、三端 fresh 只读 ledger/ancestry/dirty/rollback 方案已向用户展示——而后续 D 尚未获授权时，才可写 READY_TO_SYNC，不能提前写或写成已同步。
```
