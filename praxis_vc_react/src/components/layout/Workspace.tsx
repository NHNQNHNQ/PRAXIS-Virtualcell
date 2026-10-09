import {
  type AskDraft,
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
import LazyResultsStage from "../stages/LazyResultsStage";
import StepperRail from "./StepperRail";


export default function Workspace({
  stage,
  job,
  mode,
  canEnter,
  onJump,
  onMode,
  onAskDraftChanged,
  onParsed,
  onReviewBack,
  onReviewEdited,
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
  onAskDraftChanged: (draft: AskDraft, composedQuery: string) => void;
  onParsed: (
    r: ParseResult,
    query: string,
    draft: AskDraft,
    parsedMode: Mode,
  ) => void;
  onReviewBack: (draft: Record<string, unknown>) => void;
  onReviewEdited: (draft: Record<string, unknown>) => void;
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
      <StepperRail
        stage={stage}
        canEnter={canEnter}
        onJump={onJump}
        locked={job.runStatus === "running"}
      />
      <div className="ws-stage">{renderStage()}</div>
    </div>
  );

  function renderStage() {
    switch (stage) {
      case "ask":
        return (
          <AskStage
            initialDraft={job.askDraft}
            mode={mode}
            onMode={onMode}
            onDraftChanged={onAskDraftChanged}
            onParsed={onParsed}
          />
        );

      case "review":
        if (job.parsedIntent == null) return null;
        return (
          <ReviewStage
            parsedIntent={job.parsedIntent}
            initialRequest={job.reviewDraft ?? job.confirmedRequest}
            onConfirmed={onConfirmed}
            onBack={onReviewBack}
            onEdited={onReviewEdited}
          />
        );

      case "route":
        if (job.confirmedRequest == null) return null;
        return (
          <RouteStage
            request={job.confirmedRequest}
            onBack={onRouteBack}
            onNext={onRouteNext}
          />
        );

      case "run":
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
        return <LazyResultsStage jobId={job.jobId} onReset={onReset} />;
    }
  }
}
