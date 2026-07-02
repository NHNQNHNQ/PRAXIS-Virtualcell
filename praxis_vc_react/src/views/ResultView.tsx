import { useEffect, useState } from "react";
import {
  getProvenance,
  getReport,
  getReportMarkdown,
  getTrace,
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

export default function ResultView({
  jobId,
  onReset,
  resetLabel = "新建查询",
}: {
  jobId: string;
  onReset: () => void;
  resetLabel?: string;
}) {
  const [tab, setTab] = useState<Tab>("report");
  const [report, setReport] = useState<ReportResult | null>(null);
  const [trace, setTrace] = useState<TraceResult | null>(null);
  const [prov, setProv] = useState<ProvenanceResult | null>(null);
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
  }, [jobId]);

  if (err) return <pre className="err">{err}</pre>;
  if (!report) return <p>加载报告中…(job {jobId})</p>;

  return (
    <section className="card">
      <div className="row between">
        <h2>3 · 结果(job {jobId})</h2>
        <div className="row">
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
        {(["report", "trace", "provenance"] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            className={tab === t ? "tab active" : "tab"}
            onClick={() => setTab(t)}
          >
            {t === "report" ? "Report" : t === "trace" ? "Trace" : "Provenance"}
          </button>
        ))}
      </div>

      {tab === "report" && <ReportTab report={report} />}
      {tab === "trace" && <TraceTab trace={trace} />}
      {tab === "provenance" && <ProvenanceTab prov={prov} />}
    </section>
  );
}

function ReportTab({ report }: { report: ReportResult }) {
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
