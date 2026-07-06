# Phase 9 前端重设计:科研任务控制台 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 用 `superpowers:subagent-driven-development` 逐 task 实现。步骤用 `- [ ]` 复选框跟踪。
> 本计划由规划 subagent 对着**真实前端代码**展开(读了 `praxis_vc_react/` 的 `App.tsx` / `api.ts` / `views/{AskView,ParseReviewView,ConfirmView,ModuleContextView,RunConfirmView,ResultView,Sidebar}.tsx` / `index.css` / `App.css` / `package.json` / `vite.config.ts` / `tsconfig*.json` / `.gitignore`),无臆测。权威设计定稿:`docs/superpowers/specs/2026-07-06-frontend-redesign-design.md`(以下简称 **spec**),本计划忠实落地它,不改任何设计决策。

**Goal:** 把现有 7 步 useState 向导式前端,重构为 spec 定义的 5 阶段(Ask→Review→Route→Run→Results)科研任务控制台——学术精致视觉系统(暖白 + 深靛蓝 + 少量翠绿;Newsreader/Inter/JetBrains Mono self-host)+ 组件化目录树(spec §5)+ `Stage`/`JobState` 状态机(spec §6)+ 6 tab 证据化结果页 + 6 个数据可视化组件(Recharts 标准图 + 手写 SVG 模块/trace 图)。**后端零改动。**

**Architecture:** 纯前端重构,零后端改动。信息架构 7→5、视觉系统重写、结果页证据化。数据源全部复用 Phase 8 已有只读端点(`/api/parse` `/api/options` `/api/modules` `/api/jobs` `/api/reports/{id}` 及 `/trace` `/provenance` `/module-plan` `/markdown`)。`api.ts` 基本不变(仅按需补 UI 派生类型)。现有 `App.tsx` 7 步 → `components/layout/AppShell` + `Stage` 状态机;`views/*` 拆/迁到 `components/{layout,stages,result,visualization,ui}/*`;`index.css`/`App.css` 拆为 `styles/{tokens,base,components,themes}.css`。前端只读展示,不碰任何科学/治理决策。

**Tech Stack:** React 19 + Vite 8 + TypeScript(strict, `noEmit`)+ oxlint;新增 `recharts`(标准统计图)+ `@fontsource/newsreader` / `@fontsource/inter` / `@fontsource/jetbrains-mono`(self-host 字体打包进 dist 离线可用);模块路由图 / agent trace 图 = 手写 SVG(不引入图库)。**前端不引入测试栈**(延续用户决策)——每 task 用 **build-verified** 模板:改/建文件 → `npm run build`(`tsc -b` + `vite build`)+ `npm run typecheck`(新增)+ `npm run lint`(oxlint)全过 → 手动验证清单 → commit。运行时点击冒烟由**控制器在 Phase 末用 playwright 统一做**(P6),不要求每 task 真跑浏览器。

---

## 🔴 红线(RED-LINES,展开前已定,写进每个相关 task,实施每一步守)

1. **后端零改动**:不碰 `praxis_virtualcell/` 任何 Python、不碰 `praxis_vc_api/`、不碰根 `tests/`、不碰后端 CI。所有科学裁决仍由确定性 runtime 完成,前端只读展示。
2. **前端只读展示**,不做任何预测/治理判断;OFFLINE 全程 `llm_used=false`,保留现有"⚠ LLM 未参与预测/治理决策"提示语义。
3. **Stage 3 Route 只静态预期路由**:module_plan 是 run 产物,运行前**不重算真实路由**。Stage 3 基于 `species`(+可选 `cell_type`)匹配 cell preset 的 `modules[]` 元数据 + `/api/modules` 目录做"**预期,非实际**"展示,**必须在 UI 上明确标注**(继承现 `ModuleContextView` 的红字注意语义)。**真实路由结果在 Stage 5 的 `Module Routing` tab**(run 后 `/api/reports/{id}/module-plan`)。
4. **Stage 4 Run 同步执行**:后端 `/api/jobs` 是同步返回(`createJob` 一次 await 即拿 `job_id`),**非流式**。所以"运行中 live trace"**是确定性步骤清单指示**(Validating → Resolving species → … → Saving provenance 等固定文案的进度指示),**不是真流式**;真实 32 步 trace 在 Stage 5 `Trace` tab(`/trace`)。
5. **前端不引入测试栈**(延续用户决策),质量靠 `build` + `typecheck` + `lint` + Phase 末 playwright 冒烟。
6. **引入依赖仅前端**(`recharts` + 三个 `@fontsource/*`),不影响 Python/后端/CI 的 `praxis_virtualcell` 口径。
7. **提交纪律:** 每 task 一提交;commit 前 `find . -name '._*' -delete`;trailer 恒定 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`;在分支 `feat/v0.9-phase0-module-core` 提交;**不 push**。

**房规(每个实现 subagent):** venv 无关(纯前端);前端命令全部在 `praxis_vc_react/` 下执行;`dist` 已 `.gitignore`,不提交构建产物;commit 前删 `._*`。

---

## 状态机映射(spec §6,P2 落地依据)

**现状(`App.tsx`):** 7 步扁平 `Step` union(`ask | parse_review | confirm | module_context | run_confirm | result | advanced`),数据散在 6 个独立 `useState`(`parseResult` / `confirmedRequest` / `jobId` / `openedJobId` / `jobs` / `mode`)。`openedJobId` 分支:侧栏点历史 job → 直接渲染 `ResultView`,与查询流互斥。

**目标(spec §6):**
```ts
type Stage = "ask" | "review" | "route" | "run" | "results";
type RunStatus = "idle" | "running" | "succeeded" | "failed" | "abstained";
type JobState = {
  query: string;
  parsedIntent: ParseResult | null;          // 复用 api.ts 现有 ParseResult
  confirmedRequest: Record<string, unknown> | null;  // Review 阶段编辑产物
  modulePlan: ModulePlan | null;              // Stage3 静态预期(前端派生)+ Stage5 实际(/module-plan)
  runStatus: RunStatus;
  jobId: string | null;
};
```

**7→5 映射表:**

| 旧 Step | 新 Stage | 说明 |
|---|---|---|
| `ask` | `ask` | Ask 阶段,POST /api/parse |
| `parse_review` + `confirm` | `review` | **合并**:解析摘要(只读元信息)+ 可编辑分组表单同页 |
| `module_context` | `route` | 静态预期路由预览(红线 3) |
| `run_confirm` | `run` | execution manifest + Start run + 确定性进度指示(红线 4) |
| `result` + `advanced` | `results` | **合并**:6 tab 证据页(不再拆"高级"步) |

**stepper 规则(spec §6):** ask→review 需 parse 成功;review→route 需 required fields complete(至少 `species` 非空,复用现 Confirm 的 `disabled={!species.trim()}` 语义);route→run 需 module plan available(静态预期已算出即可);run→results 需 `runStatus ∈ {succeeded, failed, abstained}`。**已完成阶段可点回退**(StepperRail 上点亮);**不允许跳过 review**;回退**不丢数据**(`JobState` 集中保存,回退只改 `stage` 不清字段);重新运行从 run 或 results 发起。

**Sidebar 历史 job 语义保留:** 现 `openedJobId` 分支 → 新 `AppShell` 保留一个"打开历史 job"模式:侧栏点历史 job 时,直接进入 `results` 阶段并以该 `job_id` 拉 6 tab 数据(等价现 `openedJobId` 渲染 `ResultView`),与"新建查询流"互斥;点"新建查询"重置 `JobState` 回 `ask`。`activeJobId` 高亮逻辑迁移到 `AppShell`。

---

## 6 tab 数据源映射(spec §2 Stage5 / §4,P5 落地依据)

| tab | 组件 | 数据源(真实端点/字段) | 渲染方式 |
|---|---|---|---|
| `Report` | `ReportTab` | `getReport()` → `structured_report`(summary/prediction/reliability/boundary)+ `narrative_report` + `getReportMarkdown()`(`/markdown`) | HTML 分块(迁现 ResultView 的 ReportTab 5 块) |
| `Predictions` | `PredictionsTab` | `structured_report.prediction` / `.model_disagreement` / `.learned_reliability`(reliability_score) | **Recharts**:① Δgene top changes bar ② module/pathway response score bar ③ disagreement/uncertainty strip。offline 为 mock 数值,如实展示,不推断真值 |
| `Module Routing` | `ModuleRoutingTab` | `getModulePlan()`(`/module-plan`)→ `ModulePlan{primary,secondary,overall_verdict,entries[]}` | **手写 SVG** `ModuleRoutingGraph`(primary/secondary/handoff/verdict/abstain/confidence)+ 降级 entries 表 |
| `Evidence` | `EvidenceTab` | `structured_report.provenance`(`rules_referenced`/`rules_hit`)+ boundary 字段(`failed_checks`/`critic_violations`/`caution_flags`)+ `models_used/rejected/failed` | 证据表(HTML table)+ 可选 `EvidenceDistributionChart` |
| `Trace` | `TraceTab` | `getTrace()`(`/trace`)→ `trace[]`(`timestamp`/`sender`/`receiver`/`message_type`) | **手写 SVG** `AgentTraceTimeline`(默认 6–8 关键节点,可展开完整 32 步) |
| `Provenance` | `ProvenanceTab` | `getProvenance()`(`/provenance`)→ `provenance` + `llm_meta` + job metadata | 审计页 HTML + 可下载 JSON |

**下载/copy(迁现 ResultView 逻辑):** download report.json / narrative.md / report.md(现有);新增 copy report、copy provenance summary。

---

## 目标文件结构(spec §5)

```text
praxis_vc_react/src/
  api.ts                 # 基本不变,仅按需补 UI 派生类型
  main.tsx               # 改 import(index.css → styles/index.css 聚合)
  App.tsx                # 瘦身为渲染 <AppShell/>
  components/
    layout/    AppShell.tsx  TopBar.tsx  JobSidebar.tsx  Workspace.tsx  StepperRail.tsx
    stages/    AskStage.tsx  ReviewStage.tsx  RouteStage.tsx  RunStage.tsx  ResultsStage.tsx
    result/    ReportTab.tsx  PredictionsTab.tsx  ModuleRoutingTab.tsx  EvidenceTab.tsx  TraceTab.tsx  ProvenanceTab.tsx
    visualization/  ModuleRoutingGraph.tsx  AgentTraceTimeline.tsx  ReliabilityMeter.tsx  PredictionBarChart.tsx  EvidenceDistributionChart.tsx
    ui/        Button.tsx  Card.tsx  Badge.tsx  FieldRow.tsx  StatusPill.tsx  Tabs.tsx  EmptyState.tsx  Skeleton.tsx
  styles/      index.css  tokens.css  base.css  components.css  themes.css  fonts.css
```
> 旧 `views/*` 与 `index.css`/`App.css` 在各 Phase 迁移完成后删除(P3/P5 末尾清理),避免双份来源。

---

## 通用 task 模板(build-verified,非 TDD)

每个前端 task 一律:
1. **改/建文件**(Files 精确路径 + 职责一句话 + 关键 props/数据源 + 骨架要点)。
2. `cd praxis_vc_react && npm run build`(= `tsc -b` + `vite build`)通过。
3. `npm run typecheck`(= `tsc -b`,P1 新增)通过。
4. `npm run lint`(oxlint)通过。
5. **手动验证清单**(关键渲染/交互点,肉眼或 `vite preview` 静态核对;运行时点击冒烟留给 P6 playwright)。
6. `find . -name '._*' -delete` → `git add <精确文件>` → commit(trailer 正确)→ **不 push**。

> ⚠️ `tsconfig.app.json` 已含 `"noEmit": true`,故 `tsc -b` 本身即"类型检查不产出",`typecheck` script 设为 `tsc -b` 即等价 spec 意图的 `tsc -b --noEmit`(`--noEmit` 已被工程配置隐含)。

---

# P1 · 设计 token + 基础布局(4 task)

> 目标:页面气质变对(不再像 ChatGPT);light/dark 双主题可用;build 通过。**Task 9.1 引入依赖需网络,离线则 BLOCKED。**

## Task 9.1: 引入依赖 + typecheck script + 字体/样式脚手架

**Files:**
- Modify: `praxis_vc_react/package.json`(加 deps + `typecheck` script)
- Create: `praxis_vc_react/src/styles/fonts.css`(import @fontsource 面孔)
- Create: `praxis_vc_react/src/styles/index.css`(聚合入口,先只 `@import "./fonts.css";`)

**职责:** 一次性把本 Phase 所有第三方依赖装齐、字体 self-host 打包、补 `typecheck` script,给后续 task 铺好地基。

- [ ] **Step 1(⚠️ 需网络,离线则本 task BLOCKED):** `cd praxis_vc_react && npm install recharts @fontsource/newsreader @fontsource/inter @fontsource/jetbrains-mono`
  - 依赖装 `dependencies`;若无网络,**标记本 task BLOCKED 并停止**(后续 task 依赖它),报告"npm install 需网络,离线 BLOCKED"。
- [ ] **Step 2:** `package.json` `scripts` 加 `"typecheck": "tsc -b"`(build/lint 不动)。
- [ ] **Step 3:** 建 `src/styles/fonts.css`,self-host import(只引所需字重,控制体积):
  ```css
  @import "@fontsource/newsreader/400.css";
  @import "@fontsource/newsreader/500.css";
  @import "@fontsource/newsreader/600.css";
  @import "@fontsource/inter/400.css";
  @import "@fontsource/inter/500.css";
  @import "@fontsource/inter/600.css";
  @import "@fontsource/jetbrains-mono/400.css";
  ```
- [ ] **Step 4:** 建 `src/styles/index.css`,首行 `@import "./fonts.css";`(tokens/base/components/themes 由 9.2–9.3 追加)。**暂不改 `main.tsx`**(9.3 统一切换 import,避免中途样式缺失白屏)。
- [ ] **Step 5:** build + typecheck + lint 全过。**手动验证:** `node_modules/@fontsource/*` 下有 woff2(依赖装成功)、fonts.css/index.css 建成且 @import 能 resolve。⚠️ **dist 含 woff2 的验证移到 Task 9.3**:本 task 按 Step 4 有意不改 main.tsx,`styles/index.css` 尚未被任何模块引用,vite 会 tree-shake 掉,故本 task `dist` woff2=0 是**预期**(不是缺陷);main.tsx 接入 `styles/index.css` import 后(9.3)才进 dist。

**验收:** 三依赖入 `package.json`;`typecheck` script 存在且过;fonts.css/index.css 脚手架就绪(**dist 含 woff2 的验证在 Task 9.3 切 main.tsx 入口后核**,本 task 不要求 dist woff2)。
**commit:** `git add package.json package-lock.json src/styles/fonts.css src/styles/index.css`
```
git commit -m "$(cat <<'EOF'
build(phase9): 引入 recharts + self-host 字体(Newsreader/Inter/JetBrains Mono)+ typecheck script

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```
> 🔴 红线:仅前端依赖;不碰后端/CI。

## Task 9.2: 设计 token 与主题(styles/tokens.css + themes.css)

**Files:**
- Create: `praxis_vc_react/src/styles/tokens.css`
- Create: `praxis_vc_react/src/styles/themes.css`

**职责:** 把 spec §3 配色/字体/卡片规范落成 CSS 变量;light/dark 双主题,dark 用 `[data-theme="dark"]` 类切换(现 `index.css` 用 `@media prefers-color-scheme`,改为可手动 toggle,配合 TopBar 主题开关)。

- [ ] **Step 1:** `tokens.css` `:root` 落 spec §3 精确色值:
  ```css
  :root {
    --bg: #FDFDFC; --surface: #FFFFFF;
    --text: #1A1A2E; --text-muted: #5F6572;
    --primary: #1E3A5F;            /* 深靛蓝,按钮/主结构,不用黑 */
    --accent: #2F8F83;             /* 翠绿,仅状态色,不作主色/大面积 */
    --warn: #B7791F; --danger: #B42318;
    --border: #E6E3DC; --code-bg: #F6F4EF;
    --radius-card: 16px; --card-shadow: 0 1px 2px rgba(20,20,20,0.04);
    --font-serif: "Newsreader", Georgia, serif;   /* 仅大标题 */
    --font-sans: "Inter", system-ui, sans-serif;  /* 正文/表单/按钮 */
    --font-mono: "JetBrains Mono", ui-monospace, monospace; /* json/trace/schema */
  }
  ```
- [ ] **Step 2:** `themes.css` 加 `[data-theme="dark"]` 覆盖(暖白→深底,深靛蓝提亮保对比;翠绿仍仅状态色)。默认跟随 `prefers-color-scheme` 但可被 `data-theme` 覆盖。
- [ ] **Step 3:** `styles/index.css` 追加 `@import "./tokens.css"; @import "./themes.css";`(排在 fonts 之后)。
- [ ] **Step 4:** build + typecheck + lint 全过。**手动验证:** `vite preview` 下 `document.documentElement` 切 `data-theme="dark"` 时背景/文字随之变(此刻页面仍是旧壳,只验变量生效)。

**验收:** token 色值与 spec §3 逐一对齐;dark 类可切;衬线只声明给标题变量。
**commit:** `plan`→ 实际 message:
```
git commit -m "$(cat <<'EOF'
style(phase9): 设计 token + light/dark 主题(暖白/深靛蓝/翠绿状态色,Newsreader/Inter/Mono)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```
> 🔴 红线:翠绿 `--accent` 仅状态色不作主色;按钮用 `--primary` 深靛蓝不用黑。

## Task 9.3: 基础排版 + 组件基样式 + 切换样式入口

**Files:**
- Create: `praxis_vc_react/src/styles/base.css`(reset/排版/标题用衬线/正文用 Inter)
- Create: `praxis_vc_react/src/styles/components.css`(卡片/按钮/表单/表格/tab/badge/pill 基样式,迁并重写现 `index.css`+`App.css` 有用规则)
- Modify: `praxis_vc_react/src/main.tsx`(`import './index.css'` → `import './styles/index.css'`)
- Modify: `praxis_vc_react/src/styles/index.css`(追加 base/components import)

**职责:** 把散在 `index.css`/`App.css` 的排版与组件样式重写进 `styles/`,并切换全局样式入口。**此 task 后旧 `index.css`/`App.css` 暂留**(P3 各 Stage 迁完再删),但 `main.tsx` 已指向新入口。

- [ ] **Step 1:** `base.css`:body 用 `--font-sans`;`h1,h2`(hero/页面大标题)用 `--font-serif`;`code,pre` 用 `--font-mono` + `--code-bg`;卡片规范(spec §3:`background:#fff;border:1px solid var(--border);border-radius:16px;box-shadow:var(--card-shadow)`),层次靠间距/字重/小标题/分隔/状态点,不靠大色块。
- [ ] **Step 2:** `components.css`:`.btn`(深靛蓝实心)/`.btn-ghost`/表单/`.kv-table`/`.tabs .tab`/`.badge`/`.pill` 等,复用现 `App.css` 的类名以降低组件改造成本,但配色改到新 token。
- [ ] **Step 3:** `main.tsx` 切 import(`./index.css` → `./styles/index.css`);`index.css` 追加 base/components。切入口后 **build 并验证 `dist/assets/` 出现 `.woff2`**(Task 9.1 的 self-host 字体此刻真正进 dist,证明打包离线可用;此即从 Task 9.1 移来的 woff2 验证)。
- [ ] **Step 4:** build + typecheck + lint 全过。**手动验证:** `vite preview` 现有页面用新样式渲染(标题变衬线、按钮变深靛蓝、背景变暖白),无白屏、无控制台报错。

**验收:** 全局字体/配色切到新系统;旧页面仍能渲染(过渡期共存)。
**commit:**
```
git commit -m "$(cat <<'EOF'
style(phase9): 基础排版 + 组件基样式迁入 styles/,main 切新样式入口

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

## Task 9.4: ui 原子组件(Button/Card/Badge/StatusPill/FieldRow/Tabs/EmptyState/Skeleton)

**Files:**
- Create: `praxis_vc_react/src/components/ui/{Button,Card,Badge,StatusPill,FieldRow,Tabs,EmptyState,Skeleton}.tsx`

**职责:** 建后续所有 Stage/tab 复用的无状态 UI 原子组件,统一视觉与状态语义(spec §2 字段状态:`confirmed`/`inferred`/`missing`/`editable`/`locked`)。

- [ ] **Step 1:** 各组件 props(TypeScript,尽量窄):
  - `Button`: `{variant?: "primary"|"ghost"|"danger"; size?: "sm"|"md"; disabled?; onClick?; children}`
  - `Card`: `{title?; children}`(spec §3 卡片壳)
  - `Badge`: `{tone: "confirmed"|"inferred"|"missing"|"neutral"|"warn"|"danger"; children}`
  - `StatusPill`: `{status: "confirmed"|"inferred"|"missing"|"editable"|"locked"}`(spec §2 字段状态点/图标)
  - `FieldRow`: `{label; status?: StatusPill 的 status; children}`(Review 表单行:标签 + 状态 + 值/输入)
  - `Tabs`: `{tabs: {id;label}[]; active; onChange}`(受控)
  - `EmptyState`: `{title; hint?}`；`Skeleton`: `{lines?; height?}`(加载降级)
- [ ] **Step 2:** 全部纯展示、无副作用、无数据请求;样式走 `components.css` 类 + token。
- [ ] **Step 3:** build + typecheck + lint 全过(oxlint `noUnusedLocals`——未被引用组件先 `export` 即可,或加占位使用于 9.5+)。**手动验证:** 临时在 `App.tsx` 挂一组样例渲染,肉眼核对状态色(confirmed=深靛勾/inferred=amber/missing=红橙),核对完撤掉临时挂载再 commit。

**验收:** 8 个原子组件类型完整、状态语义齐、复用 token。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): ui 原子组件(Button/Card/Badge/StatusPill/FieldRow/Tabs/EmptyState/Skeleton)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

# P2 · 5 阶段状态机(3 task)

> 目标:7→5 流程改造;`Stage`/`JobState` 落地;Ask→…→Results 走通;回退不丢数据;后端零改。此 Phase 建**布局骨架 + 状态机**,Stage 内容先接现有 `views/*`(占位复用),P3 再逐个替换成新 Stage 组件——保证每 task build 绿、流程不断。

## Task 9.5: JobState 状态机 + AppShell 骨架

**Files:**
- Create: `praxis_vc_react/src/components/layout/AppShell.tsx`(状态机宿主)
- Modify: `praxis_vc_react/src/App.tsx`(瘦身为 `return <AppShell/>`)
- Modify: `praxis_vc_react/src/api.ts`(仅追加 UI 派生类型 `Stage`/`RunStatus`/`JobState`,不改任何请求方法)

**职责:** 落 spec §6 `Stage`/`JobState`,集中管理阶段与数据;定义 stepper 回退/禁用规则;保留 Sidebar 历史 job 语义。

- [ ] **Step 1:** `api.ts` 末尾追加类型(不动现有):`Stage`/`RunStatus`/`JobState`(见本计划"状态机映射";`parsedIntent: ParseResult|null`,`modulePlan: ModulePlan|null`)。
- [ ] **Step 2:** `AppShell` 用 `useState<JobState>` + `stage` + `mode` + `jobs`/`health` + `openedJobId`(历史 job 模式)。迁移现 `App.tsx` 的 `loadJobs`/`health`/`newQuery`/`activeJobId` 逻辑。
- [ ] **Step 3:** stepper 规则函数 `canEnter(stage): boolean`(ask→review 需 `parsedIntent`;review→route 需 `confirmedRequest?.species`;route→run 需 `modulePlan`(静态预期);run→results 需 `runStatus∈{succeeded,failed,abstained}`);回退不清 `JobState` 字段(只改 `stage`)。
- [ ] **Step 4:** 布局:左 `JobSidebar`(占位:先内联现 `Sidebar` 或简版)+ 右 `Workspace`(占位:先按 `stage` 渲染现有 `views/*`,用 `JobState` 字段喂进去,桥接旧 props)。历史 job:`openedJobId` 存在时 `Workspace` 直接进 `results` 模式渲染现 `ResultView`。
- [ ] **Step 5:** `App.tsx` 仅 `import AppShell` 并渲染。
- [ ] **Step 6:** build + typecheck + lint 全过。**手动验证:** `vite preview` 走 Ask→(parse)→review→…→results 全链路不断;侧栏点历史 job 进 results;点新建查询重置回 ask;回退阶段数据不丢。

**验收:** 5 阶段状态机跑通(内容暂用旧 views);回退不丢数据;历史 job 语义保留;后端零改。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): Stage/JobState 状态机 + AppShell 骨架(7→5,回退不丢数据,保留历史 job 语义)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```
> 🔴 红线:`api.ts` 只加类型不改请求;后端零改动。

## Task 9.6: JobSidebar + TopBar(布局层)

**Files:**
- Create: `praxis_vc_react/src/components/layout/JobSidebar.tsx`(重写现 `Sidebar`)
- Create: `praxis_vc_react/src/components/layout/TopBar.tsx`
- Modify: `praxis_vc_react/src/components/layout/AppShell.tsx`(接线)

**职责:** 左侧独立 Job Sidebar(历史 job / 最近运行 / 收藏区位;**不与步骤轨混**);TopBar 含 mode pill、"⚠ LLM 未参与预测/治理决策"提示、**light/dark 主题开关**(切 `document.documentElement[data-theme]`)。

- [ ] **Step 1:** `JobSidebar` props 同现 `Sidebar`(`jobs`/`activeJobId`/`onNewQuery`/`onOpenJob`/`health`/`healthErr`/`mode`),视觉重写到新 token;分区:品牌 / 新建查询 / 历史 Jobs(现有)/(收藏区位留结构,数据暂空)。
- [ ] **Step 2:** `TopBar` props `{mode; onMode; theme; onToggleTheme}`;含 mode pill、LLM 提示 pill、主题开关按钮。
- [ ] **Step 3:** `AppShell` 管 `theme` state + `data-theme` 副作用;接线 TopBar/Sidebar。
- [ ] **Step 4:** build + typecheck + lint 全过。**手动验证:** 主题开关点击后全站明暗切换;侧栏历史 job 高亮当前;窄屏(spec §1 降级:Top Bar→Header→水平 stepper→内容)不横向溢出(CSS 媒体查询降级,先保证不破)。

**验收:** Sidebar 独立不混步骤;TopBar 主题开关生效;LLM 提示语保留。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): JobSidebar + TopBar 布局层(独立历史 job 侧栏 + 主题开关 + LLM 提示)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

## Task 9.7: StepperRail + Workspace(主工作区内左侧阶段轨)

**Files:**
- Create: `praxis_vc_react/src/components/layout/StepperRail.tsx`
- Create: `praxis_vc_react/src/components/layout/Workspace.tsx`
- Modify: `praxis_vc_react/src/components/layout/AppShell.tsx`(接线)

**职责:** Stepper Rail 放主工作区内部左侧(spec §1),显 5 阶段进度;已完成阶段可点回退,未满足 `canEnter` 的阶段禁用。Workspace 按 `stage` 渲染 Stage 内容(此刻仍桥接旧 views,P3 替换)。

- [ ] **Step 1:** `StepperRail` props `{stage; canEnter:(s)=>boolean; onJump:(s)=>void}`;5 阶段(Ask/Review/Route/Run/Results)竖向 rail;当前高亮(深靛蓝)、已完成可点、未达标禁用(灰);不允许跳过 review。
- [ ] **Step 2:** `Workspace` props `{stage; jobState; ...handlers}`;`switch(stage)` 渲染,内容暂桥接旧 `views/*`(与 9.5 一致),窄屏改水平 stepper。
- [ ] **Step 3:** `AppShell` 接线,移除临时内联。
- [ ] **Step 4:** build + typecheck + lint 全过。**手动验证:** 走到 results 后点 rail 回 review 改字段再前进,数据不丢;未满足条件的阶段点不动(禁用)。

**验收:** Stepper 在工作区内、回退/禁用规则对、窄屏降级为水平。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): StepperRail + Workspace(工作区内 5 阶段轨,回退/禁用规则,窄屏降级)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

# P3 · 重写 5 个 Stage 页(5 task)

> 目标:表单向导 → 科研控制台;每阶段科研目的明确。逐个用新 `components/stages/*` 替换 Workspace 里桥接的旧 `views/*`;Stage 全替换完删旧 `views/*`(除仍被 Results 复用的逻辑,迁走后删)。

## Task 9.8: AskStage(科研感 hero 输入)

**Files:**
- Create: `praxis_vc_react/src/components/stages/AskStage.tsx`
- Modify: `praxis_vc_react/src/components/layout/Workspace.tsx`(接 AskStage)

**职责:** spec §2 Stage1——科研感 hero(非 ChatGPT 聊天窗)+ 3 示例(gene perturbation / drug response / metabolic stress)+ 可选 "Advanced input" 折叠区(上传结构化 JSON / 选物种)。数据:POST `/api/parse`(复用 `parse()`)。

**props/数据源:** `{mode; onMode; onParsed:(ParseResult, query:string)=>void}`;调 `parse(text, mode)`。
- [ ] **Step 1:** hero 标题(Newsreader 衬线)+ 大输入 textarea + 模式选择 + `Parse →`;3 个示例 chip 点击填入 textarea(示例文案:gene 例"在 human 细胞敲 AHR";drug 例"vorinostat 处理 A549";metabolic 例"葡萄糖限制下的 yeast 代谢应激")。
- [ ] **Step 2:** `<details>` Advanced input:选物种(可留占位)/ 粘贴结构化 JSON(仅前端组装,不新增端点)。
- [ ] **Step 3:** `parse` 成功 → `onParsed(result, text)` 写入 `JobState.parsedIntent`/`query` 并前进 review;失败显错不崩。
- [ ] **Step 4:** build + typecheck + lint 全过。**手动验证:** 点示例填入、Parse 进 review、错误态显示。

**验收:** hero 非聊天窗观感;3 示例可点;Advanced 折叠;parse 走通。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): AskStage 科研感 hero 输入(3 示例 + Advanced 折叠,复用 /api/parse)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```
> 🔴 红线:解析全在后端;前端不解析。

## Task 9.9: ReviewStage(解析摘要 + 可编辑分组表单,合并旧 parse_review+confirm)

**Files:**
- Create: `praxis_vc_react/src/components/stages/ReviewStage.tsx`
- Modify: `praxis_vc_react/src/components/layout/Workspace.tsx`(接 ReviewStage)

**职责:** spec §2 Stage2(最重要)——解析摘要 + 可编辑表单,字段分组(Biological system / Perturbation / Requested outputs / Assumptions),每字段带状态(`confirmed`/`inferred`/`missing`/`editable`/`locked`,用 `StatusPill`/`FieldRow`)。让科学家感觉系统运行前让人审阅任务定义。数据:上一步 `ParseResult`(前端 state)+ `/api/options`(`getOptions`,cell preset/枚举下拉)。

**props/数据源:** `{parsedIntent: ParseResult; initialRequest; onConfirmed:(request)=>void; onBack}`;`getOptions()` 拉枚举/预设。
- [ ] **Step 1:** 分组卡:**Biological system**(species 下拉[枚举+保留当前值]、cell_type、cell preset 载入)/ **Perturbation**(perturbation_type 下拉、perturbation_targets 逗号分隔)/ **Requested outputs**(task_type 等只读或可选)/ **Assumptions**(只读:`assumptions`/`missing_fields`/`errors`/`clarification_required` + parser/llm_used/schema_valid 元信息)。迁 `ConfirmView` 的 `applyPreset`/`withCurrent`/组装逻辑 + `ParseReviewView` 的元信息展示。
- [ ] **Step 2:** 字段状态映射:候选值存在且非推断→`confirmed`;`assumptions`/推断得到→`inferred`(amber);`missing_fields` 命中→`missing`(红橙);可编辑字段→`editable`(pencil);不可改字段→`locked`。用 `FieldRow`+`StatusPill`。
- [ ] **Step 3:** 组装 request(以 `candidate_request` 为基底覆盖可编辑字段,保留 `request_id`/`metadata`),`onConfirmed(request)` 写 `JobState.confirmedRequest` 前进 route;`disabled` 规则:`!species.trim()`(等价现 Confirm)。
- [ ] **Step 4:** build + typecheck + lint 全过。**手动验证:** 改 species/targets 一字段后状态点更新;缺失字段红橙提示;载入 preset 填充;确认前进 route 且 `confirmedRequest` 正确。

**验收:** 分组表单 + 字段状态齐;合并了旧两步;组装 request 与旧 Confirm 等价。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): ReviewStage 解析摘要+可编辑分组表单(字段状态化,合并 parse_review+confirm)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```
> 🔴 红线:前端只组装/展示,不做治理判断。

## Task 9.10: RouteStage(Module Routing Preview,静态预期)

**Files:**
- Create: `praxis_vc_react/src/components/stages/RouteStage.tsx`
- Modify: `praxis_vc_react/src/components/layout/Workspace.tsx`(接 RouteStage)

**职责:** spec §2 Stage3——"Module Routing Preview":primary / secondary / not activated 分组 + handoff 关系,每模块卡片(名称/触发原因/输入对象/使用模型/可靠性等级/是否 abstain)。**核心是静态预期,非实际路由(红线 3),UI 必须明确标注**。数据:`/api/modules`(`getModules`)+ `/api/options` cell preset 的 `modules[]`(`getOptions`)。

**props/数据源:** `{request; onNext; onBack}`;`getModules()` + `getOptions()`,按 `request.species`(+cell_type)匹配 preset 取 `modules[]` 作预期集(迁 `ModuleContextView` 匹配逻辑)。
- [ ] **Step 1:** 顶部醒目"预期,非实际"横幅(继承现红字注意:静态预期由 cell preset 声明,真实路由在结果页 Module Routing tab)。
- [ ] **Step 2:** 模块目录卡片网格,预期模块归 primary/secondary 高亮、其余 "not activated";卡片显 code/display_name/engines(现有)+ 触发原因(preset 声明)。前端派生一个轻量 `modulePlan`(静态预期)写入 `JobState.modulePlan` 以满足 route→run 的 `canEnter`。
- [ ] **Step 3:** 降级:`getModules` 失败→空目录提示;无匹配 preset→无高亮但不阻塞(现有语义)。
- [ ] **Step 4:** build + typecheck + lint 全过。**手动验证:** "预期非实际"标注醒目;human/K562 等有 preset 的物种高亮预期模块;无 preset 物种不阻塞可前进 run。

**验收:** 静态预期分组 + 醒目标注;不重算真实路由;可前进 run。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): RouteStage 模块路由预览(静态预期分组,醒目标注非实际,复用 /api/modules)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```
> 🔴 红线 3:运行前不重算真实路由;只静态预期;明确标注"预期,非实际"。

## Task 9.11: RunStage(execution manifest + 确定性进度指示)

**Files:**
- Create: `praxis_vc_react/src/components/stages/RunStage.tsx`
- Modify: `praxis_vc_react/src/components/layout/Workspace.tsx`(接 RunStage)

**职责:** spec §2 Stage4——execution manifest 风格(Question / Modules / Models 可用性 / Safety·reliability 检查)+ `Start run` 按钮。数据:POST `/api/jobs`(`createJob`,**同步返回**)。运行中"live trace"是**确定性步骤清单指示**(Validating → Resolving species → Routing modules → Running predictors → Governance checks → Assembling report → Saving provenance),非真流式(红线 4)。

**props/数据源:** `{request; mode; onRan:(jobId)=>void; onBack; setRunStatus}`;`createJob(request, mode, enableLlmReport)`。
- [ ] **Step 1:** manifest 汇总(迁 `RunConfirmView`:species/cell_type/perturbation/targets/task_type 只读表 + 完整 request JSON details + LLM 报告开关)+ 静态预期模块列表(来自 `JobState.modulePlan`)。
- [ ] **Step 2:** `Start run`:`setRunStatus("running")` → 展示确定性步骤指示(固定文案序列 + 逐步点亮的伪进度,**注释标明非真流式**)→ await `createJob` → 成功 `onRan(job_id)` + `setRunStatus("succeeded")` 前进 results(实际 status 由结果页 `abstain`/`reliability` 决定,可回填 `abstained`/`failed`);失败 `setRunStatus("failed")` 显错。
- [ ] **Step 3:** build + typecheck + lint 全过。**手动验证:** 点 Start run 后步骤指示走完、拿到 job_id 进 results;失败态回显;"非真流式"在代码注释与 UI 副文案清楚。

**验收:** manifest 齐;同步执行;进度指示明确标注非流式;job 落地。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): RunStage execution manifest + 确定性步骤指示(同步 /api/jobs,非流式)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```
> 🔴 红线 4:后端同步执行;"live trace"是确定性步骤指示非真流式;真 32 步 trace 在 Stage5 Trace tab。

## Task 9.12: ResultsStage 骨架(6 tab 容器,接旧 ResultView 逻辑过渡)+ 清理旧 views

**Files:**
- Create: `praxis_vc_react/src/components/stages/ResultsStage.tsx`
- Modify: `praxis_vc_react/src/components/layout/Workspace.tsx`(接 ResultsStage;历史 job 也走它)
- Delete: `praxis_vc_react/src/views/{AskView,ParseReviewView,ConfirmView,ModuleContextView,RunConfirmView,Sidebar}.tsx`(已被新组件取代)
- Keep(暂):`praxis_vc_react/src/views/ResultView.tsx`(P5 拆完 6 tab 后删)

**职责:** Results 阶段外壳——顶部 job 头 + 下载/copy 工具条 + `Tabs`(Report/Predictions/Module Routing/Evidence/Trace/Provenance 6 tab)。数据:并发 `getReport`/`getTrace`/`getProvenance`/`getModulePlan`(迁 `ResultView` 的并发拉取 + 降级)。此 task tab 内容先接现有 ResultView 的 Report/Trace/Provenance 渲染(占位),Predictions/Evidence/Module Routing 先 `EmptyState` 占位,P5 逐个实现。

**props/数据源:** `{jobId; onReset}`;并发四端点,`useState` 装载,失败降级。
- [ ] **Step 1:** 外壳 + 6 tab `Tabs`(受控)+ 工具条(download report.json / narrative.md / report.md;copy report;copy provenance summary——迁 `ResultView` download 逻辑,copy 用 `navigator.clipboard`)。
- [ ] **Step 2:** 数据并发拉取 + `Skeleton`/`EmptyState` 降级(迁 `ResultView` `useEffect`)。
- [ ] **Step 3:** Report/Trace/Provenance tab 暂用现 ResultView 内联渲染逻辑(临时 import 或复制进新组件);Predictions/Evidence/Module Routing tab 用 `EmptyState`("P5 实现")。
- [ ] **Step 4:** 删除已被取代的旧 views(上面 Delete 列表);确认无残留 import。
- [ ] **Step 5:** build + typecheck + lint 全过。**手动验证:** 6 tab 都在、可切;Report/Trace/Provenance 有内容;3 个占位 tab 显 EmptyState;下载/copy 可用;历史 job 进 results 正常。

**验收:** 6 tab 容器就位;下载/copy 工具条齐;旧 6 views 删除;流程不断。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): ResultsStage 6 tab 容器 + 下载/copy 工具条,删除旧 5 stage views

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

# P4 · 可视化组件(5 task)

> 目标:可视化增强解释而非堆装饰(spec §4 第一批 6 个)。建 `components/visualization/*`,供 P5 各 tab 消费。Recharts 用于标准统计图;模块路由/trace 用手写 SVG。

## Task 9.13: PredictionBarChart + ReliabilityMeter(Recharts)

**Files:**
- Create: `praxis_vc_react/src/components/visualization/PredictionBarChart.tsx`
- Create: `praxis_vc_react/src/components/visualization/ReliabilityMeter.tsx`

**职责:** spec §4 ①②③——Δgene top changes bar / module response score bar / reliability score strip。数据:`structured_report.prediction`(Δ 表)、module response、`learned_reliability.reliability_score`。**offline 为 mock 数值,如实展示,不推断真值。**

**props:** `PredictionBarChart {data: {label:string; value:number}[]; title; kind:"delta"|"module"}`(纯展示,数据由 tab 从 `structured_report` 提取传入);`ReliabilityMeter {score:number|null; mode?:string; reliability?:string}`。
- [ ] **Step 1:** `PredictionBarChart` 用 recharts `BarChart`/`Bar`/`XAxis`/`YAxis`/`Tooltip`/`ResponsiveContainer`,配色走 token(深靛蓝正/翠绿点缀,负值 danger);空数据→`EmptyState`。
- [ ] **Step 2:** `ReliabilityMeter` 横条 strip(0–1),阈值分段着色(高=翠绿,低=amber/red),显 mode/reliability 文案;`score==null`→"未提供"。
- [ ] **Step 3:** build + typecheck + lint 全过(注意 recharts 类型 + ResponsiveContainer 需容器有高度)。**手动验证:** 临时喂 mock 数据渲染出 bar 与 strip,配色对、空数据降级、无控制台 warning。

**验收:** 两组件用 Recharts + token;空数据降级;类型完整。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): PredictionBarChart + ReliabilityMeter 可视化(Recharts,token 配色,空数据降级)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

## Task 9.14: EvidenceDistributionChart(Recharts,disagreement/uncertainty)

**Files:**
- Create: `praxis_vc_react/src/components/visualization/EvidenceDistributionChart.tsx`

**职责:** spec §4 ③补 / §2 Predictions③——model disagreement / uncertainty 展示。数据:`structured_report.model_disagreement`(score/metric/triggered)+ `models_used/rejected/failed` 计数。

**props:** `{disagreement: {score?; metric?; triggered?}; models: {used:string[]; rejected:string[]; failed:string[]}}`。
- [ ] **Step 1:** 用 recharts 展示 disagreement score(单值 gauge 式 bar 或小 radial)+ models 计数分布(used/rejected/failed 三段 bar);triggered 时高亮 warn。
- [ ] **Step 2:** 全空→`EmptyState`;数值缺失容错(`??`)。
- [ ] **Step 3:** build + typecheck + lint 全过。**手动验证:** mock 数据渲染;triggered=true 时 warn 着色;空态降级。

**验收:** disagreement/uncertainty 图就位;容错。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): EvidenceDistributionChart(model disagreement/uncertainty,Recharts)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

## Task 9.15: ModuleRoutingGraph(手写 SVG 模块网络图)

**Files:**
- Create: `praxis_vc_react/src/components/visualization/ModuleRoutingGraph.tsx`

**职责:** spec §4 ④——手写 SVG 模块关系图:primary/secondary/handoff/verdict/abstain/confidence。数据:`ModulePlan`(`/module-plan`,`primary`/`secondary`/`entries[]{module,role,verdict,mismatch,caution_flags,...}`)。

**props:** `{plan: ModulePlan | null}`(空/`{}`→`EmptyState`"未产生模块路由")。
- [ ] **Step 1:** 手写 `<svg>`:primary 居中大节点(深靛蓝),secondary 环绕,handoff 用连线;节点着色按 verdict(ok=翠绿/caution=amber/mismatch=red);abstain 特殊标记;confidence 以节点大小或标签。布局用简单确定性算法(primary 中心 + secondary 均匀环形排布),不引 force graph(spec §4 明确不上花哨 force)。
- [ ] **Step 2:** `viewBox` 响应式;文字用 token 字体;`overflow-x:auto` 容器防横溢。
- [ ] **Step 3:** build + typecheck + lint 全过。**手动验证:** mock ModulePlan(1 primary + 2 secondary)渲染出中心-环形图,verdict 着色对,空 plan 降级。

**验收:** 手写 SVG 网络图;verdict/abstain/confidence 可读;空态降级。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): ModuleRoutingGraph 手写 SVG 模块网络图(primary/secondary/handoff/verdict/abstain)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

## Task 9.16: AgentTraceTimeline(手写 SVG trace 泳道/时间线)

**Files:**
- Create: `praxis_vc_react/src/components/visualization/AgentTraceTimeline.tsx`

**职责:** spec §4 ⑤ / §2 Trace——时间线/泳道图,默认 6–8 关键节点,可展开完整 32 步。数据:`/trace`(`trace[]{timestamp,sender,receiver,message_type}`)。

**props:** `{trace: TraceStep[]; }`(内部 `useState` 控制 collapsed/expanded)。
- [ ] **Step 1:** 手写 SVG/HTML 混合:sender→receiver 泳道 + 节点按 timestamp 排;默认取首尾+关键 message_type 的 6–8 节点,"展开完整 32 步"按钮显全部。
- [ ] **Step 2:** 节点 hover/点显 message_type/时间;着色走 token;空 trace→`EmptyState`。
- [ ] **Step 3:** build + typecheck + lint 全过。**手动验证:** mock 32 步 trace 默认显 6–8 节点、展开显全部、时间顺序对、空态降级。

**验收:** trace 时间线可折叠展开;默认精简;空态降级。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): AgentTraceTimeline 手写 SVG trace 时间线(默认 6-8 节点,可展开 32 步)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

## Task 9.17: 可视化组件 barrel + 空态/降级统一自检

**Files:**
- Create: `praxis_vc_react/src/components/visualization/index.ts`(barrel export)
- Modify(如需): 各 visualization 组件统一空态用 `ui/EmptyState`、加载用 `ui/Skeleton`

**职责:** 统一导出 5 个可视化组件 + 复核每个组件的空数据/加载/异常降级一致(offline mock、null、`{}`、空数组四种输入都不崩)。

- [ ] **Step 1:** barrel `export`。
- [ ] **Step 2:** 逐组件核对四类空输入降级;补齐缺失的 `EmptyState`。
- [ ] **Step 3:** build + typecheck + lint 全过。**手动验证:** 逐组件喂 null/`{}`/`[]`/mock 四输入不崩。

**验收:** barrel 就位;5 组件空态统一;无崩溃路径。
**commit:**
```
git commit -m "$(cat <<'EOF'
chore(phase9): visualization barrel + 空态/降级统一自检(null/{}/[]/mock 不崩)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

# P5 · 结果页证据化(6 task)

> 目标:6 tab 各自证据化,结果不是一段 AI 文本,可写进论文/demo。逐个把 P4 可视化 + 真实数据源接进 ResultsStage 的 6 个 tab。全接完删旧 `ResultView.tsx`。

## Task 9.18: ReportTab(自然语言报告分块)

**Files:**
- Create: `praxis_vc_react/src/components/result/ReportTab.tsx`
- Modify: `praxis_vc_react/src/components/stages/ResultsStage.tsx`(接 ReportTab)

**职责:** spec §2 Report——conclusion / predicted changes / affected modules / reliability / limitations / next experiment。数据:`structured_report`(summary/prediction/reliability/boundary 五块,迁现 `ResultView` 的 ReportTab)+ `narrative_report` + `getReportMarkdown()`。

**props:** `{report: ReportResult; markdown?: string}`。
- [ ] **Step 1:** 迁现 ReportTab 5 块(Summary/Prediction/Reliability decision/Boundary/Narrative)+ `llm_used_for_prediction` 徽标 + "LLM 未参与预测/治理决策"提示;用新 `Card`/`Badge`/`StatusPill` 重排为证据化布局。
- [ ] **Step 2:** abstain 时突出显示 abstain_reasons;narrative 缺失降级文案。
- [ ] **Step 3:** build + typecheck + lint 全过。**手动验证:** 有 job 时 5 块齐、abstain 态突出、无 narrative 降级。

**验收:** Report 分块证据化;LLM 边界提示保留。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): ReportTab 自然语言报告分块证据化(迁 ResultView,LLM 边界提示保留)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```
> 🔴 红线:只读展示,`llm_used_for_prediction` 如实显示。

## Task 9.19: PredictionsTab(Recharts 三图)

**Files:**
- Create: `praxis_vc_react/src/components/result/PredictionsTab.tsx`
- Modify: `praxis_vc_react/src/components/stages/ResultsStage.tsx`(接)

**职责:** spec §2 Predictions——① Δgene top changes ② module response score ③ disagreement/uncertainty。数据:`structured_report.prediction`/`.model_disagreement`/`.learned_reliability`。用 P4 的 `PredictionBarChart`/`ReliabilityMeter`/`EvidenceDistributionChart`。

**props:** `{report: ReportResult}`。
- [ ] **Step 1:** 从 `structured_report` 提取:Δgene top changes(prediction 里的基因-Δ 列表,取 top N)、module response score、reliability_score、disagreement。做数据整形函数(容错 `??`/类型守卫,offline mock 如实)。
- [ ] **Step 2:** 组合三图 + `ReliabilityMeter`;abstain/无 prediction→`EmptyState`("已 abstain,无预测")。
- [ ] **Step 3:** build + typecheck + lint 全过。**手动验证:** 有预测 job 三图渲染;abstain job 降级;数值与 Report tab 一致。

**验收:** 三 Recharts 图 + reliability meter;abstain 降级;数值一致。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): PredictionsTab(Δgene/module/disagreement 三图 + reliability meter,Recharts)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```
> 🔴 红线:offline mock 如实展示,前端不推断真值。

## Task 9.20: ModuleRoutingTab(手写 SVG + entries 表,真实路由)

**Files:**
- Create: `praxis_vc_react/src/components/result/ModuleRoutingTab.tsx`
- Modify: `praxis_vc_react/src/components/stages/ResultsStage.tsx`(接)

**职责:** spec §2 Module Routing——**真实路由结果**(与 Stage3 静态预期区分)。数据:`getModulePlan()`(`/module-plan`)。用 P4 `ModuleRoutingGraph` + 降级 entries 表(迁现 `ResultView` 的 `ModuleRoutingBlock`)。

**props:** `{plan: ModulePlan | Record<string,never> | null}`。
- [ ] **Step 1:** 顶部标注"实际路由(run 产物)"以区别 Stage3 预期;`ModuleRoutingGraph` 图 + primary/secondary/overall_verdict 摘要 + entries 表(module/role/verdict/mismatch,迁现有)。
- [ ] **Step 2:** 空 `{}`/null 降级(加载中 Skeleton / 不可路由 EmptyState,迁现有语义)。
- [ ] **Step 3:** build + typecheck + lint 全过。**手动验证:** 可路由 job 显图+表;不可路由 job 降级;标注"实际"清楚。

**验收:** 真实路由图+表;与 Stage3 预期语义区分;降级完整。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): ModuleRoutingTab 真实路由(手写 SVG 图 + entries 表,/module-plan,标注实际)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```
> 🔴 红线 3:此 tab 是 run 后真实路由;明确区别于 Stage3 静态预期。

## Task 9.21: EvidenceTab(证据表)

**Files:**
- Create: `praxis_vc_react/src/components/result/EvidenceTab.tsx`
- Modify: `praxis_vc_react/src/components/stages/ResultsStage.tsx`(接)

**职责:** spec §2 Evidence——object validation / model source / retrieved memory / prior case / negative case warning / rule applied。数据:`structured_report.provenance`(`rules_referenced`/`rules_hit`/`evidence_level`)+ boundary(`failed_checks`/`critic_violations`/`caution_flags`)+ `models_used/rejected/failed`。

**props:** `{report: ReportResult}`。
- [ ] **Step 1:** 证据表(HTML table):rules_referenced/rules_hit、model source(used/rejected/failed)、failed_checks、critic_violations、caution_flags、evidence_level;negative/warning 用 `Badge` warn/danger 着色。可选嵌 `EvidenceDistributionChart`。
- [ ] **Step 2:** 字段缺失容错;全空→`EmptyState`。
- [ ] **Step 3:** build + typecheck + lint 全过。**手动验证:** 有 governance 字段的 job 表齐、着色对;缺失容错。

**验收:** 证据表全字段;着色语义对;容错。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): EvidenceTab 证据表(rules/model source/checks/violations,warn/danger 着色)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

## Task 9.22: TraceTab(手写 SVG 时间线)

**Files:**
- Create: `praxis_vc_react/src/components/result/TraceTab.tsx`
- Modify: `praxis_vc_react/src/components/stages/ResultsStage.tsx`(接)

**职责:** spec §2 Trace——用 P4 `AgentTraceTimeline`(默认 6–8 关键节点,可展开 32 步)。数据:`getTrace()`(`/trace`)。

**props:** `{trace: TraceResult | null}`。
- [ ] **Step 1:** 包 `AgentTraceTimeline`,传 `trace.trace`;加"步数"摘要;空/加载降级。
- [ ] **Step 2:** build + typecheck + lint 全过。**手动验证:** trace 时间线默认精简、可展开、空态降级。

**验收:** trace tab 用 SVG 时间线;折叠/展开;降级。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): TraceTab(AgentTraceTimeline 时间线,/trace,默认精简可展开)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

## Task 9.23: ProvenanceTab(审计页 + 下载 JSON)+ 删除旧 ResultView

**Files:**
- Create: `praxis_vc_react/src/components/result/ProvenanceTab.tsx`
- Modify: `praxis_vc_react/src/components/stages/ResultsStage.tsx`(接;确认 6 tab 全实现)
- Delete: `praxis_vc_react/src/views/ResultView.tsx`(逻辑全迁完)
- Delete(如空): `praxis_vc_react/src/App.css`、`praxis_vc_react/src/index.css`(样式已迁 styles/,确认无引用后删)

**职责:** spec §2 Provenance——审计页:job ID / timestamp / input / parsed schema / model versions / module versions / data sources / abstain rules / report hash / 可下载 JSON。数据:`getProvenance()`(`/provenance`,`provenance`+`llm_meta`)+ job metadata。

**props:** `{prov: ProvenanceResult | null; jobId: string}`。
- [ ] **Step 1:** 审计字段分区展示(而非现在的裸 `pre` JSON):job ID/timestamp/input/schema/model&module versions/data sources/abstain rules/report hash;末尾保留完整 JSON `pre`(`--font-mono`)+ "下载 provenance JSON" 按钮 + "copy provenance summary"。
- [ ] **Step 2:** 删除旧 `ResultView.tsx`;grep 确认无残留 import(`views/ResultView`);若 `App.css`/`index.css` 已无任何引用则删,`main.tsx` 只留 `styles/index.css`。
- [ ] **Step 3:** build + typecheck + lint 全过。**手动验证:** provenance 审计分区可读、下载 JSON 生成文件、copy 可用;`views/` 目录已空或不存在;无死 import;全站样式正常(旧 css 删除后无回归)。

**验收:** provenance 审计化 + 下载/copy;旧 ResultView/css 清理;6 tab 全部真实实现。
**commit:**
```
git commit -m "$(cat <<'EOF'
feat(phase9): ProvenanceTab 审计页 + 下载/copy,删除旧 ResultView/index.css/App.css(6 tab 全实现)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

# P6 · 浏览器冒烟(2 task)

> 目标:build+typecheck+lint+playwright 10 点冒烟(spec §9)全绿。playwright 由**控制器统一跑**(前端不入测试栈,不写 spec 文件进仓库)。

## Task 9.24: 全量静态门 + Self-Review 扫描

**Files:**（无源码新增,可能小修）
- Modify(如发现): 任何 build/typecheck/lint 报错或 placeholder 残留的文件

**职责:** 收口三门 + Self-Review。

- [ ] **Step 1:** `cd praxis_vc_react && npm run build && npm run typecheck && npm run lint` 三门全绿(贴输出)。
- [ ] **Step 2:** placeholder 扫描:`grep -rn "TODO\|FIXME\|EmptyState(\"P5" src/`(确认无"P5 实现"等临时占位残留)、`grep -rn "views/" src/`(确认无死 import)。
- [ ] **Step 3:** spec 覆盖自查(对 spec §5 目录树逐项核对文件存在;6 tab / 6 可视化 / 5 stage / 状态机 §6 / 红线 §11 逐条)。
- [ ] **Step 4:** 类型一致自查:`api.ts` 未新增请求方法(`git diff` 确认只加类型);无 `any` 滥用。
- [ ] **Step 5:** commit(若有小修;无修则跳过 commit)。

**验收:** 三门绿;无占位/死 import;spec 覆盖齐;api.ts 只加类型。
**commit(若有修改):**
```
git commit -m "$(cat <<'EOF'
chore(phase9): 全量静态门收口 + Self-Review 扫描(placeholder/死 import/spec 覆盖/类型一致)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

## Task 9.25: 控制器 playwright 10 点冒烟(阶段末统一)

**Files:**（不入仓库——控制器临时脚本/交互,前端不引入测试栈）

**职责:** 控制器用 playwright 走 spec §9 的 10 点冒烟(**不写测试文件进仓库**,不改前端依赖):
- [ ] ① 首页(hero 非聊天窗观感)
- [ ] ② 输入问题 → Parse
- [ ] ③ parse → review(分组表单 + 字段状态)
- [ ] ④ 改一字段(状态点更新)
- [ ] ⑤ 进 route(静态预期 + "非实际"标注)
- [ ] ⑥ 进 run(manifest + Start run,确定性进度指示)
- [ ] ⑦ 完成 result(6 tab 出现)
- [ ] ⑧ 切 Report / Predictions / Module Routing / Evidence / Trace / Provenance tab 各有内容
- [ ] ⑨ 切 light/dark 主题
- [ ] ⑩ 回历史 job(侧栏点击进 results)

**做法:** 控制器 `cd praxis_vc_react && npm run build && npm run preview`(或 dev + 后端 proxy),playwright 连 preview URL 逐点验证;失败则回对应 task 修。**本 task 不产生 commit**(除非冒烟暴露 bug 需回改,回改按对应 task 模板 commit)。

**验收:** 10 点冒烟全绿;build+typecheck+lint 三门绿(spec §9 全部满足)。

---

## Self-Review(spec 覆盖 / placeholder 扫描 / 类型一致)

**spec 覆盖核对(逐条):**
- §1 信息架构 7→5:✅ P2 状态机映射表(旧 7 Step → 5 Stage,parse_review+confirm→review,result+advanced→results)。
- §1 三栏布局(独立 Sidebar / 工作区内 StepperRail / 窄屏降级):✅ Task 9.6/9.7。
- §2 五阶段要点:✅ Ask(9.8 hero+3 示例+Advanced)/ Review(9.9 分组+字段状态)/ Route(9.10 静态预期+标注)/ Run(9.11 manifest+确定性进度)/ Results(9.12+P5 六 tab)。
- §2 6 tab 数据源:✅ 本计划"6 tab 数据源映射"表 + Task 9.18–9.23 逐 tab 真实端点。
- §3 视觉系统(色/字/卡片,light/dark):✅ Task 9.2/9.3(色值逐一对齐 spec §3;Newsreader 仅标题;深靛蓝按钮不用黑;翠绿仅状态色)。
- §4 可视化(Recharts 标准图 + 手写 SVG 模块/trace;第一批 6 个;不上 visx/花哨):✅ P4 五组件覆盖 6 图(PredictionBarChart 承 ①②、ReliabilityMeter 承 ③ strip、EvidenceDistributionChart 承 disagreement、ModuleRoutingGraph ④、AgentTraceTimeline ⑤;ProvenanceCard 由 ProvenanceTab 承 ⑥)。
- §5 组件目录树:✅ 本计划"目标文件结构"逐项映射到 task。
- §6 状态机(`Stage`/`JobState`/stepper 回退禁用规则):✅ Task 9.5 + "状态机映射"节。
- §11 红线:✅ 顶部红线节 + 相关 task(9.1 仅前端依赖 / 9.8 后端解析 / 9.10 静态预期标注 / 9.11 同步非流式 / 9.18/9.19 只读只展示)。

**placeholder 扫描:** Task 9.24 Step 2 grep TODO/FIXME/临时 EmptyState/死 import;各 P3/P5 task 均"接完即删旧 views"避免双源。

**类型一致:** `api.ts` 全程只加 UI 派生类型(`Stage`/`RunStatus`/`JobState`),**不新增/改请求方法**(Task 9.5 Step 1 + 9.24 Step 4 `git diff` 校验);复用现有 `ParseResult`/`ModulePlan`/`ReportResult`/`TraceResult`/`ProvenanceResult`/`Options`/`ModuleInfo` 类型。

**风险/BLOCKED 标记:** Task 9.1 `npm install` 需网络——**离线则 9.1 BLOCKED,阻塞全 Phase**(recharts/字体是地基),须联网后再启动。

**红线终检:** 全程不碰 `praxis_virtualcell/` Python、不碰 `praxis_vc_api/`、不碰根 `tests/`、不碰后端 CI;`api.ts` 端点零改动;不 push。
