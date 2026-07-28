import { type Health, type JobSummary, type Mode } from "../../api";

// Job Sidebar(Task 9.6)—— 独立历史 job 侧栏,不与主工作区的阶段轨混(spec §1)。
// 由现 views/Sidebar 重写:props 签名不变,视觉迁到新 token(styles/components.css 的 .js-*)。
// 分区:品牌 / 新建查询 / 历史 Jobs(现有)/ 收藏(结构留位,数据暂空)/ 底部后端状态。
// 前端只读展示,不参与预测/治理决策。
// 文案守 spec §3.5:平实中文,无 AI/智能/助手/一键腔,无内部实现旁白。

export default function JobSidebar({
  jobs,
  activeJobId,
  dataActive,
  onNewQuery,
  onOpenData,
  onOpenJob,
  health,
  healthErr,
  mode,
}: {
  jobs: JobSummary[] | null;
  activeJobId: string | null;
  dataActive: boolean;
  onNewQuery: () => void;
  onOpenData: () => void;
  onOpenJob: (jobId: string) => void;
  health: Health | null;
  healthErr: string | null;
  mode: Mode;
}) {
  const buildSha = health?.git_sha === "unknown"
    ? "unknown"
    : health?.git_sha.slice(0, 7);

  return (
    <aside className="js-sidebar">
      <div className="js-brand">
        <span className="js-brand-name">PRAXIS-VirtualCell</span>
        <span className="js-brand-sub">虚拟细胞</span>
      </div>

      <button type="button" className="js-new-btn" onClick={onNewQuery}>
        <span className="js-plus">＋</span> 新建查询
      </button>

      <button
        type="button"
        className={dataActive ? "js-new-btn js-data-active" : "js-new-btn"}
        onClick={onOpenData}
        aria-pressed={dataActive}
      >
        数据资源
      </button>

      {/* —— 历史 Jobs（已运行任务，点击回看结果）—— */}
      <div className="js-label">历史查询</div>
      <div className="js-joblist">
        {jobs === null ? (
          <div className="js-empty">加载中…</div>
        ) : jobs.length === 0 ? (
          <div className="js-empty">还没有查询记录</div>
        ) : (
          jobs.map((j) => (
            <button
              key={j.job_id}
              type="button"
              className={j.job_id === activeJobId ? "js-job active" : "js-job"}
              onClick={() => onOpenJob(j.job_id)}
            >
              <div className="js-job-title">
                {(j.species ?? "未指定物种")} ·{" "}
                {j.perturbation_targets.join("、") || "无扰动靶点"}
              </div>
              <div className="js-job-meta">
                {j.job_id} · {j.reliability ?? "可靠度未知"}
                {j.abstain ? " · 已保留判断" : ""}
              </div>
            </button>
          ))
        )}
      </div>

      {/* —— 收藏（结构留位，数据暂空；后续接入收藏能力）—— */}
      <div className="js-fav">
        <div className="js-label">收藏</div>
        <div className="js-fav-empty">暂无收藏</div>
      </div>

      {/* —— 底部：后端连通状态 —— */}
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
          {health ? ` · ${health.runtime_protocol_version} · build ${buildSha}` : " · 同源 · 不保存密钥"}
        </div>
      </div>
    </aside>
  );
}
