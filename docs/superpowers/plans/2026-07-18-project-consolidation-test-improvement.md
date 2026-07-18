# PRAXIS-VirtualCell 项目整理、测试与完善计划

> 日期：2026-07-18
>
> 状态：active — A0 迁移硬门完成，A1 进行中
>
> 审计锚点：`24475f2`（`v1.5.0` 后 1 个前端 E2E 计划提交）
>
> 配套执行提示词：`docs/superpowers/plans/2026-07-18-project-consolidation-goal-prompt.md`

## 0. 目标与执行顺序

本计划把工作严格拆成四个阶段，禁止混跑：

1. **A — 安全迁移并整理项目**：先把活跃 Git 工作副本迁到 APFS/本机，再保护现有工作，理清分支、文件、文档、版本语义和三端差异；不修功能、不追求测试变绿。
2. **B — 建立测试基线**：在整理后的结构上实跑所有分层检查，记录真实通过、跳过和失败；不弱化断言。
3. **C — 完善项目**：只依据 B 的证据修复 lint、CI、版本、前端 E2E、打包和远端能力。
4. **D — 同步与发布候选收口**：通过 GitHub 形成唯一已发布真相，再让本地和 `.53` 快进到同一已验证 commit。

只有前一阶段的完成闸门通过，才允许进入下一阶段。每个数字必须标明测试口径；“未测”“跳过”“远端 pending”不得写成通过。

## 1. 当前已知事实（执行前基线）

| 领域 | 当前事实 | 处理原则 |
|---|---|---|
| Git 主线 | 本地 `main=176019e=v1.5.0`；当前 HEAD `24475f2` 比 main 多 1 个 docs commit | 不改写 `main`、tag 或历史 |
| 当前分支 | `feat/v0.9-phase0-module-core`，相对本地 tracking ref `+82/-1`，名称已过时 | 新建整理分支，不在旧名上继续堆工作 |
| 远端 | 本地记录的 `origin/main` 停在 `v0.8.0`，但实时远端因 SSH 超时/HTTPS 缺凭证未核实 | 不 pull、merge、push；只记录待人工核对 |
| `.53` | 2026-07-17 文档最后记录为测试后恢复到 `b9abdbd`；这不是本轮实时核验 | 先只读取 HEAD/branch/status/remote；禁止把旧记录当现状 |
| 工作区 | 4 个 `praxis_vc_react/src/styles/*.css` 修改；`.claude/`、`.playwright-mcp/`、`string.jpeg` 未跟踪 | 全部视为用户资产，先分类，禁止删除/覆盖 |
| stash | `stash@{0}` 仅保存未跟踪文档 `docs/PRAXIS-生物科学智能体-总介绍.md` | 禁止 pop/drop；先导出清单再决定 |
| Git 存储 | T7 是 ExFAT，已用 93%；全树约 1031 个 AppleDouble/129 MB，其中 `.git` 下约 316 个；Git 识别约 194 个 garbage，但对象连通性仍完整 | 活跃副本先迁 APFS；禁止在 T7 原地清理 `.git` 或运行 `git gc` |
| 核心测试 | `912 passed / 40 skipped / 9 deselected / 0 failed`，口径为 `praxis_virtualcell/tests -m "not llm"` | 这是核心权威口径，不与根 tests 混算 |
| 遗留测试 | 根 `tests/` 实测 `1136 passed / 163 skipped / 1 failed`；失败为 `.53:7788/api/info` 超时 | 单列 legacy/integration，不冒充核心回归 |
| 前端 | typecheck/lint/build 通过，Playwright `3 passed`；主包约 632 KB 有 chunk warning | B 阶段复测，C 阶段扩 E2E/分包 |
| lint | `ruff check .` 有 13 个错误 | B 阶段固化，C 阶段修复 |
| 版本 | Git tag 为 `v1.5.0`，Python/前端 metadata 为 `0.0.0`，API 为 `0.6`，UI runtime 为 `v0.3` | 区分发行版本、API 版本、治理 artifact schema 后再改 |
| 科学边界 | Phase 10：约 7 项 met、4 项 narrowed、2 项 unsupported；真实引擎级覆盖仅 4 族 | 不扩大论文/产品声称 |

## 2. 全程红线

1. 不执行 `git reset --hard`、`git checkout -- <file>`、`git clean`、`git gc`、`git stash pop/drop`、强推或历史重写。
2. 不删除分支、tag、stash、数据、图片、用户配置或任何未跟踪文件。需要清理时只生成分类清单，等人工批准。
3. 不编辑 `.git` 内文件；AppleDouble 清理由“已验证备份 + 人工批准”的独立维护窗口处理。
4. 不使用 `git add -A` 或 `git add .`；每次只显式 stage 本任务文件。
5. 保护 4 个 CSS WIP；除“主题 WIP 专项”外不得触碰或 stage。
6. 默认 OFFLINE、零 LLM；不得调用真实 LLM 网络测试，不输出或读取 `.env` 中的密钥。
7. 根 `tests/` 是 PRAXIS-2 legacy 口径，不修成 VirtualCell 核心 KPI，也不通过新增 skip 掩盖失败。
8. 不修改冻结的治理 artifact 版本（例如 `feature_schema_v0.3.0`），除非确实重训/迁移 artifact 并有兼容方案。
9. 测试失败时先复现、归因、补证据；禁止改弱断言、吞异常或把真实失败改成无条件 skip。
10. A–C 阶段不 push、不创建 PR、不修改 `.53`；D 阶段也必须先展示三端 ledger 并取得同步授权，且只允许非强制、可验证的快进同步。
11. GitHub 是发布真相源，本地 APFS clone 是开发真相源，`.53` 是运行/验证镜像；禁止直接在 `.53` 开发或产生未回传的权威提交。

## 3. Phase A — 安全迁移并整理项目

> A 阶段只做安全、分类和信息架构。允许 `git diff --check`、配置解析、文档链接检查等窄验证；不跑全量回归，不顺手修 lint/功能。

### A0 — 建立 APFS 恢复副本与保护清单（第一硬门）

- [x] 先用只读命令生成源仓库恢复清单：当前 tracked diff 文件、未跟踪文件、stash 第三父树文件、local branches/tags/remotes；临时清单写到目标 APFS 备份目录，不在 T7 仓库新增整理产物。
- [x] 在本机 APFS 选择一个不存在或明确为空的目标目录；若用户未指定，可建议 `/Users/mzy/Projects/PRAXIS-virtualcell`，但写入前必须解析并确认目标，禁止覆盖既有目录。
- [x] 在 APFS 保存并验证 `git bundle create <bundle-path> --all`；确认 bundle 列出当前 HEAD、main、tags 和 `refs/stash`。
- [x] 单独保存 4 个 CSS 的 binary patch、完整 `git status`/ref 清单，以及所有待保留未跟踪资产（包括本计划文件）；`.env` 等 ignored secret 只列路径/大小，不输出内容，是否备份由用户决定。
- [x] 从 bundle 建立新的 APFS clone；显式恢复/核对 `refs/stash`，再复制 WIP patch 和未跟踪资产。后续 A–D 只在 APFS clone 工作，T7 原仓库转为只读留档。
- [x] 保留 bundle 为只读 `recovery` 来源，并把 APFS clone 的 `origin` 明确配置为源仓库记录的 GitHub URL；先核对 URL，再 fetch，禁止让 bundle 临时路径冒充 GitHub origin。
- [x] 在 APFS clone 验证 HEAD/main/tags/stash 与源仓库一致、`git rev-list --objects --all --missing=print` 无 missing、`git fsck --full` 无 corrupt/missing、`.git` 中没有 `._*`。
- [x] 仅在 APFS clone 创建 `docs/status/PROJECT-STATE-2026-07-18.md`，记录：源/新路径、HEAD/main/tag、branch upstream、remote caveat、stash、dirty/untracked、AppleDouble、已知测试数字和恢复物 sha256。
- [x] 若没有足够 APFS 空间、bundle 未覆盖所有 refs/stash、WIP 无法恢复或新 clone 校验失败，写 `BLOCKED` 并停止；不得退回 T7 原地继续整理。检查结果未触发本阻塞条件。

验收：状态文档能让新会话在不依赖聊天记忆的情况下恢复当前事实；APFS clone 可完整恢复 committed history、stash 和 WIP；T7 原仓库没有删除、stash、reset、gc 或 stage 用户资产。

### A1 — 三端同步台账、分支与版本历史整理

- [x] 在 APFS clone、任何整理提交之前，从当前 HEAD 新建本地工作分支 `codex/project-consolidation`；不移动 `main`，不改 tag。
- [ ] 记录分支关系：`HEAD...main`、`HEAD...origin/feat/...`、`main...origin/main`，并明确 tracking ref 可能陈旧。
- [ ] 在 APFS clone 执行经凭证允许的只读 `git fetch --prune --tags origin`；fetch 失败则保留 tracking-ref 快照并写明原因，不猜测 GitHub 现状。
- [ ] 新建 `docs/status/SYNC-STATE.md`，逐端记录 local APFS、GitHub、`.53` 的仓库路径/remote URL/branch/HEAD/main/tag/dirty 状态/核验时间/核验方式；未实时核验的值标 `UNKNOWN` 或 `LAST_RECORDED`。
- [ ] 定义同步不变量：发布检查点上 `local main == GitHub origin/main == .53 deployed SHA`；工作分支允许仅存在于 local/GitHub，不要求部署到 `.53`，但必须在 ledger 标明 intentionally ahead。
- [ ] 取得 `.53` 访问权时先只读执行 `pwd`、`git status --short --branch`、`git remote -v`、`git rev-parse HEAD`、`git show-ref --heads --tags`；不 fetch/checkout/pull，不触碰运行进程。
- [ ] 记录远端唯一提交 `b9abdbd` 与本地 `4359602` 的文件级差异；结论只能写“待远端核对/本地是否超集”，不得自动 merge。
- [ ] 将 `stash@{0}` 的唯一文件名和来源写进状态文档；stash 保留原样。
- [ ] 建立发布历史简表：bootstrap → v0.1 → v0.3 alpha → v0.8 → v0.9 → v1.0–v1.5；标明哪些 tag 仅能确认在本地存在。

验收：当前工作分支名与任务相符；`SYNC-STATE.md` 明确三端真实/未知状态和预期目标；主线、旧远端分支和 tag 均未被改写；没有 push/pull/merge，也没有修改 `.53`。

### A2 — 工作区资产分类

- [ ] 为以下每项写出 `keep-and-commit / keep-local-and-ignore / archive-with-provenance / pending-user-decision` 四选一分类：
  - 4 个主题 CSS WIP；
  - `.claude/launch.json`；
  - `.playwright-mcp/` 页面快照与日志；
  - `string.jpeg`（STRING TP53/EGFR 映射截图）；
  - stash 中的项目总介绍文档。
- [ ] CSS WIP 独立为“主题专项”，不得与整理、测试、版本修复混交；记录其已通过结构性 E2E、尚未完成视觉验收。
- [ ] 若 `string.jpeg` 要入库，先改为语义化文件名、放入明确的文档 assets 目录并补来源/用途；否则保持未跟踪等待人工决定。
- [ ] `.playwright-mcp/` 默认视为工具生成物候选，不把日志/页面快照直接提交。
- [ ] stash 中的总介绍仍以 v1.4 为主且可能含超出 Phase 10 闸门的旧措辞；若恢复，只能进独立草稿分支并逐项对照 `PHASE10_GATE.md`，不得原样发布。
- [ ] 不通过移动或复制制造第二份不清楚谁是权威源的文件。

验收：每个脏项都有去向和理由；未获批准的内容仍原样存在；整理提交不包含 CSS WIP 或工具输出。

### A3 — 文档信息架构

- [ ] 新建 `docs/INDEX.md`，至少分为：当前状态、用户文档、架构/能力边界、发布记录、执行计划、测试报告、论文/历史材料。
- [ ] 指定当前权威入口：根 `README.md`、`docs/INDEX.md`、`docs/status/PROJECT-STATE-2026-07-18.md`、`reports/phase10/PHASE10_GATE.md`。
- [ ] 对旧计划/旧 handoff 采用“索引标注历史状态”，不批量移动或改写 256 个文档，避免断链。
- [ ] 记录明显陈旧项：README 的 `277 passed`、前端 Vite 模板 README、旧根测试失败数、旧 runtime 展示版本。
- [ ] 新建 `docs/VERSIONING.md` 设计稿，区分：产品发行版、API 版本、消息/schema 版本、治理 artifact/model 版本、前端包版本。

验收：一个新贡献者能从 `docs/INDEX.md` 找到当前真相，并能区分历史记录与有效操作文档；不改科学结果正文。

### A4 — 目录与生成物规则

- [ ] 检查 `.gitignore` 是否覆盖构建、Playwright、runs、AppleDouble；列出 `.claude/` 与 `.playwright-mcp/` 的建议，不在未分类前直接忽略用户文件。
- [ ] 记录 1126 个 tracked files 中 code/test/docs/data/audit 的职责，不以“大扫除”为由删除继承代码或研究证据。
- [ ] 明确 `_audit/`、`reports/`、`docs/findings/` 是证据/历史，`runs/`、`dist/`、`test-results/` 是生成物。
- [ ] 为 Git 外置盘污染写一份非破坏维护 runbook：备份、迁移到 APFS/本机、只读 `git fsck`、人工批准后清理、再次 `git fsck`；本计划不执行清理。

验收：目录职责和生成物规则写清；未删除任何 legacy、audit、paper、data 或 `.git` 内容。

### A5 — 整理完成闸门

- [ ] `git diff --check` 通过。
- [ ] 新增 Markdown 文件链接可解析，计划中的绝对事实与 `git` 只读命令一致。
- [ ] `git status --short` 中原有 4 CSS + 3 未跟踪资产保持不丢；整理提交只包含显式 docs/索引文件。
- [ ] `main`、`v1.5.0`、stash 未改变；origin tracking refs 只能因已记录的 fetch 更新，不得被手工移动或改写。
- [ ] 当前工作目录是已验证 APFS clone；T7 原仓库保持只读；`SYNC-STATE.md` 状态至少为 `KNOWN_DIVERGENCE`，不存在未经记录的 SHA 差异。
- [ ] 在状态文档写入 `PHASE_A_COMPLETE` 和完成 commit；若任何保护项不满足，写 `BLOCKED`，不得进入 Phase B。

## 4. Phase B — 建立真实测试基线

> 只有 A5 完成后才能开始。B 阶段先测量、后归因，不修复。所有命令记录解释器、工作目录、退出码、passed/skipped/deselected/failed。

### B0 — 环境与静态检查

- [ ] 在 APFS clone 创建新的本地 `.venv`，按项目声明安装 `.[dev,api,mechanistic]`；不复制 T7 的旧 editable 环境。安装失败记录依赖/网络硬门，不用旧环境冒充干净基线。
- [ ] 在前端运行 `npm ci` 重建 lockfile 对应依赖；不复制旧 `node_modules`。
- [ ] 记录 Python、Node、npm、pytest、ruff、FastAPI、Starlette、httpx、React、Vite、Playwright 版本。
- [ ] 运行 `.venv/bin/python -m pip check`。
- [ ] 运行 `cd praxis_vc_react && npm audit`。
- [ ] 运行 `.venv/bin/ruff check . --output-format concise`，把 13 个已知问题按生产代码/测试代码/自动可修分类。
- [ ] 运行只读 `git fsck --no-reflogs --connectivity-only`，区分对象损坏与 AppleDouble garbage warning。

### B1 — VirtualCell 核心后端

- [ ] 运行：`.venv/bin/pytest praxis_virtualcell/tests -m "not llm" -o addopts='' -q -ra`。
- [ ] 记录本机 40 条 skip 的具体类别：torch/GPU、Docker、remote donor 等。
- [ ] 运行 Phase 10 交付脚本时只使用其声明的包口径，不把根 tests 混入。
- [ ] 核对 `reports/phase10/PHASE10_SUMMARY.md` 与实测；`tests=passed+skipped` 的不同表述不得误报为漂移。

### B2 — 前端与同源 E2E

- [ ] `npm run typecheck`。
- [ ] `npm run lint`。
- [ ] `npm run build`，记录 chunk size warning 和主要 bundle 大小。
- [ ] `npm run e2e`，记录现有 3 个 spec 的 passed/failed。
- [ ] 确认 E2E 使用临时 `PRAXIS_VC_RUNS`，不污染仓库 `runs/`。

### B3 — 打包、CLI 与依赖

- [ ] 从 `git archive` 的干净树构建 wheel，不让工作区 WIP 混入产物。
- [ ] 检查 wheel 是否包含 `praxis_virtualcell/cli.py`、`praxis_vc_api/main.py`、运行时数据和 console entry point。
- [ ] 记录 wheel metadata 版本、当前 editable install 版本和 `.venv/bin/praxis-vc` 是否存在。
- [ ] 在临时虚拟环境做 `--no-deps` 或可控依赖的 CLI help smoke；不修改主 `.venv` 来掩盖安装漂移。

### B4 — Legacy 与远端能力（单独口径）

- [ ] 根 `tests/` 单独运行并标 `legacy`，不计入 VirtualCell 核心绿灯。
- [ ] 固定 IP/服务健康检查失败归类为 `remote operational`，不在普通单元 CI 中无条件阻断。
- [ ] `.53` GPU、donor checkpoint、Docker 等仅复用已有亲验证据；没有本轮远端授权时保持 pending。
- [ ] 不运行需要真实 API key 的 LLM 测试。

### B5 — 基线完成闸门

- [ ] 新建 `reports/quality/BASELINE-2026-07-18.md`，汇总 B0–B4 的命令、环境、退出码、数字、失败归因和待修列表。
- [ ] 每个失败能映射到 C 阶段的一个任务；无法归因的标 `BLOCKED`。
- [ ] 基线报告不得使用“整仓全绿”，除非所有分层口径确实为 0 failed。
- [ ] 写入 `PHASE_B_COMPLETE`；完成前不得修代码或改测试。

## 5. Phase C — 完善项目

> 只处理 B 报告里的证据项。每个任务先复现失败，再最小修复，再跑相关测试和完整核心回归；每个任务独立提交。

### C0 — 恢复 lint 绿灯

- [ ] 修复 B0 记录的 13 个 Ruff 错误；自动修复后必须人工审 diff。
- [ ] 生产代码与测试代码都保持 `ruff check .` 0 error，不靠新增大范围 exclude/noqa 逃避。
- [ ] 运行核心 pytest，确认 lint 整理没有行为回归。

### C1 — 测试配置与 CI 分层

- [ ] 在 pytest 配置注册 `integration`、`llm`、`remote` 等实际使用 marker，并评估启用 strict markers。
- [ ] CI 拆成至少三个清晰 job：Python lint/core、frontend build/E2E、legacy/integration（可按环境设非阻断或条件触发）。
- [ ] 核心 job 明确运行 `praxis_virtualcell/tests -m "not llm"`；不把固定私网服务当普通 CI 前提。
- [ ] 前端使用 `npm ci`，依次执行 typecheck、lint、build、Playwright。
- [ ] 本地复现 CI 命令后再提交，不声称无法看到的 GitHub 绿勾。

### C2 — 版本、文档与 CLI 收口

- [ ] 按 `docs/VERSIONING.md` 建立单一产品版本源；当前历史基线是 `v1.5.0`，下一发行号由改动范围决定。
- [ ] 让 Python metadata、前端 package、API/UI 展示引用明确的发行版本；保留独立 schema/artifact 版本。
- [ ] 更新根 README 的测试数字、安装/开发命令和能力边界；替换前端 Vite 模板 README。
- [ ] 重新安装 editable 环境并验证 `praxis-vc --help`；干净 wheel 安装 smoke 通过。
- [ ] 不在未验证远端/tag 状态时创建或 push 新 release tag。

### C3 — 前端 WIP 与全面 E2E

- [ ] 先对 4 个主题 CSS 做人工视觉验收；通过后单独提交，未通过则继续保留 WIP，不和测试改动混交。
- [ ] 若已不使用 Newsreader，删除对应依赖并更新 lockfile，重新 build/audit。
- [ ] 按 `2026-07-17-frontend-full-e2e-test-plan.md` 的优先级实现：S3 → S9 → S4 → S6 → S7/S8 → S11 → S5 → S12 → S13；S10 无 key 时诚实 skip。
- [ ] 本整理计划覆盖旧 E2E 计划的编排细节：不盲杀占用 8000 端口的未知进程，优先使用独立端口/明确归属的 webServer；提交不写固定模型署名；console/page error/500 使用 Playwright 原生 listener 采集，不依赖未定义的浏览器 MCP 指令。
- [ ] 每个 suite 先真跑获取页面/API 真值，再写 role/label/text 断言，并做一次变异证伪。
- [ ] 发现 UI/API 真 bug 时修生产代码并补回归，禁止弱化 E2E 凑绿。

### C4 — 依赖、包体与发布复现

- [ ] 为 Python 建立可复现 constraints/lock 策略，处理 FastAPI/Starlette/TestClient 弃用风险。
- [ ] 对约 632 KB 主 chunk 做测量驱动的 lazy load/code splitting；优化前后记录 gzip 大小和 E2E。
- [ ] 完成 wheel 内容、CLI、API、同源 dist、Dockerfile 的本地可验部分。
- [ ] Linux Docker smoke 若需 `.53`/镜像网络则停在远端硬门，不伪造通过。

### C5 — 科学能力与远端 backlog

- [ ] 优先关闭 MLBackedPredictor Gate A 不误伤真 ML 的端到端验证。
- [ ] 定位 `W4B_CKPT_DIR`，完成 `test_ml_workflow_e2e`；没有 checkpoint 就保留 pending。
- [ ] 建立 corpus 后再测单模块成功率、unsupported abstain rate；没有分母不得编百分比。
- [ ] “独立结果冲突检测”和“LLM unsupported claim=0”目前仍 unsupported；只有新增真实能力与独立评估后才可改状态。
- [ ] 论文/产品持续声明：真实引擎级覆盖仅 4 族，M1/M5/M8 advisory，M6/emt/fate limitation，非 SOTA 预测模型。

## 6. Phase D — GitHub、本地与 `.53` 同步收口

> D 是唯一允许改变 GitHub 或 `.53` 状态的阶段。进入 D 前必须冻结一个通过 C 阶段全部本地闸门的 release-candidate commit。第一次实际 push 或修改 `.53` 前，展示完整同步方案并取得用户明确授权。

### D0 — 冻结候选与同步前对账

- [ ] 选择唯一 release-candidate SHA、目标产品版本和目标 GitHub branch；把核心测试、前端测试、wheel/CLI smoke 与该 SHA 绑定。
- [ ] 更新 `SYNC-STATE.md`：local APFS HEAD/main、GitHub live refs、`.53` live HEAD/branch/dirty、预期同步后的 SHA。
- [ ] 确认本地工作树（不含明确保留的本地 WIP 分支）干净；`.53` 工作树干净且没有未回传提交；否则停止，不 reset/覆盖。
- [ ] 对 GitHub divergence 做 ancestry/range-diff/cherry 检查；只允许可解释的 fast-forward 或经人工审查的正常 PR/merge，禁止 force push。
- [ ] 提交“将要 push 哪些 refs/tags、`.53` 将切到哪个 SHA、如何回滚”的清单，请用户确认同步授权。

### D1 — 同步 GitHub

- [ ] 先 push release-candidate 工作分支，不直接覆盖 main；验证 `git ls-remote` 返回的 SHA 与本地完全一致。
- [ ] 等待/核对该 SHA 的 CI；没有可见 CI 证据时不得声称 GitHub 全绿。
- [ ] 通过用户批准的 PR 或非强制 fast-forward 更新 GitHub main；再按批准清单 push release tag，禁止一次性 `push --all`/`push --tags` 把历史草稿全发出。
- [ ] 本地 APFS clone `fetch` 后只用 fast-forward 更新本地 main；验证 `local main == origin/main`。

### D2 — 同步 `.53`

- [ ] 在 `.53` 再次确认仓库路径、remote、branch、HEAD、dirty、运行服务状态；生产服务在运行时先给出无扰动更新窗口方案。
- [ ] `.53` 只从同一个 GitHub origin fetch；目标必须是 D1 已通过 CI 的精确 SHA。若 `.53` 当前提交不是目标祖先或工作树不干净，停止，禁止 reset --hard。
- [ ] 正常情况使用显式 `git fetch --tags origin` + `git merge --ff-only <approved-ref>` 同步。若 `.53` 仍停在带独有 `b9abdbd` 的历史分支，且该提交不是目标祖先，则保留旧分支/commit，按批准清单新建一个跟踪 GitHub main 的 deployment branch 并切到目标 SHA；不把冗余提交盲 merge 进 main，也不 reset/删除旧分支。
- [ ] 不在 `.53` 修改源码或提交；部署分支的每个 commit 必须先存在于 GitHub。
- [ ] 在目标 SHA 运行约定的 remote/Docker/API smoke，记录解释器/环境/模型 checkpoint 和结果；失败则 ledger 标 `SYNCED_BUT_NOT_VALIDATED` 或按事先回滚方案处理，不伪造健康。

### D3 — 三端一致性证明

- [ ] 同一时间窗口记录：本地 `git rev-parse main`、GitHub `git ls-remote origin refs/heads/main`、`.53 git rev-parse <deployed-branch>`，三者必须等于批准的 SHA。
- [ ] 核对 release tag 在本地、GitHub、`.53` 指向同一 object；三端工作树/refs 无未解释差异。
- [ ] 在 `SYNC-STATE.md` 写同步时间、操作者、命令摘要、CI 链接/编号（若可用）、远端 smoke、回滚点和下次检查方式。
- [ ] 若任一端不一致，状态必须为 `DRIFTED` 并阻断发布完成，不允许用“基本同步”收口。

### D4 — 后续持续同步协议

- [ ] 固化唯一流向：本地 feature branch → GitHub branch/CI → 审批合入 GitHub main → 本地 main fast-forward → `.53` 从 GitHub fast-forward → 三端 SHA 核对。
- [ ] 禁止在 `.53` 直接开发；远端实验只产测试报告/artifact，若必须改代码则回到本地分支实现并重新走 GitHub。
- [ ] 每次 Phase/Release checkpoint 更新 `SYNC-STATE.md`；工作分支 intentionally ahead 不算漂移，未记录的 main/deployed SHA 差异才算漂移。
- [ ] 可新增只读 `scripts/release/check_sync.sh`，但脚本不得自动 push/pull/checkout/reset，只输出三端 refs 和退出码。

## 7. 最终完成闸门

- [ ] Phase A/B/C 状态均有锚定 commit 和报告；Phase D 已完成三端同步，或因尚未取得外部同步授权而明确停在 `READY_TO_SYNC`。
- [ ] `git diff --check`、`ruff check .`、核心 pytest、前端 typecheck/lint/build/E2E 全部按各自口径通过。
- [ ] wheel 版本与发行版本一致，CLI 在干净环境可用。
- [ ] CI 分层与文档口径一致；legacy/remote/pending 不冒充核心失败或核心通过。
- [ ] 用户原有 CSS、stash、未跟踪资产均有明确去向，没有静默丢失。
- [ ] 活跃本地仓库已迁到 APFS；T7 原仓库只读留档。原盘污染未清理时继续列为运维风险，不得写“原仓库完全健康”。
- [ ] 若用户授权 D 阶段同步：本地 main、GitHub main、`.53` deployed SHA 与 release tag 全部一致并有 ledger 证据；若未授权，则最终状态必须明确为 `READY_TO_SYNC`，不能写已同步。
- [ ] 提交最终整理报告；任何新的 push/tag/deploy 仍须走 D 阶段清单与授权。

## 8. 提交建议

建议按以下边界做本地小提交，实际文件以任务为准，禁止混入 WIP：

1. `docs(consolidation): 建立项目状态与文档索引`
2. `docs(consolidation): 记录版本语义与仓库维护 runbook`
3. `test(baseline): 固化分层质量基线报告`
4. `style(lint): 恢复全仓 ruff 绿灯`
5. `ci: 拆分 core frontend legacy 测试口径`
6. `chore(version): 统一产品发行版本与 CLI metadata`
7. 前端主题、每个 E2E suite、依赖/包体优化分别提交
8. `docs(sync): 记录 GitHub 本地与 .53 三端一致性证明`

每次提交前检查 `git status --short` 和 `git diff --cached --name-only`；若出现计划外文件，立即取消该文件的 stage 并查明来源。

## 9. 硬门

遇到以下情况立即停下、写明证据并请求用户决定：

1. 需要删除/覆盖用户 WIP、stash、未跟踪资产、分支、tag、数据或 `.git` 内容。
2. A0 无可用 APFS 目标、bundle/WIP/stash 无法完整恢复，或 APFS clone 校验失败。
3. D 阶段前需要 GitHub 凭证、push、PR、远端 merge/rebase 或 `.53` SSH/GPU/Docker 操作；D 阶段已展示清单但尚未获得用户同步授权。
4. `git fsck` 出现 missing/corrupt object，而非仅 AppleDouble garbage warning。
5. 工作树出现本计划未产生的新改动，或与 4 个 CSS WIP 重叠。
6. GitHub、本地或 `.53` 出现非 fast-forward、dirty worktree、未知提交或 SHA 无法解释。
7. 测试数字与基线无法解释，或修复需要改变科学裁决、可靠性数值、LLM 边界。
8. 需要下载受限数据、私有 checkpoint、付费服务或使用真实 API key。
9. 需要改变论文中的科学结论或把 narrowed/unsupported 改成 met。
