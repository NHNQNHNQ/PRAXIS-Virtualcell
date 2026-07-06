# PRAXIS-VirtualCell 前端重设计 —— 科研任务控制台(设计定稿 spec)

> 来源:2026-07-06 用户 approve 的完整设计计划(brainstorm 定稿)。本文件是项目内权威设计文档 + 工程落地映射,供 writing-plans 展开实施计划。
> 定位一句话:**让人感觉这不是聊天机器人,而是一个能把自然语言科学问题转化为可审计虚拟细胞实验的科研工作台。**

## 0. 定位与目标

从"问答向导"升级为**面向科学家的实验任务控制台**。关键词不是 chat/assistant/AI demo,而是 Scientific workflow / Agent routing / Predictive model orchestration / Provenance / Reproducibility。

不是:ChatGPT clone / AI dashboard / 炫酷生物科技官网 / 普通后台管理系统。
而是:Nature-style scientific software / bench scientist workflow console / evidence-first research interface。

**性质**:纯前端重构 —— 信息架构升级 + 视觉系统重写 + 结果页证据化增强。**后端零改动**。非科学核心(前端只读展示,不碰预测/治理决策)。

## 1. 信息架构:7 步 → 5 阶段

| 阶段 | 名称 | 目的 | 对应旧步骤 |
|---|---|---|---|
| 1 | Ask | 输入自然语言科学问题 | ask |
| 2 | Review | 解析结果核对与编辑 | parse_review + confirm |
| 3 | Route | 模块路由与模型**预览** | module_context |
| 4 | Run | 运行确认与执行状态 | run_confirm |
| 5 | Results | 报告/证据/trace/provenance | result + advanced |

**布局**(三栏逻辑,视觉简洁):
- **左侧 Job Sidebar 独立保留**:历史 job / 最近运行 / 收藏。**不与步骤轨混。**
- **Stepper Rail 放在主工作区内部左侧**:表示当前任务的 5 阶段进度;已完成阶段可点回退。
- 窄屏降级:Top Bar → Current Job Header → 水平 Stepper → Stage Content。

## 2. 五阶段设计要点

- **Stage 1 Ask**:科研感 hero 输入(非 ChatGPT 聊天窗);3 个示例(gene perturbation / drug response / metabolic stress);可选 "Advanced input" 折叠区(上传结构化 JSON / 选物种)。
- **Stage 2 Review**(最重要):解析摘要 + 可编辑表单。字段分组(Biological system / Perturbation / Requested outputs / Assumptions),每字段带状态:`confirmed`(深靛勾选)/ `inferred`(amber 标签)/ `missing`(红橙提示)/ `editable`(pencil)/ `locked`(lock)。让科学家感觉系统**运行前让人审阅任务定义**,而非直接乱跑。
- **Stage 3 Route**("Module Routing Preview"):展示系统准备如何调度模块 —— primary / secondary / not activated 分组 + handoff 关系。每模块卡片:名称/触发原因/输入对象/使用模型(公开·本地·自训)/可靠性等级/是否 abstain。核心是让用户知道"为什么调这些模块"。
  - ⚠️ **落地约束(延续 Phase 8 红线)**:module_plan 是 run 产物,运行前不能真重算路由。**Stage 3 展示的是"静态预期路由"**(基于 species + cell preset 的 `modules` 元数据 + `/api/modules` 目录),必须明确标注"预期,非实际"。**真实路由结果在 Stage 5 的 Module Routing tab**(run 后 `/api/reports/{id}/module-plan`)。
- **Stage 4 Run**:execution manifest 风格 —— Question / Modules / Models(可用性)/ Safety·reliability 检查。按钮 `Start run`。
  - ⚠️ **落地约束**:后端 `/api/jobs` 是**同步执行**(run_job 同步返回,非流式)。所以"运行中 live trace"**是确定性步骤清单指示**(1 Validating → 2 Resolving species → … → 7 Saving provenance),不是真流式;真实 32 步 trace 在 Stage 5 Trace tab。
- **Stage 5 Results**:**6 个证据 tab**(不再合并成"高级区域"):
  - `Report` —— 自然语言报告(conclusion / predicted changes / affected modules / reliability / limitations / next experiment)。数据:structured_report + report.md(`/markdown`)+ narrative。
  - `Predictions` —— Recharts 标准图:① Δ gene expression top changes ② pathway/module response score ③ model disagreement / uncertainty。数据:structured_report.prediction / model_disagreement / reliability。(offline 为 mock 数值,真值在 .53;前端如实展示 structured_report。)
  - `Module Routing` —— 手写 SVG 关系图:primary/secondary/handoff/verdict/abstain/confidence。数据:`/module-plan`。
  - `Evidence` —— 证据表:object validation / model source / retrieved memory / prior case / negative case warning / rule applied。数据:provenance(rules_referenced/rules_hit/evidence_level)+ governance 字段。
  - `Trace` —— 时间线/泳道图:默认 6–8 个关键节点,可展开完整 32 步。数据:`/trace`。
  - `Provenance` —— 审计页:job ID / timestamp / input / parsed schema / model versions / module versions / data sources / abstain rules / report hash / 可下载 JSON。数据:`/provenance` + job metadata。
  - 支持:下载 JSON、copy report、copy provenance summary。

## 3. 视觉设计系统(重写样式)

**配色**(暖白 + 深靛蓝 + 少量翠绿;克制,不像杂志封面):
| 用途 | 颜色 |
|---|---|
| 页面背景 | `#FDFDFC` |
| 主面板 | `#FFFFFF` |
| 主文字 | `#1A1A2E` |
| 次级文字 | `#5F6572` |
| 主色(按钮/主结构) | `#1E3A5F` 深靛蓝 |
| 强调色(success/biology/active) | `#2F8F83` 翠绿(**仅状态色,不作主色/大面积**) |
| 警告 | `#B7791F` |
| 危险 | `#B42318` |
| 边框 | `#E6E3DC` |
| 代码背景 | `#F6F4EF` |
按钮用深靛蓝(**不用黑按钮**)。保留 light/dark 双主题。

**字体**(self-host 打包进 dist,离线可用):
| 区域 | 字体 |
|---|---|
| Hero / 页面大标题 | **Newsreader**(Nature/Cell 风编辑衬线;**不用 Fraunces**,个性过强) |
| 正文/表单/按钮 | **Inter** |
| JSON/trace/schema | **JetBrains Mono** 或 IBM Plex Mono |
衬线**只用于大标题**,不用于表单/结果正文。

**卡片**(不重边框、不大阴影;层次靠间距/字重/小标题/细分隔/标签/状态点,不靠大色块):
```css
background: #ffffff; border: 1px solid #e8e4dc;
border-radius: 16px; box-shadow: 0 1px 2px rgba(20,20,20,0.04);
```

## 4. 数据可视化方案

- **标准统计图 → Recharts**(React 友好、SVG 输出、写常规图快、工程复杂度低于 visx)。
- **模块网络图 → 手写 SVG**(图表库不擅长网络图)。
- **Trace/Provenance → 手写 SVG + HTML timeline**。
- **复杂交互图 → 以后再考虑 visx**(本期不上)。

**第一批只做 6 个**:① Module response bar chart ② Top predicted changes ③ Reliability score strip ④ Module routing graph ⑤ Agent trace timeline ⑥ Provenance summary card。
**暂不做**:复杂 Sankey / 3D 细胞图 / 粒子动画 / 过度 dashboard / 花哨 force graph(会分散严肃性)。

## 5. 组件拆分(目标结构)

```text
src/
  components/
    layout/    AppShell.tsx  TopBar.tsx  JobSidebar.tsx  Workspace.tsx  StepperRail.tsx
    stages/    AskStage.tsx  ReviewStage.tsx  RouteStage.tsx  RunStage.tsx  ResultsStage.tsx
    result/    ReportTab.tsx  PredictionsTab.tsx  ModuleRoutingTab.tsx  EvidenceTab.tsx  TraceTab.tsx  ProvenanceTab.tsx
    visualization/  ModuleRoutingGraph.tsx  AgentTraceTimeline.tsx  ReliabilityMeter.tsx  PredictionBarChart.tsx  EvidenceDistributionChart.tsx
    ui/        Button.tsx  Card.tsx  Badge.tsx  FieldRow.tsx  StatusPill.tsx  Tabs.tsx  EmptyState.tsx  Skeleton.tsx
  styles/      tokens.css  base.css  components.css  themes.css
```

## 6. 状态机设计

```ts
type Stage = "ask" | "review" | "route" | "run" | "results";

type JobState = {
  query: string;
  parsedIntent: ParsedIntent | null;
  modulePlan: ModulePlan | null;          // Stage 3 静态预期 + Stage 5 实际
  runStatus: "idle" | "running" | "succeeded" | "failed" | "abstained";
  result: ResultPayload | null;
  trace: TraceEvent[];
  provenance: ProvenancePayload | null;
};
```
stepper 规则:ask→review(parse 成功)/ review→route(required fields complete)/ route→run(module plan available)/ run→results(succeeded|failed|abstained);已完成阶段可点回退;不允许跳过 review;重新运行从 run 或 results 发起;回退不丢数据。

## 7. 落地映射(对着现有真实代码 —— writing-plans 展开时的地基)

**现有前端**(`praxis_vc_react/src/`):`App.tsx`(7 步 useState 状态机)+ `views/{AskView,ParseReviewView,ConfirmView,ModuleContextView,RunConfirmView,ResultView,Sidebar}.tsx` + `api.ts` + `index.css`/`App.css`。React 19 + Vite 8 + TypeScript + oxlint,**无测试栈**。

**映射**:
- `App.tsx` 7 步 → 重构为 `components/layout/AppShell` + 5 阶段 `Stage` 状态机(见 §6)。
- `views/*` → 拆/重写为 `components/{layout,stages,result,visualization,ui}/*`(§5)。
- `api.ts` → **基本不变**(数据源已够,见下);仅按需补类型。端点全部复用 Phase 8 已有:`/api/parse` `/api/options` `/api/modules` `/api/jobs` `/api/reports/{id}` `/trace` `/provenance` `/module-plan` `/markdown`。
- `index.css`/`App.css` → 拆为 `styles/{tokens,base,components,themes}.css`。
- `package.json` → 加依赖 `recharts` + self-host 字体(Newsreader/Inter/JetBrains Mono 打包);加 scripts:`typecheck`(`tsc -b --noEmit`);`smoke` 由控制器用 playwright 走 5 阶段(可留控制器手动,不强制入 npm)。

**后端零改动确认**:5 阶段 / 6 tab 所需数据后端全有(Phase 8 建的端点)。两个约束已在 §2 标注(Route 静态预期 / Run 同步)。**不碰 Python、不碰根 tests/、不碰科学决策。**

## 8. 实施 Phase(用户 6 工程 Phase → autopilot task 组)

| 工程 Phase | 目标 | 验收 |
|---|---|---|
| P1 设计 token + 基础布局 | 页面气质变对 | 不再像 ChatGPT;light/dark 可用;build 通过 |
| P2 5 阶段状态机 | 7→5 流程改造 | Ask→…→Results 走通;回退不丢数据;后端零改 |
| P3 重写 5 个 Stage 页 | 表单向导→科研控制台 | 每阶段科研目的明确 |
| P4 可视化组件 | 增强解释非堆装饰 | Route/Results/Trace/Provenance 各图就位 |
| P5 结果页证据化 | 6 tab + 下载/copy | 结果不是一段 AI 文本,可写进论文/demo |
| P6 浏览器冒烟 | Playwright 5 阶段 | build+typecheck+lint+smoke 全绿 |

## 9. 验收

`npm run build` + `npm run typecheck`(新增)+ `npm run lint` 全过;控制器 playwright 走 10 点冒烟:①首页 ②输入问题 ③parse→review ④改一字段 ⑤进 route ⑥进 run ⑦完成 result ⑧切 Report/Trace/Provenance tab ⑨切明暗主题 ⑩回历史 job。

## 10. 三开放点决定(已定稿)

1. **图表库 = Recharts**(标准图);模块路由/trace = 手写 SVG;本期不上 visx。
2. **强调色 = 深靛蓝主 + 少量翠绿**(翠绿仅状态色,不作主色);warning=amber,danger=muted red。
3. **字体 = Newsreader(标题)+ Inter(界面)+ JetBrains Mono(trace/schema)**;不用 Fraunces。

## 11. 红线(延续 Phase 8,实施每一步守)

1. **后端零改动**、不碰 `praxis_virtualcell/` Python、不碰根 `tests/`。
2. **前端只读展示**,不做预测/治理判断;OFFLINE 全程 `llm_used=false`。
3. **Stage 3 Route 不在运行前重算真实路由**(只静态预期),真实路由在 Stage 5;不误导用户以为是实际路由(明确标注)。
4. **前端不引入测试栈**(延续用户决策),靠 build+typecheck+lint+playwright 冒烟。
5. 引入依赖仅前端(`recharts` + 字体),不影响 Python/后端/CI 的 `praxis_virtualcell` 口径。
