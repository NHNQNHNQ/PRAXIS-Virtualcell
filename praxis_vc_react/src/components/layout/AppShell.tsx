import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  getOptions,
  health,
  listJobs,
  type CellPreset,
  type Health,
  type JobSummary,
  type Options,
} from "../../api";
import PlatformPage from "../platform/PlatformPage";
import JobSidebar, { type PlatformView } from "./JobSidebar";

export default function AppShell() {
  const mainRef = useRef<HTMLElement>(null);
  const [view, setView] = useState<PlatformView>("chat");
  const [selectedCell, setSelectedCell] = useState<CellPreset | null>(null);
  const [openedJobId, setOpenedJobId] = useState<string | null>(null);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [chatEpoch, setChatEpoch] = useState(0);
  const [options, setOptions] = useState<Options | null>(null);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [runtimeHealth, setRuntimeHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  const loadJobs = useCallback(() => {
    setJobs(null);
    setJobsError(null);
    listJobs()
      .then((response) => setJobs(response.jobs))
      .catch((reason: unknown) => setJobsError(String(reason)));
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = "light";
    health()
      .then(setRuntimeHealth)
      .catch((reason: unknown) => setHealthError(String(reason)));
    getOptions()
      .then(setOptions)
      .catch((reason: unknown) => setOptionsError(String(reason)));
    loadJobs();
  }, [loadJobs]);

  useLayoutEffect(() => {
    mainRef.current?.focus({ preventScroll: true });
  }, [chatEpoch, openedJobId, view]);

  function newChat() {
    setSelectedCell(null);
    setOpenedJobId(null);
    setCurrentJobId(null);
    setView("chat");
    setChatEpoch((value) => value + 1);
  }

  function selectCell(cell: CellPreset) {
    setSelectedCell(cell);
    setOpenedJobId(null);
    setCurrentJobId(null);
    setView("chat");
    setChatEpoch((value) => value + 1);
  }

  function openJob(jobId: string) {
    setSelectedCell(null);
    setOpenedJobId(jobId);
    setCurrentJobId(jobId);
    setView("chat");
  }

  return (
    <div className="app-shell cell-chat-shell">
      <JobSidebar
        jobs={jobs}
        jobsError={jobsError}
        activeJobId={openedJobId ?? currentJobId}
        view={view}
        selectedCell={selectedCell}
        health={runtimeHealth}
        healthError={healthError}
        onNewChat={newChat}
        onNavigate={(nextView) => {
          setOpenedJobId(null);
          setView(nextView);
        }}
        onOpenJob={openJob}
      />

      <main ref={mainRef} className="cell-chat-main" tabIndex={-1}>
        <PlatformPage
          page={view}
          chatEpoch={chatEpoch}
          selectedCell={selectedCell}
          options={options}
          optionsError={optionsError}
          openedJobId={openedJobId}
          health={runtimeHealth}
          onSelectCell={selectCell}
          onBrowseCells={() => setView("data-center")}
          onNewChat={newChat}
          onJobCreated={(jobId) => {
            setCurrentJobId(jobId);
            loadJobs();
          }}
        />
      </main>
    </div>
  );
}
