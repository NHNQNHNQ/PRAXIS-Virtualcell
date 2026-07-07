import { useCallback, useEffect, useState } from "react";
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
import ResultView from "../../views/ResultView";
import JobSidebar from "./JobSidebar";
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

// JobState 初值:各字段为空,回退只改 stage 不清这些字段(回退不丢数据)。
const emptyJob: JobState = {
  query: "",
  parsedIntent: null,
  confirmedRequest: null,
  modulePlan: null,
  runStatus: "idle",
  jobId: null,
};

export default function AppShell() {
  const [mode, setMode] = useState<Mode>("offline");
  const [stage, setStage] = useState<Stage>("ask");
  const [job, setJob] = useState<JobState>(emptyJob);
  const [openedJobId, setOpenedJobId] = useState<string | null>(null); // 侧栏载入的历史 job
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [h, setH] = useState<Health | null>(null);
  const [healthErr, setHealthErr] = useState<string | null>(null);
  // 主题(light/dark):TopBar 切换,副作用写到 <html data-theme>,themes.css 据此覆盖 token。
  // 默认 light;不写 data-theme 时 themes.css 会跟随 prefers-color-scheme(系统偏好)。
  const [theme, setTheme] = useState<Theme>("light");

  const loadJobs = useCallback(() => {
    listJobs()
      .then((d) => setJobs(d.jobs))
      .catch(() => setJobs([]));
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
    setJob(emptyJob);
    setStage("ask");
    setOpenedJobId(null);
  }

  // JobState 局部更新助手(集中改字段,回退不动这些字段)。
  function patchJob(patch: Partial<JobState>) {
    setJob((prev) => ({ ...prev, ...patch }));
  }

  // 阶段进入条件(spec §6 stepper 规则):
  // ask→review 需 parsedIntent;review→route 需 confirmedRequest?.species;
  // route→run 需 modulePlan(静态预期已算出);run→results 需 runStatus∈{succeeded,failed,abstained}。
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
          job.runStatus === "succeeded" ||
          job.runStatus === "failed" ||
          job.runStatus === "abstained"
        );
    }
  }

  // 当前阶段的进入前提是否满足:渲染前守卫,避免异常路径下渲染半成品阶段
  // (读的是已 commit 的 job 状态,非 stale 闭包)。StepperRail 复用 canEnter 做 jump 守卫。
  const stageReady = stage === "ask" || canEnter(stage);
  // 实际渲染的阶段:守卫兜底时回落到 ask(异常路径不渲半成品阶段)。
  const effectiveStage: Stage = stageReady ? stage : "ask";

  // StepperRail 的 jump:已完成阶段回退 / 紧邻可达阶段前进(rail 内部已做逐步不跳过约束,
  // 此处再以 canEnter 兜底,非法 target 忽略)。回退只改 stage,不清 JobState 字段(不丢数据)。
  function jumpTo(target: Stage) {
    if (target !== "ask" && !canEnter(target)) return;
    setStage(target);
  }

  // 主区当前展示的 job（供侧栏高亮）：历史 job 优先;否则 results 阶段展示当前 job。
  const activeJobId = openedJobId ?? (stage === "results" ? job.jobId : null);

  return (
    <div className="app-shell">
      {/* 左:独立 Job Sidebar(历史 job / 收藏;不与阶段轨混,spec §1) */}
      <JobSidebar
        jobs={jobs}
        activeJobId={activeJobId}
        onNewQuery={newQuery}
        onOpenJob={(id) => setOpenedJobId(id)}
        health={h}
        healthErr={healthErr}
        mode={mode}
      />

      <div className="main">
        {/* 顶栏:mode pill + LLM 提示 + light/dark 主题开关 */}
        <TopBar
          mode={mode}
          onMode={setMode}
          theme={theme}
          onToggleTheme={() =>
            setTheme((t) => (t === "light" ? "dark" : "light"))
          }
        />

        <div className="main-scroll">
          <div className="main-inner">
            {/* 右:Workspace(工作区,内含左侧 StepperRail)。
                历史 job 模式:直接进 results,以该 job_id 渲 ResultView(等价旧 openedJobId 分支)。 */}
            {openedJobId ? (
              <ResultView
                jobId={openedJobId}
                onReset={newQuery}
                resetLabel="＋ 新建查询"
              />
            ) : (
              <Workspace
                stage={effectiveStage}
                job={job}
                mode={mode}
                canEnter={canEnter}
                onJump={jumpTo}
                onMode={setMode}
                onParsed={(r, query) => {
                  // AskStage 回传 ParseResult 与原始 query 文本,一并写入 JobState
                  // (P2 桥接的「query 暂留空」限制到此解除)。
                  patchJob({ parsedIntent: r, query });
                  setStage("review");
                }}
                onReviewBack={() => setStage("ask")}
                onConfirmed={(req) => {
                  patchJob({ confirmedRequest: req });
                  setStage("route");
                }}
                onRouteBack={() => setStage("review")}
                onRouteNext={(plan) => {
                  // 旧 ModuleContextView 不产出 modulePlan;为满足 route→run 的 canEnter,
                  // 用 Workspace 派生的轻量静态预期占位(P3 的 RouteStage 才产完整静态预期)。
                  patchJob({ modulePlan: plan });
                  setStage("run");
                }}
                onRunBack={() => setStage("route")}
                onRunStatus={(s: RunStatus) => patchJob({ runStatus: s })}
                onRan={(id) => {
                  // 实际 abstain/failed 由结果页回填;此处先置 succeeded 满足 run→results。
                  patchJob({ jobId: id, runStatus: "succeeded" });
                  setStage("results");
                  loadJobs();
                }}
                onReset={newQuery}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// 说明:阶段渲染与静态预期占位(staticModulePlanStub)已迁入 Workspace,
// AppShell 只保留状态机(stage/job/canEnter)与跳转编排。
