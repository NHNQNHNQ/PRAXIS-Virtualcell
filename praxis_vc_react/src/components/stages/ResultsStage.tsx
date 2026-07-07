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
} from "../../api";
import Card from "../ui/Card";
import Button from "../ui/Button";
import Tabs, { type TabItem } from "../ui/Tabs";
import EmptyState from "../ui/EmptyState";
import Skeleton from "../ui/Skeleton";

// Stage 5 · Results(spec §2 Stage5)—— 结果证据页外壳:顶部 job 头 + 下载/复制工具条 + 6 tab 容器。
// P3 收官:替换旧 views/ResultView 桥接。并发拉取 report/trace/provenance/module-plan(迁 ResultView 逻辑),
// Report/Trace/Provenance 三 tab 暂用迁移进来的内联渲染;Predictions/Evidence/Module Routing 三 tab
// 先占位(EmptyState),P5(9.18–9.23)逐个实现真内容。
//
// 铁律:前端只读展示,不做预测/治理裁决;llm_used_for_prediction 如实显示 +「结果由确定性模型给出,
// 未经语言模型改写」语义(§3.5)。api.ts 请求方法复用,不新增/改端点。

// 6 tab id(受控切换,与 ui/Tabs 复用)。
type Tab =
  | "report"
  | "predictions"
  | "routing"
  | "evidence"
  | "trace"
  | "provenance";

const TAB_ITEMS: TabItem[] = [
  { id: "report", label: "报告" },
  { id: "predictions", label: "预测" },
  { id: "routing", label: "模块路由" },
  { id: "evidence", label: "证据" },
  { id: "trace", label: "运行轨迹" },
  { id: "provenance", label: "溯源" },
];

// 小工具:安全取值(迁自 ResultView)。
function g(obj: Record<string, unknown>, key: string): unknown {
  return obj?.[key];
}
function asArr(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}
function pretty(v: unknown): string {
  return JSON.stringify(v, null, 2);
}

// 前端下载:把内容存为本地文件(纯前端,不上传任何数据)。迁自 ResultView。
function download(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// 复制到剪贴板(纯前端)。失败静默(权限/不安全上下文),不阻断展示。
function copy(text: string) {
  void navigator.clipboard?.writeText(text).catch(() => {});
}

// module_plan 可能为空对象 {}(不可路由 job)。判定是否有可展示的路由。迁自 ResultView。
function isModulePlan(v: ModulePlan | Record<string, never>): v is ModulePlan {
  return Boolean(v) && Array.isArray((v as ModulePlan).entries);
}

export default function ResultsStage({
  jobId,
  onReset,
}: {
  jobId: string;
  onReset: () => void;
}) {
  const [tab, setTab] = useState<Tab>("report");
  const [report, setReport] = useState<ReportResult | null>(null);
  const [trace, setTrace] = useState<TraceResult | null>(null);
  const [prov, setProv] = useState<ProvenanceResult | null>(null);
  // module_plan:并发拉取;null=加载中/失败,ModulePlan|{} = 已到。
  const [modulePlan, setModulePlan] = useState<
    ModulePlan | Record<string, never> | null
  >(null);
  const [err, setErr] = useState<string | null>(null);

  // 数据并发拉取(迁 ResultView useEffect):report/trace/provenance 主链;module_plan 独立并发不阻塞。
  useEffect(() => {
    setErr(null);
    setReport(null);
    setTrace(null);
    setProv(null);
    setModulePlan(null);
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

  // provenance summary 文本(供 copy;失败/空时给占位)。
  const provSummary = prov
    ? pretty({ provenance: prov.provenance, llm_meta: prov.llm_meta })
    : "";

  // 工具条:下载 report.json / narrative.md / report.md;复制 report / provenance summary。
  const toolbar = (
    <>
      <Button
        variant="ghost"
        size="sm"
        disabled={!report}
        onClick={() =>
          report &&
          download(
            `${jobId}_structured_report.json`,
            pretty(report.structured_report),
            "application/json",
          )
        }
      >
        下载 report.json
      </Button>
      <Button
        variant="ghost"
        size="sm"
        disabled={!report?.narrative_report}
        onClick={() =>
          download(
            `${jobId}_narrative.md`,
            report?.narrative_report ?? "",
            "text/markdown",
          )
        }
      >
        下载 narrative.md
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() =>
          getReportMarkdown(jobId)
            .then((md) => download(`${jobId}_report.md`, md, "text/markdown"))
            .catch((e: unknown) => setErr(String(e)))
        }
      >
        下载 report.md
      </Button>
      <Button
        variant="ghost"
        size="sm"
        disabled={!report}
        onClick={() => report && copy(pretty(report.structured_report))}
      >
        复制报告
      </Button>
      <Button
        variant="ghost"
        size="sm"
        disabled={!prov}
        onClick={() => copy(provSummary)}
      >
        复制溯源摘要
      </Button>
      <Button size="sm" onClick={onReset}>
        ＋ 新建查询
      </Button>
    </>
  );

  return (
    <Card
      title={<>结果 · job {jobId}</>}
      actions={toolbar}
    >
      <Tabs
        tabs={TAB_ITEMS}
        active={tab}
        onChange={(id) => setTab(id as Tab)}
      />

      {/* 主链错误:整页降级。module_plan 失败不进此分支(独立降级)。 */}
      {err ? (
        <EmptyState title="结果加载失败" hint={err} />
      ) : (
        <div style={{ marginTop: "var(--space-3)" }}>
          {tab === "report" && (
            <ReportTab report={report} modulePlan={modulePlan} />
          )}
          {/* Predictions / Evidence / Module Routing 三 tab:P5(9.18–9.23)实现真内容,此处占位。 */}
          {tab === "predictions" && (
            <EmptyState title="此视图正在完善" hint="预测结果图将在此呈现。" />
          )}
          {tab === "routing" && (
            <EmptyState title="此视图正在完善" hint="模块路由关系图将在此呈现。" />
          )}
          {tab === "evidence" && (
            <EmptyState title="此视图正在完善" hint="证据明细将在此呈现。" />
          )}
          {tab === "trace" && <TraceTab trace={trace} loading={!report} />}
          {tab === "provenance" && (
            <ProvenanceTab prov={prov} loading={!report} />
          )}
        </div>
      )}
    </Card>
  );
}

// ───────── Report tab(迁自 ResultView.ReportTab)─────────
// 加载中(report 未到)显 Skeleton;到达后渲染 Summary / Prediction / Reliability / Boundary / Module Routing / Narrative。
function ReportTab({
  report,
  modulePlan,
}: {
  report: ReportResult | null;
  modulePlan: ModulePlan | Record<string, never> | null;
}) {
  if (!report) return <Skeleton lines={6} />;

  const sr = report.structured_report ?? {};
  const abstain = Boolean(g(sr, "abstain"));
  const prediction = g(sr, "prediction");
  const disagreement = (g(sr, "model_disagreement") ?? {}) as Record<string, unknown>;
  const learned = (g(sr, "learned_reliability") ?? {}) as Record<string, unknown>;
  const srProv = (g(sr, "provenance") ?? {}) as Record<string, unknown>;

  return (
    <>
      {/* §3.5:结果由确定性模型给出,未经语言模型改写;llm_used_for_prediction 如实显示。 */}
      <div className="badge-strong">
        结果由确定性模型给出,未经语言模型改写(llm_used_for_prediction:
        {String(report.llm_used_for_prediction)})
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
          <p className="muted">未生成文字解读(可在运行前确认时勾选"生成文字解读")。</p>
        )}
      </div>
    </>
  );
}

// 块 5:Module Routing。展示该 job 的实际模块路由(primary/secondary/overall_verdict + entries 表)。
// 空 module_plan({})或加载中降级为文案,绝不崩。迁自 ResultView。
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

// ───────── Trace tab(迁自 ResultView.TraceTab)─────────
// 主链加载中显 Skeleton;到达后无 trace 用 EmptyState 降级。
function TraceTab({ trace, loading }: { trace: TraceResult | null; loading: boolean }) {
  if (loading) return <Skeleton lines={5} />;
  const steps: TraceStep[] = trace?.trace ?? [];
  if (steps.length === 0) return <EmptyState title="暂无运行轨迹" />;
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

// ───────── Provenance tab(迁自 ResultView.ProvenanceTab)─────────
function ProvenanceTab({ prov, loading }: { prov: ProvenanceResult | null; loading: boolean }) {
  if (loading) return <Skeleton lines={5} />;
  if (!prov) return <EmptyState title="暂无溯源信息" />;
  return (
    <div className="block">
      <h3>Provenance</h3>
      <pre className="json">{pretty(prov.provenance)}</pre>
      <h3>llm_meta</h3>
      <pre className="json">{pretty(prov.llm_meta)}</pre>
    </div>
  );
}
