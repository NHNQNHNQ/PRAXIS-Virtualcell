import {
  type JobState,
  type Mode,
  type ModulePlan,
  type ParseResult,
  type Stage,
} from "../../api";
import AskView from "../../views/AskView";
import ParseReviewView from "../../views/ParseReviewView";
import ConfirmView from "../../views/ConfirmView";
import ModuleContextView from "../../views/ModuleContextView";
import RunConfirmView from "../../views/RunConfirmView";
import ResultView from "../../views/ResultView";
import StepperRail from "./StepperRail";

// Workspace(Task 9.7)—— 主工作区:左侧阶段轨(StepperRail)+ 右侧当前阶段内容。
// 阶段轨在工作区内部左侧(spec §1),不是全局侧栏。
// 本 task 阶段内容仍桥接旧 views/*(与 9.5 一致),P3 逐个替换为新 components/stages/*。
// AppShell 拥有状态机(stage/job/reviewSub/canEnter)与所有跳转;Workspace 只做呈现与转发。
// 窄屏(max-width:900px)时阶段轨由竖向 rail 降级为顶部水平 stepper(见 components.css)。

// review 阶段内部子步(与 AppShell 一致):summary=只读核对,form=可编辑确认。
type ReviewSub = "summary" | "form";

export default function Workspace({
  stage,
  job,
  mode,
  reviewSub,
  canEnter,
  onJump,
  onMode,
  onParsed,
  onReviewNext,
  onReviewBack,
  onConfirmed,
  onRouteBack,
  onRouteNext,
  onRunBack,
  onRan,
  onReset,
}: {
  stage: Stage;
  job: JobState;
  mode: Mode;
  reviewSub: ReviewSub;
  canEnter: (s: Stage) => boolean;
  onJump: (s: Stage) => void;
  onMode: (m: Mode) => void;
  onParsed: (r: ParseResult) => void;
  onReviewNext: () => void;
  onReviewBack: () => void;
  onConfirmed: (req: Record<string, unknown>) => void;
  onRouteBack: () => void;
  onRouteNext: (plan: ModulePlan) => void;
  onRunBack: () => void;
  onRan: (jobId: string) => void;
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
        return <AskView mode={mode} onMode={onMode} onParsed={onParsed} />;

      case "review":
        // 合并旧 parse_review + confirm:子步 summary(只读核对)→ form(可编辑确认)。
        if (job.parsedIntent == null) return null;
        return reviewSub === "summary" ? (
          <ParseReviewView
            parseResult={job.parsedIntent}
            onBack={onReviewBack}
            onNext={onReviewNext}
          />
        ) : (
          <ConfirmView
            parseResult={job.parsedIntent}
            onBack={onReviewBack}
            onConfirmed={onConfirmed}
          />
        );

      case "route":
        if (job.confirmedRequest == null) return null;
        return (
          <ModuleContextView
            request={job.confirmedRequest}
            onBack={onRouteBack}
            onNext={() => onRouteNext(staticModulePlanStub(job.confirmedRequest))}
          />
        );

      case "run":
        if (job.confirmedRequest == null) return null;
        return (
          <RunConfirmView
            request={job.confirmedRequest}
            mode={mode}
            onBack={onRunBack}
            onRan={onRan}
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

// 轻量静态预期占位:仅承载 species 以满足 route→run 的 canEnter(modulePlan!=null)。
// 非实际路由(红线):真实静态预期分组在 P3 的 RouteStage 派生,实际路由在结果页 tab。
function staticModulePlanStub(
  request: Record<string, unknown> | null,
): ModulePlan {
  const species = request?.species == null ? "" : String(request.species);
  return {
    species,
    primary: "",
    secondary: [],
    overall_verdict: "expected",
    entries: [],
    notes: ["静态预期占位(非实际路由)"],
  };
}
