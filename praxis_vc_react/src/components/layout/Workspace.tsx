import {
  type JobState,
  type Mode,
  type ModulePlan,
  type ParseResult,
  type RunStatus,
  type Stage,
} from "../../api";
import AskStage from "../stages/AskStage";
import ReviewStage from "../stages/ReviewStage";
import RouteStage from "../stages/RouteStage";
import RunStage from "../stages/RunStage";
import ResultView from "../../views/ResultView";
import StepperRail from "./StepperRail";

// Workspace(Task 9.7)—— 主工作区:左侧阶段轨(StepperRail)+ 右侧当前阶段内容。
// 阶段轨在工作区内部左侧(spec §1),不是全局侧栏。
// review 阶段已由 9.9 的 ReviewStage 合并替换旧 parse_review+confirm 两子步;
// 其余阶段仍桥接旧 views/*(P3 逐个替换为新 components/stages/*)。
// AppShell 拥有状态机(stage/job/canEnter)与所有跳转;Workspace 只做呈现与转发。
// 窄屏(max-width:900px)时阶段轨由竖向 rail 降级为顶部水平 stepper(见 components.css)。

export default function Workspace({
  stage,
  job,
  mode,
  canEnter,
  onJump,
  onMode,
  onParsed,
  onReviewBack,
  onConfirmed,
  onRouteBack,
  onRouteNext,
  onRunBack,
  onRan,
  onRunStatus,
  onReset,
}: {
  stage: Stage;
  job: JobState;
  mode: Mode;
  canEnter: (s: Stage) => boolean;
  onJump: (s: Stage) => void;
  onMode: (m: Mode) => void;
  onParsed: (r: ParseResult, query: string) => void;
  onReviewBack: () => void;
  onConfirmed: (req: Record<string, unknown>) => void;
  onRouteBack: () => void;
  onRouteNext: (plan: ModulePlan) => void;
  onRunBack: () => void;
  onRan: (jobId: string) => void;
  onRunStatus: (s: RunStatus) => void;
  onReset: () => void;
}) {
  return (
    <div className="ws">
      {/* 阶段轨:工作区内部左侧竖轨(窄屏降级为顶部水平 stepper,由 CSS 控制) */}
      <StepperRail stage={stage} canEnter={canEnter} onJump={onJump} />
      {/* 阶段内容区 */}
      <div className="ws-stage">{renderStage()}</div>
    </div>
  );

  // 按 stage 渲染阶段内容,桥接旧 views/*,用 JobState 字段喂旧 props(与 9.5 一致)。
  function renderStage() {
    switch (stage) {
      case "ask":
        return <AskStage mode={mode} onMode={onMode} onParsed={onParsed} />;

      case "review":
        // 9.9:ReviewStage 合并旧 parse_review + confirm 为同一页(上部解析摘要 + 下部可编辑分组表单)。
        // 可编辑初值优先回填 confirmedRequest(回退再进保留上次编辑值),否则用 parsedIntent 候选。
        if (job.parsedIntent == null) return null;
        return (
          <ReviewStage
            parsedIntent={job.parsedIntent}
            initialRequest={job.confirmedRequest}
            onConfirmed={onConfirmed}
            onBack={onReviewBack}
          />
        );

      case "route":
        // 9.10:RouteStage 替换旧 ModuleContextView。自派生轻量静态预期 modulePlan(overall_verdict="expected"),
        // 经 onRouteNext 传出以满足 route→run 的 canEnter。confirmedRequest 到 route 阶段必非空,保留 null 守卫。
        if (job.confirmedRequest == null) return null;
        return (
          <RouteStage
            request={job.confirmedRequest}
            onBack={onRouteBack}
            onNext={onRouteNext}
          />
        );

      case "run":
        // 9.11:RunStage 替换旧 RunConfirmView。最终请求汇总 + 完整参数 + 文字解读开关 + 预期模块 +
        // 「确定性步骤指示」(非真流式,红线 4);createJob 同步一次拿 job_id。
        // setRunStatus 由 AppShell 经 onRunStatus 落到 JobState.runStatus(running/failed);
        // 成功的 succeeded 与 jobId 由 onRan 一并落。
        if (job.confirmedRequest == null) return null;
        return (
          <RunStage
            request={job.confirmedRequest}
            mode={mode}
            onBack={onRunBack}
            onRan={onRan}
            setRunStatus={onRunStatus}
            modulePlan={job.modulePlan}
          />
        );

      case "results":
        if (job.jobId == null) return null;
        return (
          <ResultView jobId={job.jobId} onReset={onReset} resetLabel="＋ 新建查询" />
        );
    }
  }
}
