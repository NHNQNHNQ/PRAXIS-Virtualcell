import { type Health, type JobSummary, type Mode } from "../../api";

export type PlatformView =
  | "home"
  | "data-center"
  | "reports"
  | "my-cells"
  | "settings"
  | "organisms"
  | "datasets"
  | "packs"
  | "virtual-cells"
  | "agent-workspace";

const NAV_ITEMS: {
  key: PlatformView;
  label: string;
  shortLabel: string;
  icon: string;
}[] = [
  {
    key: "virtual-cells",
    label: "Virtual Cells",
    shortLabel: "Cells",
    icon: "◉",
  },
  {
    key: "agent-workspace",
    label: "Agent Workspace",
    shortLabel: "Workspace",
    icon: "↗",
  },
  { key: "reports", label: "Reports", shortLabel: "Reports", icon: "▤" },
  { key: "data-center", label: "Data Center", shortLabel: "Data", icon: "⌘" },
  { key: "my-cells", label: "My Cells", shortLabel: "My Cells", icon: "◇" },
  { key: "settings", label: "Settings", shortLabel: "Settings", icon: "⚙" },
];

const DATA_CENTER_VIEWS = new Set<PlatformView>([
  "data-center",
  "organisms",
  "datasets",
  "packs",
]);

function activeNavigation(view: PlatformView): PlatformView | null {
  return DATA_CENTER_VIEWS.has(view)
    ? "data-center"
    : view === "home"
      ? null
      : view;
}

function contextTitle(view: PlatformView): string {
  if (DATA_CENTER_VIEWS.has(view)) return "Data Center";
  return NAV_ITEMS.find((item) => item.key === view)?.label ?? "Research Home";
}

export default function JobSidebar({
  jobs,
  jobsErr,
  activeJobId,
  view,
  onNewQuery,
  onNavigate,
  onOpenJob,
  health,
  healthErr,
  mode,
}: {
  jobs: JobSummary[] | null;
  jobsErr: string | null;
  activeJobId: string | null;
  view: PlatformView;
  onNewQuery: () => void;
  onNavigate: (view: PlatformView) => void;
  onOpenJob: (jobId: string) => void;
  health: Health | null;
  healthErr: string | null;
  mode: Mode;
}) {
  const buildSha =
    health?.git_sha === "unknown" ? "unknown" : health?.git_sha.slice(0, 7);
  const activeNav = activeNavigation(view);

  return (
    <aside className="js-sidebar">
      <div className="js-global-rail">
        <button
          type="button"
          className="js-brand-mark"
          onClick={() => onNavigate("home")}
          aria-label="PRAXIS 首页"
          title="PRAXIS 首页"
        >
          P
        </button>

        <nav className="js-platform-nav" aria-label="主导航">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={
                item.key === activeNav ? "js-nav-btn active" : "js-nav-btn"
              }
              onClick={() => onNavigate(item.key)}
              aria-current={item.key === activeNav ? "page" : undefined}
              aria-label={item.label}
              title={item.label}
            >
              <span className="js-nav-icon" aria-hidden="true">
                {item.icon}
              </span>
              <span className="js-nav-label">{item.shortLabel}</span>
            </button>
          ))}
        </nav>
      </div>

      <div className="js-context-panel">
        <div className="js-brand">
          <span className="js-brand-sub">PRAXIS · VIRTUAL CELL</span>
          <span className="js-brand-name">{contextTitle(view)}</span>
        </div>

        <button type="button" className="js-new-btn" onClick={onNewQuery}>
          <span className="js-plus">＋</span> New analysis
        </button>

        <div className="js-label">Recent runs</div>
        <div className="js-joblist">
          {jobsErr ? (
            <div className="js-empty" role="alert">
              Agent Run 目录不可用
            </div>
          ) : jobs === null ? (
            <div className="js-empty">加载中…</div>
          ) : jobs.length === 0 ? (
            <div className="js-empty">还没有运行记录</div>
          ) : (
            jobs.map((j) => (
              <button
                key={j.job_id}
                type="button"
                className={
                  j.job_id === activeJobId ? "js-job active" : "js-job"
                }
                onClick={() => onOpenJob(j.job_id)}
              >
                <div className="js-job-title">
                  {(j.species ?? "未指定物种")} ·{" "}
                  {j.perturbation_targets.join("、") || "无扰动靶点"}
                </div>
                <div className="js-job-meta">
                  {j.job_id} · {j.reliability ?? "可靠度未知"}
                  {j.abstain ? " · abstained" : ""}
                </div>
              </button>
            ))
          )}
        </div>

        <div className="js-foot">
          <div className="js-foot-status">
            <span className={health ? "js-dot ok" : "js-dot off"} />
            {health
              ? `后端 ${health.status} · 产品 ${health.product_version}`
              : healthErr
                ? "后端未连通"
                : "连接中…"}
          </div>
          <div className="js-foot-note">
            {mode === "offline" ? "本地模式" : "语言模型辅助"}
            {health
              ? ` · ${health.runtime_protocol_version} · build ${buildSha}`
              : " · 同源 · 不保存密钥"}
          </div>
        </div>
      </div>
    </aside>
  );
}
