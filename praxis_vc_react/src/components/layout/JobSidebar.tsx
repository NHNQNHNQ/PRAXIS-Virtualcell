import {
  type CellPreset,
  type Health,
  type JobSummary,
} from "../../api";

export type PlatformView =
  | "chat"
  | "data-center"
  | "omics-intake"
  | "pack-library";

function HistoryItems({
  jobs,
  jobsError,
  activeJobId,
  onOpenJob,
}: {
  jobs: JobSummary[] | null;
  jobsError: string | null;
  activeJobId: string | null;
  onOpenJob: (jobId: string) => void;
}) {
  if (jobsError) return <p role="alert">Report catalog unavailable</p>;
  if (jobs == null) return <p>Loading…</p>;
  if (jobs.length === 0) return <p>No reports yet</p>;

  return jobs.map((job) => (
    <button
      key={job.job_id}
      type="button"
      className={
        job.job_id === activeJobId
          ? "chat-history-item active"
          : "chat-history-item"
      }
      onClick={() => onOpenJob(job.job_id)}
    >
      <strong>
        {job.species ?? "Species unspecified"} ·{" "}
        {job.perturbation_targets.join(", ") || "No perturbation targets"}
      </strong>
      <small>{job.abstain ? "Abstained" : "Saved report"}</small>
      {job.pack_id && (
        <small>
          Pack {job.pack_id}@{job.pack_version ?? "?"}
        </small>
      )}
      {job.execution_scope && (
        <small>
          {job.execution_scope} · science={String(job.scientifically_validated)}
          {job.models_used.length ? ` · ${job.models_used.join(", ")}` : ""}
        </small>
      )}
    </button>
  ));
}

export default function JobSidebar({
  jobs,
  jobsError,
  activeJobId,
  view,
  selectedCell,
  health,
  healthError,
  onNewChat,
  onNavigate,
  onOpenJob,
}: {
  jobs: JobSummary[] | null;
  jobsError: string | null;
  activeJobId: string | null;
  view: PlatformView;
  selectedCell: CellPreset | null;
  health: Health | null;
  healthError: string | null;
  onNewChat: () => void;
  onNavigate: (view: PlatformView) => void;
  onOpenJob: (jobId: string) => void;
}) {
  return (
    <aside className="chat-sidebar">
      <button
        type="button"
        className="chat-brand"
        onClick={onNewChat}
        aria-label="New PRAXIS conversation"
      >
        <span>P</span>
        <strong>PRAXIS VirtualCell</strong>
      </button>

      <button type="button" className="chat-new-button" onClick={onNewChat}>
        <span aria-hidden="true">＋</span>
        New chat
      </button>

      <button
        type="button"
        className={view === "data-center" ? "chat-nav active" : "chat-nav"}
        onClick={() => onNavigate("data-center")}
        aria-current={view === "data-center" ? "page" : undefined}
      >
        <span aria-hidden="true">◎</span>
        Data Center
      </button>

      <button
        type="button"
        className={view === "omics-intake" ? "chat-nav active" : "chat-nav"}
        onClick={() => onNavigate("omics-intake")}
        aria-current={view === "omics-intake" ? "page" : undefined}
      >
        <span aria-hidden="true">⇧</span>
        Omics intake
      </button>

      <button
        type="button"
        className={view === "pack-library" ? "chat-nav active" : "chat-nav"}
        onClick={() => onNavigate("pack-library")}
        aria-current={view === "pack-library" ? "page" : undefined}
      >
        <span aria-hidden="true">▦</span>
        Pack library
      </button>

      <div className="chat-selected-context">
        <span>Selected cell</span>
        <strong>{selectedCell?.cell_type ?? "Not selected"}</strong>
        <small>
          {selectedCell
            ? `${selectedCell.species} · catalog preset`
            : "Choose a cell before asking"}
        </small>
      </div>

      <div className="chat-history-label">Recent reports</div>
      <div className="chat-history">
        <HistoryItems
          jobs={jobs}
          jobsError={jobsError}
          activeJobId={activeJobId}
          onOpenJob={onOpenJob}
        />
      </div>

      <details className="chat-mobile-history">
        <summary>Reports</summary>
        <div>
          <HistoryItems
            jobs={jobs}
            jobsError={jobsError}
            activeJobId={activeJobId}
            onOpenJob={onOpenJob}
          />
        </div>
      </details>

      <footer className="chat-sidebar-footer">
        <span className={health ? "chat-status-dot ok" : "chat-status-dot"} />
        <div>
          <strong>
            {health
              ? `Backend ${health.status} · v${health.product_version}`
              : healthError
                ? "Backend unavailable"
                : "Connecting…"}
          </strong>
          <small>Language models only parse and explain; they do not simulate or make final decisions</small>
        </div>
      </footer>
    </aside>
  );
}
