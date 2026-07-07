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
} from "../../api";
import Card from "../ui/Card";
import Button from "../ui/Button";
import Tabs, { type TabItem } from "../ui/Tabs";
import EmptyState from "../ui/EmptyState";
import Skeleton from "../ui/Skeleton";
import ReportTab from "../result/ReportTab";
import PredictionsTab from "../result/PredictionsTab";

// Stage 5 · Results(spec §2 Stage5)—— 结果证据页外壳:顶部 job 头 + 下载/复制工具条 + 6 tab 容器。
// 并发拉取 report/trace/provenance 主链(迁 ResultView 逻辑)。
// Report tab 已由 components/result/ReportTab 证据化实现(Task 9.18);Trace/Provenance 暂用内联渲染
// (Task 9.22/9.23 处理);Predictions/Module Routing/Evidence 三 tab 先占位(EmptyState),
// P5(9.19–9.21)逐个实现真内容(module_plan 改由 ModuleRoutingTab 自行拉取)。
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
  const [err, setErr] = useState<string | null>(null);

  // 数据并发拉取(迁 ResultView useEffect):report/trace/provenance 主链。
  // module_plan 由「模块路由」tab(Task 9.20 ModuleRoutingTab)自行拉取,本 tab 不再依赖。
  useEffect(() => {
    setErr(null);
    setReport(null);
    setTrace(null);
    setProv(null);
    Promise.all([getReport(jobId), getTrace(jobId), getProvenance(jobId)])
      .then(([r, t, p]) => {
        setReport(r);
        setTrace(t);
        setProv(p);
      })
      .catch((e: unknown) => setErr(String(e)));
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

      {/* 主链(report/trace/provenance)错误:整页降级。 */}
      {err ? (
        <EmptyState title="结果加载失败" hint={err} />
      ) : (
        <div style={{ marginTop: "var(--space-3)" }}>
          {tab === "report" &&
            (report ? <ReportTab report={report} /> : <Skeleton lines={6} />)}
          {/* Evidence / Module Routing 两 tab:P5(9.20–9.21)实现真内容,此处占位。 */}
          {tab === "predictions" &&
            (report ? <PredictionsTab report={report} /> : <Skeleton lines={6} />)}
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
