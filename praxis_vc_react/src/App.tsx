import { useCallback, useEffect, useState } from "react";
import { health, listJobs, type Health, type JobSummary, type Mode, type ParseResult } from "./api";
import AskView from "./views/AskView";
import ParseReviewView from "./views/ParseReviewView";
import ConfirmView from "./views/ConfirmView";
import ModuleContextView from "./views/ModuleContextView";
import RunConfirmView from "./views/RunConfirmView";
import ResultView from "./views/ResultView";
import Sidebar from "./views/Sidebar";
import "./App.css";

// 7 步流程:ask → parse_review → confirm → module_context → run_confirm → result → advanced。
type Step =
  | "ask"
  | "parse_review"
  | "confirm"
  | "module_context"
  | "run_confirm"
  | "result"
  | "advanced";

export default function App() {
  const [mode, setMode] = useState<Mode>("offline");
  const [step, setStep] = useState<Step>("ask");
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [confirmedRequest, setConfirmedRequest] = useState<
    Record<string, unknown> | null
  >(null); // confirm 步交出的组装 request(run 在 run_confirm 步)
  const [jobId, setJobId] = useState<string | null>(null); // 查询流产出
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
    health().then(setH).catch((e: unknown) => setHealthErr(String(e)));
    loadJobs();
  }, [loadJobs]);

  function newQuery() {
    setParseResult(null);
    setConfirmedRequest(null);
    setJobId(null);
    setOpenedJobId(null);
    setStep("ask");
  }

  // 主区当前展示的 job(供侧栏高亮):result / advanced 步均展示当前 job
  const activeJobId =
    openedJobId ?? (step === "result" || step === "advanced" ? jobId : null);

  return (
    <div className="app-shell">
      <Sidebar
        jobs={jobs}
        activeJobId={activeJobId}
        onNewQuery={newQuery}
        onOpenJob={(id) => {
          setOpenedJobId(id);
        }}
        health={h}
        healthErr={healthErr}
        mode={mode}
      />

      <div className="main">
        <div className="topbar">
          <span className="mode-pill">mode:{mode}</span>
          <span className="notice-pill">⚠ LLM 未参与预测/治理决策</span>
        </div>

        <div className="main-scroll">
          <div className="main-inner">
            {openedJobId ? (
              <ResultView
                jobId={openedJobId}
                onReset={newQuery}
                resetLabel="＋ 新建查询"
              />
            ) : (
              <>
                {step === "ask" && (
                  <AskView
                    mode={mode}
                    onMode={setMode}
                    onParsed={(r) => {
                      setParseResult(r);
                      setStep("parse_review");
                    }}
                  />
                )}
                {step === "parse_review" && parseResult && (
                  <ParseReviewView
                    parseResult={parseResult}
                    onBack={() => setStep("ask")}
                    onNext={() => setStep("confirm")}
                  />
                )}
                {step === "confirm" && parseResult && (
                  <ConfirmView
                    parseResult={parseResult}
                    onBack={() => setStep("parse_review")}
                    onConfirmed={(req) => {
                      setConfirmedRequest(req);
                      setStep("module_context");
                    }}
                  />
                )}
                {step === "module_context" && confirmedRequest && (
                  <ModuleContextView
                    request={confirmedRequest}
                    onBack={() => setStep("confirm")}
                    onNext={() => setStep("run_confirm")}
                  />
                )}
                {step === "run_confirm" && confirmedRequest && (
                  <RunConfirmView
                    request={confirmedRequest}
                    mode={mode}
                    onBack={() => setStep("module_context")}
                    onRan={(id) => {
                      setJobId(id);
                      setStep("result");
                      loadJobs();
                    }}
                  />
                )}
                {step === "result" && jobId && (
                  <ResultView
                    jobId={jobId}
                    onReset={newQuery}
                    resetLabel="＋ 新建查询"
                    onAdvanced={() => setStep("advanced")}
                  />
                )}
                {step === "advanced" && jobId && (
                  <ResultView
                    jobId={jobId}
                    onReset={newQuery}
                    resetLabel="＋ 新建查询"
                    advanced
                    onBack={() => setStep("result")}
                  />
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
