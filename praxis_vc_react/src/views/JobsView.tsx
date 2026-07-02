import { useEffect, useState } from "react";
import { listJobs, type JobSummary } from "../api";

// Jobs 页:列出 runs/ 下历史 job(只读)。点击载入历史 job → 复用 ResultView。
export default function JobsView({ onOpen }: { onOpen: (jobId: string) => void }) {
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  function refresh() {
    setErr(null);
    listJobs()
      .then((d) => setJobs(d.jobs))
      .catch((e: unknown) => setErr(String(e)));
  }

  useEffect(refresh, []);

  return (
    <section className="card">
      <div className="row between">
        <h2>历史 Jobs</h2>
        <button type="button" className="ghost" onClick={refresh}>
          刷新
        </button>
      </div>
      {err && <pre className="err">{err}</pre>}
      {jobs && jobs.length === 0 && <p className="muted">暂无历史 job。</p>}
      {jobs && jobs.length > 0 && (
        <table className="jobs">
          <thead>
            <tr>
              <th>job_id</th>
              <th>species</th>
              <th>targets</th>
              <th>abstain</th>
              <th>reliability</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.job_id}>
                <td><code>{j.job_id}</code></td>
                <td>{j.species ?? "—"}</td>
                <td>{j.perturbation_targets.join(", ") || "—"}</td>
                <td>
                  <code className={j.abstain ? "bad" : "ok"}>{String(j.abstain)}</code>
                </td>
                <td>{j.reliability ?? "—"}</td>
                <td>
                  <button type="button" onClick={() => onOpen(j.job_id)}>
                    载入
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
