import { type Health, type JobSummary, type Mode } from "../api";

// 侧边栏(ChatGPT 风格):品牌 + 新建查询 + 历史 Jobs 列表 + 后端状态。
export default function Sidebar({
  jobs,
  activeJobId,
  onNewQuery,
  onOpenJob,
  health,
  healthErr,
  mode,
}: {
  jobs: JobSummary[] | null;
  activeJobId: string | null;
  onNewQuery: () => void;
  onOpenJob: (jobId: string) => void;
  health: Health | null;
  healthErr: string | null;
  mode: Mode;
}) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-name">PRAXIS-VirtualCell</span>
        <span className="brand-sub">virtual-cell</span>
      </div>

      <button type="button" className="new-btn" onClick={onNewQuery}>
        <span className="plus">＋</span> 新建查询
      </button>

      <div className="side-label">历史 Jobs</div>
      <div className="job-list">
        {jobs === null ? (
          <div className="job-empty">加载中…</div>
        ) : jobs.length === 0 ? (
          <div className="job-empty">暂无 job</div>
        ) : (
          jobs.map((j) => (
            <button
              key={j.job_id}
              type="button"
              className={j.job_id === activeJobId ? "job-item active" : "job-item"}
              onClick={() => onOpenJob(j.job_id)}
            >
              <div className="job-title">
                {(j.species ?? "?")} · {j.perturbation_targets.join(", ") || "—"}
              </div>
              <div className="job-meta">
                {j.job_id} · {j.reliability ?? "?"}
                {j.abstain ? " · abstain" : ""}
              </div>
            </button>
          ))
        )}
      </div>

      <div className="side-foot">
        <div className="foot-status">
          <span className={health ? "dot ok" : "dot off"} />
          {health
            ? `后端 ${health.status} · runtime ${health.runtime_version}`
            : healthErr
              ? "后端未连通"
              : "连接中…"}
        </div>
        <div className="foot-note">{mode} · 同源 · 不存 API key</div>
      </div>
    </aside>
  );
}
