import { useEffect, useState } from "react";
import { API_BASE, health, type Health, type Mode, type ParseResult } from "./api";
import AskView from "./views/AskView";
import ConfirmView from "./views/ConfirmView";
import JobsView from "./views/JobsView";
import ResultView from "./views/ResultView";
import "./App.css";

type Nav = "query" | "jobs";
type Step = "ask" | "confirm" | "result";

export default function App() {
  const [nav, setNav] = useState<Nav>("query");
  const [mode, setMode] = useState<Mode>("offline");
  const [step, setStep] = useState<Step>("ask");
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [jobId, setJobId] = useState<string | null>(null); // 查询流产出的 job
  const [openedJobId, setOpenedJobId] = useState<string | null>(null); // Jobs 列表载入的历史 job
  const [h, setH] = useState<Health | null>(null);
  const [healthErr, setHealthErr] = useState<string | null>(null);

  useEffect(() => {
    health()
      .then(setH)
      .catch((e: unknown) => setHealthErr(String(e)));
  }, []);

  function resetQuery() {
    setParseResult(null);
    setJobId(null);
    setStep("ask");
  }

  return (
    <div className="app">
      <header className="banner">
        <strong>PRAXIS-VirtualCell</strong>
        <span className="mode">mode:{mode}</span>
        <span className="notice">LLM 未参与预测/治理决策</span>
      </header>

      <p className="muted subline">
        本地只读展示前端 · API base:{API_BASE} · 前端不存/不显示 API key ·{" "}
        {h ? `后端 ${h.status}(runtime ${h.runtime_version})` : healthErr ? "后端未连通" : "连接后端…"}
      </p>

      <nav className="tabs">
        <button
          type="button"
          className={nav === "query" ? "tab active" : "tab"}
          onClick={() => setNav("query")}
        >
          查询
        </button>
        <button
          type="button"
          className={nav === "jobs" ? "tab active" : "tab"}
          onClick={() => {
            setOpenedJobId(null);
            setNav("jobs");
          }}
        >
          历史 Jobs
        </button>
      </nav>

      {nav === "query" && (
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
              }}
            />
          )}
          {step === "result" && jobId && <ResultView jobId={jobId} onReset={resetQuery} />}
        </>
      )}

      {nav === "jobs" &&
        (openedJobId ? (
          <ResultView
            jobId={openedJobId}
            onReset={() => setOpenedJobId(null)}
            resetLabel="← 返回列表"
          />
        ) : (
          <JobsView onOpen={setOpenedJobId} />
        ))}
    </div>
  );
}
