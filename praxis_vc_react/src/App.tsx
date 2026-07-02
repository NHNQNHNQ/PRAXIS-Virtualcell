import { useCallback, useEffect, useState } from "react";
import { health, listJobs, type Health, type JobSummary, type Mode, type ParseResult } from "./api";
import AskView from "./views/AskView";
import ConfirmView from "./views/ConfirmView";
import ResultView from "./views/ResultView";
import Sidebar from "./views/Sidebar";
import "./App.css";

type Step = "ask" | "confirm" | "result";

export default function App() {
  const [mode, setMode] = useState<Mode>("offline");
  const [step, setStep] = useState<Step>("ask");
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
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
    setJobId(null);
    setOpenedJobId(null);
    setStep("ask");
  }

  // 主区当前展示的 job(供侧栏高亮)
  const activeJobId = openedJobId ?? (step === "result" ? jobId : null);

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
                      setStep("confirm");
                    }}
                  />
                )}
                {step === "confirm" && parseResult && (
                  <ConfirmView
                    parseResult={parseResult}
                    mode={mode}
                    onBack={() => setStep("ask")}
                    onRan={(id) => {
                      setJobId(id);
                      setStep("result");
                      loadJobs();
                    }}
                  />
                )}
                {step === "result" && jobId && (
                  <ResultView jobId={jobId} onReset={newQuery} resetLabel="＋ 新建查询" />
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
