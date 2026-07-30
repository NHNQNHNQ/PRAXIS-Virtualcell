import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  health,
  listJobs,
  type Health,
  type JobState,
  type JobSummary,
  type Mode,
  type RunStatus,
  type Stage,
} from "../../api";
import DataLibrary from "../data/DataLibrary";
import PlatformPage from "../platform/PlatformPage";
import LazyResultsStage from "../stages/LazyResultsStage";
import JobSidebar, { type PlatformView } from "./JobSidebar";
import TopBar, { type Theme } from "./TopBar";
import Workspace from "./Workspace";

// Phase 9 Task 9.5/9.7 · 状态机宿主(spec §6)。
// 集中管理 5 阶段(Ask→Review→Route→Run→Results)+ 集中式 JobState,
// 迁移旧 App.tsx 的 loadJobs/health/newQuery/activeJobId。
// 布局层:JobSidebar(全局历史侧栏,9.6)/ TopBar(9.6)/ Workspace(工作区,9.7,内含左侧 StepperRail)。
// 9.7 起 Workspace/StepperRail 从本文件抽出为独立组件,本文件不再内联阶段渲染;
// review 阶段自 9.9 起由 ReviewStage 单页承载(旧 parse_review+confirm 双子步机制已移除);
// 其余阶段内容仍由 Workspace 桥接现有 views/*(P3 逐个替换成新 Stage 页)。
// 铁律:api.ts 只加类型不改请求;后端零改动。

// JobState 初值:各字段为空；回退保留 Ask/Review 草稿，确认后的下游状态按依赖失效。
const emptyJob: JobState = {
  query: "",
  askDraft: null,
  parsedMode: null,
  parsedIntent: null,
  reviewDraft: null,
  confirmedRequest: null,
  modulePlan: null,
  runStatus: "idle",
  jobId: null,
};

export default function AppShell() {
  const mainScrollRef = useRef<HTMLElement>(null);
  const [mode, setMode] = useState<Mode>("offline");
  const modeRef = useRef<Mode>(mode);
  const [stage, setStage] = useState<Stage>("ask");
  const [view, setView] = useState<PlatformView>("home");
  const [queryEpoch, setQueryEpoch] = useState(0);
  const queryEpochRef = useRef(0);
  // null 表示当前 Ask 尚未上报草稿；空字符串则是用户确实清空了输入。
  // 二者必须区分，否则迟到的旧解析会把空草稿重新推进到 Review。
  const askQueryRef = useRef<string | null>(null);
  const [job, setJob] = useState<JobState>(emptyJob);
  const [openedJobId, setOpenedJobId] = useState<string | null>(null); // 侧栏载入的历史 job
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [jobsErr, setJobsErr] = useState<string | null>(null);
  const [h, setH] = useState<Health | null>(null);
  const [healthErr, setHealthErr] = useState<string | null>(null);
  // 主题(light/dark):TopBar 切换,副作用写到 <html data-theme>,themes.css 据此覆盖 token。
  // 默认 light;不写 data-theme 时 themes.css 会跟随 prefers-color-scheme(系统偏好)。
  const [theme, setTheme] = useState<Theme>("light");

  modeRef.current = mode;

  const loadJobs = useCallback(() => {
    setJobs(null);
    setJobsErr(null);
    listJobs()
      .then((d) => setJobs(d.jobs))
      .catch((e: unknown) => setJobsErr(String(e)));
  }, []);

  useEffect(() => {
    health()
      .then(setH)
      .catch((e: unknown) => setHealthErr(String(e)));
    loadJobs();
  }, [loadJobs]);

  // 主题副作用:显式写 document.documentElement.dataset.theme,全站明暗切换。
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  // 新建查询:重置整个 JobState 回 ask,退出历史 job 模式。
  function newQuery() {
    const nextEpoch = queryEpochRef.current + 1;
    queryEpochRef.current = nextEpoch;
    setQueryEpoch(nextEpoch);
    askQueryRef.current = null;
    setJob(emptyJob);
    setStage("ask");
    setView("agent-workspace");
    setOpenedJobId(null);
  }

  function startQuery(query: string) {
    const nextEpoch = queryEpochRef.current + 1;
    queryEpochRef.current = nextEpoch;
    setQueryEpoch(nextEpoch);
    askQueryRef.current = null;
    setJob({
      ...emptyJob,
      askDraft: { text: query, species: "", structuredDescription: "" },
    });
    setStage("ask");
    setView("agent-workspace");
    setOpenedJobId(null);
  }

  // JobState 局部更新助手(集中改字段,回退不动这些字段)。
  function patchJob(patch: Partial<JobState>) {
    setJob((prev) => ({ ...prev, ...patch }));
  }

  // 模式是解析契约的一部分；已有解析链不能跨模式复用。
  function changeMode(nextMode: Mode) {
    if (job.runStatus === "running") return;
    if (nextMode === modeRef.current) return;
    modeRef.current = nextMode;
    setMode(nextMode);
    if (
      !openedJobId &&
      (job.parsedIntent != null || job.confirmedRequest != null || job.jobId != null)
    ) {
      patchJob({
        parsedIntent: null,
        reviewDraft: null,
        confirmedRequest: null,
        modulePlan: null,
        runStatus: "idle",
        jobId: null,
      });
      setStage("ask");
    }
  }

  // 阶段进入条件(spec §6 stepper 规则):
  // ask→review 需 parsedIntent;review→route 需 confirmedRequest?.species;
  // route→run 需 modulePlan(静态预期已算出);run→results 需 jobId + 成功/弃权终态。
  // 回退不受此限(已完成阶段可点回退,回退只改 stage 不清字段)。
  // 本函数即 StepperRail 的 jump 守卫;也用于前进跳转守卫与阶段可达性判定。
  function canEnter(target: Stage): boolean {
    switch (target) {
      case "ask":
        return true;
      case "review":
        return job.parsedIntent != null;
      case "route":
        return Boolean(
          (job.confirmedRequest?.species as string | undefined)?.toString().trim(),
        );
      case "run":
        return job.modulePlan != null;
      case "results":
        return (
          job.jobId != null &&
          (job.runStatus === "succeeded" || job.runStatus === "abstained")
        );
    }
  }

  // 当前阶段的进入前提是否满足:渲染前守卫,避免异常路径下渲染半成品阶段
  // (读的是已 commit 的 job 状态,非 stale 闭包)。StepperRail 复用 canEnter 做 jump 守卫。
  const stageReady = stage === "ask" || canEnter(stage);
  // 实际渲染的阶段:守卫兜底时回落到 ask(异常路径不渲半成品阶段)。
  const effectiveStage: Stage = stageReady ? stage : "ask";

  // 每个阶段都是独立页面；阶段切换后应从新页面顶部开始，而不是继承上一阶段的滚动位置。
  // layout effect 在浏览器绘制新阶段前归零并把焦点移入新主区，让键盘和读屏用户
  // 都能感知 state-driven 的页面变化。
  useLayoutEffect(() => {
    const main = mainScrollRef.current;
    main?.scrollTo({ top: 0, left: 0 });
    main?.focus({ preventScroll: true });
  }, [effectiveStage, openedJobId, view]);

  // StepperRail 的 jump:已完成阶段回退 / 紧邻可达阶段前进(rail 内部已做逐步不跳过约束,
  // 此处再以 canEnter 兜底,非法 target 忽略)。回退只改 stage,不清 JobState 字段(不丢数据)。
  function jumpTo(target: Stage) {
    if (job.runStatus === "running") return;
    if (target !== "ask" && !canEnter(target)) return;
    setStage(target);
  }

  // 主区当前展示的 job（供侧栏高亮）：历史 job 优先;否则 results 阶段展示当前 job。
  const activeJobId =
    view === "agent-workspace" || view === "reports"
      ? openedJobId ?? (view === "agent-workspace" && stage === "results" ? job.jobId : null)
      : null;

  return (
    <div className="app-shell">
      {/* 左:独立 Job Sidebar(历史 job / 收藏;不与阶段轨混,spec §1) */}
      <JobSidebar
        jobs={jobs}
        jobsErr={jobsErr}
        activeJobId={activeJobId}
        view={view}
        onNewQuery={newQuery}
        onNavigate={(nextView) => {
          setView(nextView);
          if (nextView !== "agent-workspace") setOpenedJobId(null);
        }}
        onOpenJob={(id) => {
          const nextEpoch = queryEpochRef.current + 1;
          queryEpochRef.current = nextEpoch;
          setQueryEpoch(nextEpoch);
          askQueryRef.current = null;
          setView("agent-workspace");
          setOpenedJobId(id);
        }}
        health={h}
        healthErr={healthErr}
        mode={mode}
      />

      <div className="main">
        {/* 顶栏:mode pill + LLM 提示 + light/dark 主题开关 */}
        <TopBar
          mode={mode}
          onMode={changeMode}
          theme={theme}
          onToggleTheme={() =>
            setTheme((t) => (t === "light" ? "dark" : "light"))
          }
        />

        <main ref={mainScrollRef} className="main-scroll" tabIndex={-1}>
          <div className="main-inner">
            {/* 右:Workspace(工作区,内含左侧 StepperRail)。
                历史 job 模式:直接进 results,以该 job_id 渲 ResultsStage 7 tab 外壳(等价旧 openedJobId 分支)。 */}
            {view === "datasets" ? (
              <DataLibrary section="datasets" />
            ) : view === "packs" ? (
              <DataLibrary section="packs" />
            ) : view !== "agent-workspace" ? (
              <PlatformPage
                page={view}
                jobs={jobs}
                jobsError={jobsErr}
                health={h}
                healthError={healthErr}
                openedJobId={view === "reports" ? openedJobId : null}
                onNavigate={setView}
                onOpenJob={(id) => {
                  const nextEpoch = queryEpochRef.current + 1;
                  queryEpochRef.current = nextEpoch;
                  setQueryEpoch(nextEpoch);
                  askQueryRef.current = null;
                  setView("reports");
                  setOpenedJobId(id);
                }}
                onCloseReport={() => setOpenedJobId(null)}
                onNewQuery={newQuery}
                onStartQuery={startQuery}
              />
            ) : (
              <section className="agent-workspace" aria-label="Agent Workspace">
                <header className="agent-context-header">
                  <div>
                    <span className="platform-eyebrow">
                      AGENT WORKSPACE · GOVERNED RUN
                    </span>
                    <h1>Ask a supported scientific question.</h1>
                    <p>
                      {openedJobId
                        ? "当前正在审计历史运行；Pack、模型与数据身份以后端保存的 execution identity 为准。"
                        : "当前部署尚无持久化 Virtual Cell registry；该请求以 unbound 模式进入既有五阶段治理流程。"}
                    </p>
                  </div>
                  <span className="agent-cell-chip">
                    <span>Current virtual cell</span>
                    <strong>
                      {openedJobId
                        ? "See saved execution identity"
                        : "Not bound"}
                    </strong>
                  </span>
                </header>
                {openedJobId ? (
                  <LazyResultsStage
                    key={openedJobId}
                    jobId={openedJobId}
                    onReset={newQuery}
                  />
                ) : (
                  <Workspace
                    key={queryEpoch}
                    stage={effectiveStage}
                    job={job}
                    mode={mode}
                    canEnter={canEnter}
                    onJump={jumpTo}
                    onMode={changeMode}
                    onAskDraftChanged={(draft, composedQuery) => {
                      askQueryRef.current = composedQuery;
                      setJob((prev) => {
                        const matchesLastParse =
                          prev.parsedIntent != null &&
                          prev.query === composedQuery &&
                          prev.parsedMode === modeRef.current;
                        return {
                          ...prev,
                          askDraft: draft,
                          ...(!matchesLastParse && {
                            parsedIntent: null,
                            reviewDraft: null,
                            confirmedRequest: null,
                            modulePlan: null,
                            runStatus: "idle" as const,
                            jobId: null,
                          }),
                        };
                      });
                    }}
                    onParsed={(r, query, draft, parsedMode) => {
                      if (
                        queryEpoch !== queryEpochRef.current ||
                        parsedMode !== modeRef.current ||
                        (askQueryRef.current !== null &&
                          askQueryRef.current !== query)
                      ) {
                        return;
                      }
                      askQueryRef.current = query;
                      setJob((prev) => ({
                        ...prev,
                        query,
                        askDraft: draft,
                        parsedMode,
                        parsedIntent: r,
                        reviewDraft:
                          prev.query === query &&
                          prev.parsedMode === parsedMode
                            ? prev.reviewDraft
                            : null,
                        confirmedRequest: null,
                        modulePlan: null,
                        runStatus: "idle",
                        jobId: null,
                      }));
                      setStage("review");
                    }}
                    onReviewBack={(draft) => {
                      patchJob({
                        reviewDraft: draft,
                        confirmedRequest: null,
                        modulePlan: null,
                        runStatus: "idle",
                        jobId: null,
                      });
                      setStage("ask");
                    }}
                    onReviewEdited={(draft) => {
                      patchJob({
                        reviewDraft: draft,
                        confirmedRequest: null,
                        modulePlan: null,
                        runStatus: "idle",
                        jobId: null,
                      });
                    }}
                    onConfirmed={(req) => {
                      patchJob({
                        confirmedRequest: req,
                        reviewDraft: req,
                        modulePlan: null,
                        runStatus: "idle",
                        jobId: null,
                      });
                      setStage("route");
                    }}
                    onRouteBack={() => setStage("review")}
                    onRouteNext={(plan) => {
                      patchJob({
                        modulePlan: plan,
                        runStatus: "idle",
                        jobId: null,
                      });
                      setStage("run");
                    }}
                    onRunBack={() => {
                      if (job.runStatus !== "running") setStage("route");
                    }}
                    onRunStatus={(s: RunStatus) => {
                      if (queryEpoch !== queryEpochRef.current) return;
                      patchJob({
                        runStatus: s,
                        ...((s === "running" || s === "failed") && {
                          jobId: null,
                        }),
                      });
                    }}
                    onRan={(id) => {
                      if (queryEpoch !== queryEpochRef.current) return;
                      patchJob({ jobId: id, runStatus: "succeeded" });
                      setStage("results");
                      loadJobs();
                    }}
                    onReset={newQuery}
                  />
                )}
              </section>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

// 说明:阶段渲染已迁入 Workspace;静态预期 modulePlan 由 RouteStage 派生、经 onRouteNext 传入。
// AppShell 只保留状态机(stage/job/canEnter)与跳转编排。
