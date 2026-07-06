import { useCallback, useEffect, useState } from "react";
import {
  health,
  listJobs,
  type Health,
  type JobState,
  type JobSummary,
  type Mode,
  type ModulePlan,
  type Stage,
} from "../../api";
import AskView from "../../views/AskView";
import ParseReviewView from "../../views/ParseReviewView";
import ConfirmView from "../../views/ConfirmView";
import ModuleContextView from "../../views/ModuleContextView";
import RunConfirmView from "../../views/RunConfirmView";
import ResultView from "../../views/ResultView";
import Sidebar from "../../views/Sidebar";

// Phase 9 Task 9.5 · 状态机宿主(spec §6)。
// 集中管理 5 阶段(Ask→Review→Route→Run→Results)+ 集中式 JobState,
// 迁移旧 App.tsx 的 loadJobs/health/newQuery/activeJobId。
// 本 task 为「渐进过渡」骨架:布局层(JobSidebar/TopBar/StepperRail/Workspace)先内联,
// Stage 内容先桥接现有 views/*(用 JobState 字段喂旧 props),P3 再逐个替换成新 Stage 页。
// 铁律:api.ts 只加类型不改请求;后端零改动。

// review 阶段内部子步:旧 parse_review + confirm 合并进 review,
// 用子步在同一阶段内先只读核对(summary)再可编辑确认(form)。
type ReviewSub = "summary" | "form";

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
  const [reviewSub, setReviewSub] = useState<ReviewSub>("summary");
  const [openedJobId, setOpenedJobId] = useState<string | null>(null); // 侧栏载入的历史 job
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [h, setH] = useState<Health | null>(null);
  const [healthErr, setHealthErr] = useState<string | null>(null);

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

  // 新建查询:重置整个 JobState 回 ask,退出历史 job 模式。
  function newQuery() {
    setJob(emptyJob);
    setReviewSub("summary");
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
  // 本函数即 9.7 StepperRail 的 jump 守卫;本 task 用于前进跳转守卫与阶段可达性判定。
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
  // (读的是已 commit 的 job 状态,非 stale 闭包)。9.7 StepperRail 复用 canEnter 做 jump 守卫。
  const stageReady = stage === "ask" || canEnter(stage);

  // 主区当前展示的 job（供侧栏高亮）：历史 job 优先;否则 results 阶段展示当前 job。
  const activeJobId =
    openedJobId ?? (stage === "results" ? job.jobId : null);

  return (
    <div className="app-shell">
      {/* 左：Job Sidebar(本 task 先内联现 Sidebar,9.6 拆成 JobSidebar) */}
      <Sidebar
        jobs={jobs}
        activeJobId={activeJobId}
        onNewQuery={newQuery}
        onOpenJob={(id) => setOpenedJobId(id)}
        health={h}
        healthErr={healthErr}
        mode={mode}
      />

      <div className="main">
        {/* TopBar(本 task 先内联,9.6 拆成 TopBar 组件) */}
        <div className="topbar">
          <span className="mode-pill">mode:{mode}</span>
          <span className="notice-pill">⚠ LLM 未参与预测/治理决策</span>
        </div>

        <div className="main-scroll">
          <div className="main-inner">
            {/* 右：Workspace(本 task 先内联,9.7 拆成 Workspace + StepperRail)。
                历史 job 模式:直接进 results,以该 job_id 渲 ResultView(等价旧 openedJobId 分支)。 */}
            {openedJobId ? (
              <ResultView
                jobId={openedJobId}
                onReset={newQuery}
                resetLabel="＋ 新建查询"
              />
            ) : stageReady ? (
              renderStage()
            ) : (
              renderStage("ask")
            )}
          </div>
        </div>
      </div>
    </div>
  );

  // 按 stage 渲染 Stage 内容,桥接旧 views/*,用 JobState 字段喂旧 props。
  // override:守卫兜底时强制渲染某阶段(正常线性流程不传,用当前 stage)。
  function renderStage(override?: Stage) {
    switch (override ?? stage) {
      case "ask":
        return (
          <AskView
            mode={mode}
            onMode={setMode}
            onParsed={(r) => {
              // 旧 AskView 的 onParsed 只回传 ParseResult(不含 query 文本);
              // query 文本在 P3 的 AskStage 才回传,此处桥接暂留空。
              patchJob({ parsedIntent: r });
              setReviewSub("summary");
              setStage("review");
            }}
          />
        );

      case "review":
        // 合并旧 parse_review + confirm:子步 summary(只读核对)→ form(可编辑确认)。
        if (job.parsedIntent == null) return null;
        return reviewSub === "summary" ? (
          <ParseReviewView
            parseResult={job.parsedIntent}
            onBack={() => setStage("ask")}
            onNext={() => setReviewSub("form")}
          />
        ) : (
          <ConfirmView
            parseResult={job.parsedIntent}
            onBack={() => setReviewSub("summary")}
            onConfirmed={(req) => {
              patchJob({ confirmedRequest: req });
              setStage("route");
            }}
          />
        );

      case "route":
        if (job.confirmedRequest == null) return null;
        return (
          <ModuleContextView
            request={job.confirmedRequest}
            onBack={() => {
              setReviewSub("form");
              setStage("review");
            }}
            onNext={() => {
              // 旧 ModuleContextView 不产出 modulePlan;为满足 route→run 的 canEnter,
              // 派生一个轻量静态预期占位(P3 的 RouteStage 才产完整静态预期)。
              patchJob({ modulePlan: staticModulePlanStub(job.confirmedRequest) });
              setStage("run");
            }}
          />
        );

      case "run":
        if (job.confirmedRequest == null) return null;
        return (
          <RunConfirmView
            request={job.confirmedRequest}
            mode={mode}
            onBack={() => setStage("route")}
            onRan={(id) => {
              // 实际 abstain/failed 由结果页回填;此处先置 succeeded 满足 run→results。
              patchJob({ jobId: id, runStatus: "succeeded" });
              setStage("results");
              loadJobs();
            }}
          />
        );

      case "results":
        if (job.jobId == null) return null;
        return (
          <ResultView
            jobId={job.jobId}
            onReset={newQuery}
            resetLabel="＋ 新建查询"
          />
        );
    }
  }
}

// 轻量静态预期占位:仅承载 species 以满足 route→run 的 canEnter(modulePlan!=null)。
// 非实际路由(红线 3),真实静态预期分组在 P3 的 RouteStage 派生,实际路由在结果页 tab。
function staticModulePlanStub(
  request: Record<string, unknown> | null,
): ModulePlan {
  const species =
    request?.species == null ? "" : String(request.species);
  return {
    species,
    primary: "",
    secondary: [],
    overall_verdict: "expected",
    entries: [],
    notes: ["静态预期占位(非实际路由)"],
  };
}
