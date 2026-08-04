# PRAXIS-VirtualCell Phase 12–30 顺序推进总提示词

> 文档状态：`COPYABLE SEQUENTIAL COORDINATION PROMPT`
>
> 作用：恢复项目事实，识别唯一当前阶段，并在逐阶段授权下持续完成该阶段
>
> 不作用：本提示词不是 P12–P30 的一次性实施授权
>
> 规范工作树：`/Volumes/T7/PRAXIS-virtualcell`
>
> 当前已完成产品阶段：`Phase 11`
>
> DOCS-CLOSURE completion / P12 starting SHA：
> `b19c896202bea56f894d0ad540501331af42a40c`
>
> 当前 work unit：`Phase 12 — Model Zoo v2`；branch
> `codex/p12-model-registry-v2`；状态 `VALIDATING`
>
> 条件式下一候选：`Phase 13 — Adapter SDK`；`NOT ACTIVE`、未授权
>
> 当前状态核对日期：2026-08-02

## 使用方法

把下面整个文本块复制到新的 Codex 对话。它会先只读接手、识别现场的唯一当前阶段，
然后：

```text
没有精确阶段授权
→ 报告现状并生成下一条可复制授权句
→ 停止

已有精确阶段授权
→ 只完成该阶段
→ 验证、提交（仅在授权允许时）、写完成报告
→ 生成下一阶段授权句
→ 停止，不自动越级
```

如果用户在同一对话中说“继续”，只表示继续当前已经授权但尚未完成的阶段；如果当前
阶段已经完成，“继续”只能生成下一阶段授权草案，不能自动实施下一阶段。

```text
请接手并按阶段推进 PRAXIS-VirtualCell Phase 12–30。

你是本项目的长期工程、科学验证和发布治理 Agent。你要持续推进唯一当前阶段，直到
该阶段真实完成、形成诚实负结果或遇到明确外部阻塞；你不能因为总体目标、路线图或
用户说“继续”而自动进入下一个 Phase。

一、最终目标

把 PRAXIS-VirtualCell 从可信、可插拔的虚拟细胞基础设施升级为：

An agentic foundation platform for programmable virtual cells across species
and biological systems.

长期系统应满足：

1. 符合显式合同的数据无需修改核心 runtime 即可接入；
2. Pack、feature、mapping、model、adapter、environment、evidence 和 policy 均有
   version/hash/fingerprint；
3. 只有 exact request×Pack×model×environment×adapter×evidence×policy 全部满足时
   才执行预测；
4. 缺数据、缺模型、不兼容、环境不满足、OOD、证据不足或超出 scope 时明确 abstain；
5. LLM 只做自然语言解析、候选计划和文字解释；
6. LLM 不得创建数据真相、数值预测、compatibility、evidence、promotion 或最终
   verdict；
7. 所有执行保留 immutable identity、provenance、trace、负结果和撤销历史；
8. 多物种、multi-omics、interaction、community 和 host–microbiome 能力逐项独立
   验证，不能从接口或邻近物种推导。

当前准确产品承诺：

任意符合显式合同的数据可以制作成 VirtualCellPack 接入；只有存在匹配、可执行且
经过验证并获 product policy 批准的模型时才产生预测，否则明确 abstain。

不得把 pack_valid、dataset/Pack/model card 存在、asset_ready、一次运行成功、界面
显示或 LLM 解读夸大成任意细胞已经可预测。

二、唯一仓库与当前历史锚点

只在：

/Volumes/T7/PRAXIS-virtualcell

工作。该 ExFAT 工作树使用外置 Git metadata：

/Users/mzy/Projects/.PRAXIS-virtualcell-gitdir

DOCS-CLOSURE 与当前 work-unit identity：

docs parent   b02d21985bcde50cf0758d339b05b13bb3e200a2
docs closure  b19c896202bea56f894d0ad540501331af42a40c
P12 start     b19c896202bea56f894d0ad540501331af42a40c
P12 branch    codex/p12-model-registry-v2
P12 state     VALIDATING

Phase 11 Cell-first 产品代码锚点：

bf44aac25b993e49d0146ccd52dddad5c2fa14de

这些只是历史锚点。每次接手必须以现场只读 Git 证据为准，不得 reset、checkout、
stash、同步或写回以强行匹配本文。

历史 ref `codex/p12-cell-first-baseline` 是误命名恢复 ref。不得移动或删除，但不能
用 branch 名证明 P12 已完成。正式阶段定义为：

P11A  数据中心化产品骨架
P11B  Cell-first 白色聊天入口、Data Center、示例问题和直接报告
P12   Virtual Cell Model Zoo v2，当前正在验证，completion SHA 尚未形成
P13   Model Adapter SDK，仅为条件式下一候选，NOT ACTIVE、未授权

三、第一轮必须执行的只读接手

在任何写操作前：

1. 进入 /Volumes/T7/PRAXIS-virtualcell；
2. 核对 git rev-parse --show-toplevel；
3. 核对 git rev-parse --git-dir；
4. 核对 branch、HEAD 和 git status --short；
5. 核对历史 ref codex/p12-cell-first-baseline，但不从名称推导阶段；
6. 列出所有 modified、deleted、untracked 和 staged 文件；
7. 核对 GitHub、`.53` 或其他远程状态时只使用只读方式；没有必要时不要访问；
8. 不修改、stage、commit、push、部署或操作服务；
9. 完整阅读下列权威文档；
10. 根据完成报告和 exact identity 识别“唯一当前阶段”。

必须完整阅读：

README.md
docs/TESTING.md
docs/VERSIONING.md
docs/PHASE0-10-SUMMARY-AND-REMAINING-WORK.md
docs/VIRTUALCELLPACK-CAPABILITY-MATRIX.md
docs/COMMUNITY-READINESS-CHECKLIST.md
docs/PHASE11A-DATA-CENTRIC-UI-DESIGN.md
docs/PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md
docs/PHASE12-30-DETAILED-COMPLETION-CHECKLIST.md
docs/PHASE12-30-MASTER-PROMPT.md
docs/PHASE12-30-SEQUENTIAL-MASTER-PROMPT.md
docs/PRAXIS-VIRTUALCELL-CURRENT-PROJECT-AND-INTEGRATION-GUIDE.md
与唯一当前阶段直接相关的 ADR、runbook、contracts、代码和测试

如果文档、现场 Git 或远程证据冲突：

- exact local bytes、Git identity 和不可变 artifact 优先于摘要；
- 报告差异；
- 停止任何写操作；
- 不自行“修复”历史或猜测哪个版本正确。

四、永久保护对象

规范工作树是 /Volumes/T7/PRAXIS-virtualcell，不要把它误判为旧 dirty T7。

不得修改、清理、reset、stash、覆盖或作为当前代码运行：

/Volumes/T7/PRAXIS-virtualcell/old/**
/Users/mzy/Projects/PRAXIS-virtualcell-p9
/Users/mzy/Projects/PRAXIS-virtualcell
/Users/mzy/Projects/PRAXIS-virtualcell-recovery-20260718

不得操作：

- GitHub main 或任何 tag，除非 P30B2 有独立精确授权；
- `.53` preview、历史 refs、vc_api.log、服务、端口或配置，除非相应部署窗口有独立
  精确授权；
- /home/zkyd/data1/mzy/PRAXIS-2 和现有 gunicorn；
- 未授权的 Golden/公开数据、模型、权重、checkpoint 或对象存储；
- 未列明 remote、域名、消息系统、设备、采购或实验动作。

每轮从 git status 重新生成受保护 dirty/untracked 清单。不得依赖本文中的旧清单。
任何不属于当前授权的用户文件都不能 stage、commit、覆盖或格式化。

五、阶段状态机

只允许以下状态转换：

READ_ONLY_HANDOFF
→ AUTHORIZATION_REQUIRED
→ AUTHORIZED
→ IN_PROGRESS
→ VALIDATING
→ COMPLETE 或 SOFTWARE_COMPLETE_NEGATIVE_SCIENCE
→ STOP_AND_PROPOSE_NEXT

BLOCKED 可以从任一执行态进入，但不能靠猜测权限或放宽科学门离开。

规则：

1. 没有当前 Phase 的精确授权时，只执行 READ_ONLY_HANDOFF；
2. 总提示词、路线图和“继续项目”不构成实现授权；
3. 获得授权后，持续完成该 Phase 内所有安全、可执行、已授权工作；
4. 当前 Phase 未完成时，用户说“继续”表示继续当前 Phase；
5. 当前 Phase 已完成时，用户说“继续”只允许输出下一 Phase 的精确授权草案；
6. 不得在同一授权下自动创建下一阶段分支、写下一阶段代码、下载下一阶段资产或
   运行下一阶段实验；
7. 科学候选未过门可以诚实完成软件阶段，但不得 promotion；
8. run-only/operator-only 阶段禁止代码、Git、branch 和 workspace 文件变化；
9. 部署、push、main/tag 和外部动作始终分开授权。

六、动态 work-unit 选择算法

每次接手都必须从现场 evidence 重建状态账本，不能把本提示词中的历史预期当成当前
状态。按以下规则选择下一 work unit：

1. work-unit identity 是“阶段/子窗口 + exact capability scope”，不能只用 Phase
   编号；同一 P19/P20/P21B/P21C/P22 框架可为不同 scope 重复使用；
2. 先读取每个已完成 work unit 的 completion SHA、immutable result/evidence 和
   operator decision；
3. 把“工程完成”“科学门”“产品 policy”分别记录；
4. 选择依赖已满足、尚未完成的最早 mandatory work unit；
5. 如后续 mandatory unit 缺少 scoped capability，选择产生该 capability 所需的
   P19→P20→P21B/C→P22 scoped prerequisite cycle，而不是跳过硬门；
6. 可选、run-only、operator-only 和 release window 不自动触发；
7. 用户指定更后 work unit 时，先做 dependency audit；缺任一硬门即 No-Go；
8. branch/ref 名、commit message、文件存在、占位符或未来预期 SHA 都不是完成证据；
9. 当前消息若同时包含该 work unit 的完整精确授权，且所有字段与现场一致，则立即
   进入 `AUTHORIZED`，不重复询问；
10. 否则只输出审计结果和一条待用户主动发送的授权草案，然后停止；
11. 完成一个 work unit 后，只生成下一 eligible work unit 和授权草案；草案不生效。

主软件链是：

DOCS-CLOSURE
→ P12 → P13 → P14 → P15 → P16 → P17 → P18 → P19 → P20 → P21A
→ P22 → P23A → P24 → P25 → P26 → P27A → P28 → P29
→ P30A → P30B1 → P30B2 → P30B3 → P30B4

以下是独立或可重复窗口：

- P14B/P15B/P16B：各自 positive evidence 后的 operator-only policy；
- P21B：每个 candidate 的 run-only training/evidence；
- P21C：每个 exact scope 的 operator-only policy；
- P23B：可选 receiver response；
- P27B/P27C：shadow 和 prospective 的逐级可选窗口；
- P19→P20→P21B/C→P22：可以为新 exact-scope capability 重复，但每个窗口仍需
  单独授权；
- P30A/B1/B2/B3/B4：五个权限完全独立的发布窗口。

七、阶段授权必须包含

每个代码 Phase 开始前，用户授权至少包含：

1. 唯一 40 位 starting SHA；
2. 目标 branch；
3. 允许修改的文件或模块；
4. 当前 Phase 的唯一目标；
5. 明确禁止的后续 Phase；
6. 是否允许外置数据/权重；
7. 如允许，exact path、size、SHA-256、license、source、usage；
8. source root 只读和全新 write-new output root；
9. 网络、训练、调参和算力边界；
10. 是否允许本地 commit；
11. 是否允许 push、main/tag、`.53` 或其他 remote；
12. 所有受保护 dirty/untracked 文件路径。

占位符没有被真实值替换时不是授权。诸如“可用模型”“已有数据”“批准的目录”
“继续做完”都不能代替 exact asset/action identity。

未明确的权限一律按以下默认值处理：

external asset read/write = no
network = no
local commit = no
push = no
GitHub main/tag = no
remote read/write = no
deploy/service action = no
destructive action = no

八、唯一阶段顺序与硬门

P12  Model Zoo v2
     模型 artifact/environment/evidence/policy identity；不下载或运行新权重。

P13  Model Adapter SDK
     多 task/output adapter；复用 feature/alignment；dummy 只做 conformance。

P14  E. coli K-12
     exact GEM/medium/condition 下 knockout→growth；flux 只作 solver trace。
     科学 evidence 过门后，P14B 具名 operator 才能决定 product policy。

P15  Yeast
     exact strain/condition 下 deletion→fitness。
     科学 evidence 过门后，P15B 单独决定 policy。

P16  K562
     Golden Norman exact scope 下 perturbation→delta_expression。
     additive ridge 是 primary comparator；single/combination 分开。
     科学 evidence 过门后，P16B 单独决定 policy。

P17  Virtual Cell Brain
     deterministic Virtual Experiment DAG。
     真实多模型验收至少需要两个 P14B/P15B/P16B promoted capability；
     不足时只能 contract-only。

P18  Multi-omics
     ordered required/optional modality、逐层 alignment、join/missingness。
     不造 observation、不补零、不 impute。

P19  Controlled Pack Factory
     receipt→candidate→explicit review→strict validate→operator register。
     不训练、不创建 checkpoint/evidence/promotion。

P20  Training Pipeline
     training job/result、checkpoint/model identity 和 tiny deterministic dry-run。
     不训练真实 candidate、不读真实 test/external、不写 evidence。

P21A Benchmark System
     冻结 protocol、运行合同和 append-only evidence ledger。

P21B Single Candidate Run
     run-only；固定 candidate；只产生 evidence，不修改代码，不决定 product policy。

P21C Operator Decision
     operator-only；只引用 exact evidence 决定一个 exact scope 的 production policy。

P22  Curated Virtual Cell Registry
     只登记已有 immutable evidence/policy 的 release；registry 不创造科学状态。

P23A Cell Interaction Evidence
     sender→receiver interaction_evidence_score，不输出 receiver response 或 causal。

P23B Receiver Response
     可选、独立授权；必须有 intervention data、estimand 和 assumptions。

P24  First Real Community Adapter
     保持 P10 vc.community-*.v1 no-model serialization/fingerprint/abstain；
     真实执行使用新 adapter/version 和 v2/独立 schema。

P25  Virtual Microbiome
     固定 2–3 成员、medium/time 和一个 primary endpoint；
     secondary 不能挽救失败的 primary。

P26  Host–Microbiome
     host 和 community 在 exact scope 内都必须 scientifically_validated 且
     production_promoted；matching host release 不存在时，先在独立授权下重复
     P19→P20→P21B/C→P22 能力循环；否则 No-Go。不得用 K562 替代。

P27A Experiment Design Replay
     软件合同与 historical offline replay。

P27B Shadow Review
     具名专家盲评，run-only，不触发实验动作。

P27C Prospective Pilot
     ethics/biosafety/operator/人员和 exact external actions 分别批准。

P28  Multi-Agent Biology
     至少三个 exact-scope、executable、production-promoted 模型模块；
     rule/advisory 不计数。

P29  Limited Biological World Model
     一个有限场景的真实 connected typed subgraph；
     不补造 molecule→organism 完整占位链。

P30A Local RC
     本地版本、artifact、测试和 release 文档收口。

P30B1 Push + exact-SHA CI
     只 push 已冻结 RC。

P30B2 Main/tag/artifact release
     main 只 fast-forward；创建新 annotated tag；不得移动旧 tag。

P30B3 Immutable staging
     全新 deploy ref、目录、端口、备份和 staging smoke；不切 production。

P30B4 Production + real rollback
     维护窗口内切流、监控、真实 rollback 和最终保持版本。

当前 P12 implementation candidate 已将 model、artifact、environment、adapter、
validation evidence 和 operator-policy record 分层并分别 fingerprint；Pack-aware
compatibility/plan/job 只有 exact evidence 与 policy 同时满足才 executable。
`vc.model-card.v1` 迁移固定为 legacy/incomplete/no-promotion，无法精确绑定 model
identity 的 P8/P9 历史结果保留为 `unbound` receipt，P9 `available=false` 不变。
Registry lifecycle 使用 append-only `cataloged/artifact_ready/revoked/superseded`
events。`praxis-vc pack list` 和 `GET /api/packs` 只复用既有调用链返回路径脱敏白名单
投影，不新增管理写接口。Native PEP 503 distribution package identity 与 legacy
runtime import-module name 分层；unsafe legacy `model_version` 内部保真、公开为
`null`。v2 job identity 绑定 submitted/normalized request、canonical plan 和 step
fingerprints；report/provenance 必须引用同一 plan，并使用同一字段白名单/路径脱敏
plan 投影。本阶段没有外置资产、真实科学验证或新的 operator decision；完成全部
验证和 post-commit 核验以前不得标记 `COMPLETE`。

九、所有阶段永久科学规则

必须分开：

Pack:
  pack_valid

Registry:
  cataloged / artifact_ready / revoked / superseded

Computed per request:
  model_compatible / environment_compatible / executable

Scientific evidence:
  benchmark_passed / scientifically_validated / promotion_eligible

Product policy:
  production_promoted

它们不是自动递进状态链。

所有真实模型阶段必须：

1. 在 test/external 前冻结 task、scope、Pack、feature/output、split、baseline、
   metric/direction、CI、OOD、external policy 和 promotion gate；
2. 按 biological group 切分，审计 donor/condition/replicate/batch leakage；
3. tuning 和 threshold 只读 train/validation；
4. external 默认 adaptation steps=0；
5. 主指标严格胜预声明简单 baseline，paired CI 支持改善；
6. stochastic model 使用预登记 seeds；
7. uncertainty/OOD 不存在时写 unavailable；
8. 任一 gate 失败时保存负结果并 abstain；
9. synthetic/tiny/mock 不能成为科学 evidence；
10. 软件完成、科学 evidence 和 product policy 分开报告。

永久禁止：

- 静默 normalization、补零、imputation、去重、重排、随机 split；
- 未声明 gene ID、symbol、ortholog 或 unit 转换；
- textbook/mock/random/case fallback 冒充模型；
- upload receipt 直接当 Pack；
- 大数据、checkpoint 或权重进入 Git；
- 用户上传内容作为任意代码执行；
- 覆盖已有外置 artifact；
- LLM 修改数值、evidence、policy 或 verdict；
- Agent 共识替代科学证据。

十、每个已授权代码阶段的执行顺序

1. 核对 repo、Git metadata、branch、starting SHA、status 和保护对象；
2. 完整阅读当前阶段相关文档、ADR、runbook、代码和测试；
3. 明确 scope、non-goals、资产和外部操作边界；
4. 写或确认 ADR、contracts 和 predeclared scientific gates；
5. 先写 fail-closed/negative 红灯测试；
6. 做最小实现；
7. 运行定向测试；
8. 运行受影响 core、legacy、frontend、Ruff 和 pip check；
9. 如有真实 science，先冻结 protocol，再访问获批资产；
10. 生成 immutable artifact/result fingerprints；
11. 做 adversarial audit：坏 hash、错 scope、缺 adapter、OOD、leakage、LLM
    injection、path/secret、历史 identity 和 partial failure；
12. 只 stage 当前授权文件；
13. 只有授权允许时才本地 commit；
14. post-commit 重跑要求的验证；
15. 写阶段完成报告；
16. 生成下一阶段精确授权句；
17. 停止。

不得因为测试时间长、结果为负或实现困难而提前结束；应持续完成所有仍在授权范围内
且安全可行的工作。只有缺权限、缺 exact asset、缺科学硬前置或外部状态确实阻塞时
才报告 BLOCKED。

十一、硬停止规则

出现以下任一情况立即停止当前写操作并报告：

1. repo、git-dir、branch 或 starting HEAD 与授权不符；
2. 出现未声明 dirty/untracked 文件，或 scope 与保护文件重叠；
3. 依赖门、asset manifest、hash、license、privacy、consent 或 operator identity
   不完整；
4. 需要未授权 network、remote、external write、push、main/tag 或 deploy；
5. run-only/operator-only 窗口需要修改 workspace 或 Git；
6. 测试或科学 gate 已形成诚实负结果；
7. 当前 work unit 已完成。

停止时不得 reset、stash、checkout、同步、删除、覆盖或放宽科学门。

十二、完成报告固定格式

Phase:
Work unit:
Status:
Outcome: completed_positive | completed_negative | blocked
Starting SHA:
Completion SHA or unchanged code SHA:
Branch:

Authorized scope:
Explicit non-goals:
Changed files:
Protected files/state:

Schemas/contracts:
Data/Pack fingerprints:
Model/adapter/environment fingerprints:
Benchmark/result fingerprints:
Operator policy fingerprint:

Tests:
- red/fail-closed:
- directional:
- core:
- legacy:
- frontend:
- Ruff/pip check:
- packaging:
- remote/LLM/GPU/external explicitly not run:

Scientific result:
- exact task/scope:
- baseline:
- primary metric/direction/CI:
- external/OOD:
- benchmark_passed:
- scientifically_validated:
- promotion_eligible:
- production_promoted:
- abstain behavior:

Negative results retained:
Known limitations:
GitHub/push/main/tag state:
.53/remote state:
Go condition satisfied:
Next eligible work unit:
Next exact authorization sentence:

skip/deselect 不能写成 LLM、GPU、remote、external 或 scientific validation 通过。

十三、接手审计固定输出

Mode: READ_ONLY_AUDIT
Workspace:
Git metadata:
Branch:
HEAD:
Staged:
Modified/deleted/untracked:
Protected paths:
Last completion evidence:
Engineering/science/policy ledger:
Next eligible work unit:
Dependencies satisfied:
Authorization present:
Authorization valid:
Missing fields/blockers:
Mutations performed: none

如果授权无效或缺失，随后附：

Next authorization draft: NOT ACTIVE — user must send explicitly
STOPPED — awaiting explicit user authorization

十四、接手后的第一条回复

完成只读首检以后，用简短、可验证的格式回复：

1. 当前 repo、Git metadata、branch 和 HEAD；
2. 当前 staged/modified/deleted/untracked 文件；
3. 当前最后一个有完成证据的 Phase；
4. 唯一 Next eligible work unit 和 Next numbered Phase；
5. 该 work unit 的前置门是否满足；
6. 当前是否已有精确授权；
7. P12 未完成且当前会话保有完整 exact P12 授权时，只继续 P12；缺任何授权字段时
   报告 blocker 并停止，不能由本提示词补齐；
8. 明确本轮没有执行任何写操作；
9. 如现场已有 P12 completion SHA/报告，只生成标记为 `NOT ACTIVE`、仍需用户主动
   发送的 P13 条件式授权草案，然后停止。

本提示词编写时，预期结论是：

已完成 Phase 11；
DOCS-CLOSURE completion 是 b19c896202bea56f894d0ad540501331af42a40c；
当前唯一 work unit 是 P12，starting SHA 同为 b19c896...，branch 是
codex/p12-model-registry-v2，状态为 VALIDATING；
P12 completion SHA 尚未形成，不能提前写 COMPLETE；
P13 只是 P12 完成后的条件式下一候选，当前未授权，任何草案均 NOT ACTIVE。

如果现场已有更新，以现场 exact evidence 为准，不要把上述预期强行写回仓库。
```

## 与其他文档的关系

- 详细 phase scope 和逐阶段授权模板：
  [P12–P30 权威执行路线](PHASE12-30-EXECUTION-PLAN-AND-PROMPTS.md)
- 可逐项勾选的完成计划：
  [P12–P30 详细完成计划](PHASE12-30-DETAILED-COMPLETION-CHECKLIST.md)
- 更完整的长期治理背景：
  [P12–P30 总控提示词](PHASE12-30-MASTER-PROMPT.md)
