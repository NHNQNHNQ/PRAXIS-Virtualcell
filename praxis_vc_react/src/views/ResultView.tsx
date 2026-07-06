import { useEffect, useState } from "react";
import {
  getModulePlan,
  getProvenance,
  getReport,
  getReportMarkdown,
  getTrace,
  type ModulePlan,
  type ModulePlanEntry,
  type ProvenanceResult,
  type ReportResult,
  type TraceResult,
  type TraceStep,
} from "../api";

type Tab = "report" | "trace" | "provenance";

// 小工具:安全取值
function g(obj: Record<string, unknown>, key: string): unknown {
  return obj?.[key];
}
function asArr(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}
function pretty(v: unknown): string {
  return JSON.stringify(v, null, 2);
}

// 前端下载:把内容存为本地文件(纯前端,不上传任何数据)。
function download(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// module_plan 可能为空对象 {}(不可路由 job)。判定是否有可展示的路由。
function isModulePlan(v: ModulePlan | Record<string, never>): v is ModulePlan {
  return Boolean(v) && Array.isArray((v as ModulePlan).entries);
}

export default function ResultView({
  jobId,
  onReset,
  resetLabel = "新建查询",
  advanced = false,
  onAdvanced,
  onBack,
}: {
  jobId: string;
  onReset: () => void;
  resetLabel?: string;
  advanced?: boolean; // 为真时只显 trace + provenance 两 tab(默认 Trace)
  onAdvanced?: () => void; // result 步显"高级"按钮 → 跳 advanced 步
  onBack?: () => void; // advanced 步返回 result 步
}) {
  const [tab, setTab] = useState<Tab>(advanced ? "trace" : "report");
  const [report, setReport] = useState<ReportResult | null>(null);
  const [trace, setTrace] = useState<TraceResult | null>(null);
  const [prov, setProv] = useState<ProvenanceResult | null>(null);
  // module_plan:并发拉取;null=加载中/失败,ModulePlan|{} = 已到。
  const [modulePlan, setModulePlan] = useState<
    ModulePlan | Record<string, never> | null
  >(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setErr(null);
    Promise.all([getReport(jobId), getTrace(jobId), getProvenance(jobId)])
      .then(([r, t, p]) => {
        setReport(r);
        setTrace(t);
        setProv(p);
      })
      .catch((e: unknown) => setErr(String(e)));
    // module_plan 独立并发:失败不阻塞主报告,静默降级为空。
    getModulePlan(jobId)
      .then((d) => setModulePlan(d.module_plan))
      .catch(() => setModulePlan({}));
  }, [jobId]);

  // advanced 步只有 trace/provenance 两 tab;若当前 tab 落在 report,回退到 trace。
  const tabs: Tab[] = advanced ? ["trace", "provenance"] : ["report", "trace", "provenance"];
  const effTab: Tab = advanced && tab === "report" ? "trace" : tab;

  if (err) return <pre className="err">{err}</pre>;
  if (!report) return <p>加载报告中…(job {jobId})</p>;

  return (
    <section className="card">
      <div className="row between">
        <h2>
          {advanced ? "高级 · trace / provenance" : "3 · 结果"}(job {jobId})
        </h2>
        <div className="row">
          {advanced && onBack && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={onBack}>
              ← 返回结果
            </button>
          )}
          {!advanced && onAdvanced && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={onAdvanced}>
              高级 →
            </button>
          )}
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() =>
              download(
                `${jobId}_structured_report.json`,
                pretty(report.structured_report),
                "application/json",
              )
            }
          >
            导出 report.json
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            disabled={!report.narrative_report}
            onClick={() =>
              download(`${jobId}_narrative.md`, report.narrative_report ?? "", "text/markdown")
            }
          >
            导出 narrative.md
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() =>
              getReportMarkdown(jobId)
                .then((md) => download(`${jobId}_report.md`, md, "text/markdown"))
                .catch((e: unknown) => setErr(String(e)))
            }
          >
            导出 report.md
          </button>
          <button type="button" className="btn btn-sm" onClick={onReset}>
            {resetLabel}
          </button>
        </div>
      </div>

      <div className="tabs">
        {tabs.map((t) => (
          <button
            key={t}
            type="button"
            className={effTab === t ? "tab active" : "tab"}
            onClick={() => setTab(t)}
          >
            {t === "report" ? "Report" : t === "trace" ? "Trace" : "Provenance"}
          </button>
        ))}
      </div>

      {effTab === "report" && <ReportTab report={report} modulePlan={modulePlan} />}
      {effTab === "trace" && <TraceTab trace={trace} />}
      {effTab === "provenance" && <ProvenanceTab prov={prov} />}
    </section>
  );
}

function ReportTab({
  report,
  modulePlan,
}: {
  report: ReportResult;
  modulePlan: ModulePlan | Record<string, never> | null;
}) {
  const sr = report.structured_report ?? {};
  const abstain = Boolean(g(sr, "abstain"));
  const prediction = g(sr, "prediction");
  const disagreement = (g(sr, "model_disagreement") ?? {}) as Record<string, unknown>;
  const learned = (g(sr, "learned_reliability") ?? {}) as Record<string, unknown>;
  const srProv = (g(sr, "provenance") ?? {}) as Record<string, unknown>;

  return (
    <>
      <div className="badge-strong">
        llm_used_for_prediction:{String(report.llm_used_for_prediction)} —— LLM 未参与预测/治理决策
      </div>

      {/* 块 1:Summary */}
      <div className="block">
        <h3>Summary</h3>
        <ul className="meta">
          <li>request_id:<code>{String(g(sr, "request_id"))}</code></li>
          <li>models_used:<code>{asArr(g(sr, "models_used")).join(", ") || "—"}</code></li>
          <li>models_rejected:<code>{asArr(g(sr, "models_rejected")).join(", ") || "—"}</code></li>
          <li>models_failed:<code>{asArr(g(sr, "models_failed")).join(", ") || "—"}</code></li>
        </ul>
      </div>

      {/* 块 2:Prediction(是否 abstain) */}
      <div className="block">
        <h3>Prediction</h3>
        <p>
          abstain:
          <code className={abstain ? "bad" : "ok"}>{String(abstain)}</code>
          {abstain && asArr(g(sr, "abstain_reasons")).length > 0 && (
            <span className="muted"> — {asArr(g(sr, "abstain_reasons")).join(";")}</span>
          )}
        </p>
        {!abstain && <pre className="json">{pretty(prediction)}</pre>}
        <p className="muted">
          model_disagreement:score={String(g(disagreement, "score"))} · metric=
          {String(g(disagreement, "metric"))} · triggered=
          {String(g(disagreement, "triggered"))}
        </p>
      </div>

      {/* 块 3:Reliability decision */}
      <div className="block">
        <h3>Reliability decision</h3>
        <ul className="meta">
          <li>reliability:<code>{String(g(sr, "reliability"))}</code></li>
          <li>mode:<code>{String(g(learned, "reliability_mode"))}</code></li>
          <li>reliability_score:<code>{String(g(learned, "reliability_score"))}</code></li>
          <li>abstain_decision:<code>{String(g(learned, "abstain_decision"))}</code></li>
          <li>model_version:<code>{String(g(learned, "model_version"))}</code></li>
          <li>artifact_sha256:<code className="sha">{String(g(learned, "artifact_sha256"))}</code></li>
        </ul>
        {asArr(g(sr, "downgrade_reasons")).length > 0 && (
          <div className="warn">downgrade:{asArr(g(sr, "downgrade_reasons")).join(";")}</div>
        )}
      </div>

      {/* 块 4:Boundary */}
      <div className="block">
        <h3>Boundary</h3>
        <ul className="meta">
          <li>failed_checks:<code>{asArr(g(sr, "failed_checks")).join(", ") || "—"}</code></li>
          <li>critic_violations:<code>{asArr(g(sr, "critic_violations")).join(", ") || "—"}</code></li>
          <li>caution_flags:<code>{pretty(g(sr, "caution_flags"))}</code></li>
          <li>rules_referenced:<code>{asArr(g(srProv, "rules_referenced")).join("; ") || "—"}</code></li>
          <li>rules_hit:<code>{asArr(g(srProv, "rules_hit")).join("; ") || "—"}</code></li>
        </ul>
      </div>

      {/* 块 5:Module Routing(该 job 的实际模块路由) */}
      <ModuleRoutingBlock plan={modulePlan} />

      {/* narrative */}
      <div className="block">
        <h3>Narrative</h3>
        {report.narrative_report ? (
          <>
            <div className="note">generated from structured report(LLM 未改动预测/治理结论)</div>
            <pre className="narrative">{report.narrative_report}</pre>
          </>
        ) : (
          <p className="muted">未生成叙述报告(可在 Confirm 勾选"生成 LLM 叙述报告")。</p>
        )}
      </div>
    </>
  );
}

// 块 5:Module Routing。展示该 job 的实际模块路由(primary/secondary/overall_verdict + entries 表)。
// 空 module_plan({})或加载中降级为文案,绝不崩。
function ModuleRoutingBlock({
  plan,
}: {
  plan: ModulePlan | Record<string, never> | null;
}) {
  if (plan === null) {
    return (
      <div className="block">
        <h3>Module Routing</h3>
        <p className="muted">加载模块路由中…</p>
      </div>
    );
  }
  if (!isModulePlan(plan)) {
    return (
      <div className="block">
        <h3>Module Routing</h3>
        <p className="muted">该请求未产生模块路由(abstain/不可路由)。</p>
      </div>
    );
  }
  const entries: ModulePlanEntry[] = plan.entries ?? [];
  return (
    <div className="block">
      <h3>Module Routing</h3>
      <ul className="meta">
        <li>primary:<code>{plan.primary || "—"}</code></li>
        <li>secondary:<code>{plan.secondary?.length ? plan.secondary.join(", ") : "—"}</code></li>
        <li>overall_verdict:<code>{plan.overall_verdict || "—"}</code></li>
      </ul>
      {entries.length > 0 ? (
        <div className="table-scroll">
          <table className="kv-table module-table">
            <thead>
              <tr>
                <th>module</th>
                <th>role</th>
                <th>verdict</th>
                <th>mismatch</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, i) => (
                <tr key={e.module ?? i}>
                  <td><code>{e.module || "—"}</code></td>
                  <td>{e.role || "—"}</td>
                  <td>{e.verdict || "—"}</td>
                  <td>{e.mismatch ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">无模块条目。</p>
      )}
    </div>
  );
}

function TraceTab({ trace }: { trace: TraceResult | null }) {
  const steps: TraceStep[] = trace?.trace ?? [];
  if (steps.length === 0) return <p className="muted">无 trace。</p>;
  return (
    <div className="block">
      <h3>Agent 流程({steps.length} 步)</h3>
      <ol className="timeline">
        {steps.map((s, i) => {
          const r = s as Record<string, unknown>;
          return (
            <li key={i}>
              <span className="ts">{String(g(r, "timestamp") ?? "")}</span>
              <span className="hop">
                {String(g(r, "sender") ?? "?")} → {String(g(r, "receiver") ?? "?")}
              </span>
              <span className="mtype">{String(g(r, "message_type") ?? "")}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function ProvenanceTab({ prov }: { prov: ProvenanceResult | null }) {
  if (!prov) return <p className="muted">无 provenance。</p>;
  return (
    <div className="block">
      <h3>Provenance</h3>
      <pre className="json">{pretty(prov.provenance)}</pre>
      <h3>llm_meta</h3>
      <pre className="json">{pretty(prov.llm_meta)}</pre>
    </div>
  );
}
