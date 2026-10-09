import { useEffect, useState } from "react";
import {
  getModulePlan,
  getProvenance,
  getReport,
  getReportMarkdown,
  getTrace,
  type ModulePlan,
  type ProvenanceResult,
  type ReportResult,
  type TraceResult,
} from "../../api";
import Card from "../ui/Card";
import Button from "../ui/Button";
import Tabs, { type TabItem } from "../ui/Tabs";
import EmptyState from "../ui/EmptyState";
import Skeleton from "../ui/Skeleton";
import ReportTab from "../result/ReportTab";
import PredictionsTab from "../result/PredictionsTab";
import ModuleRoutingTab from "../result/ModuleRoutingTab";
import EvidenceTab from "../result/EvidenceTab";
import TraceTab from "../result/TraceTab";
import ProvenanceTab from "../result/ProvenanceTab";
import ExecutionIdentityTab from "../result/ExecutionIdentityTab";
type Tab =
  | "report"
  | "predictions"
  | "routing"
  | "identity"
  | "evidence"
  | "trace"
  | "provenance";

export type ResultsStageProps = {
  jobId: string;
  onReset: () => void;
};

const TAB_ITEMS: TabItem[] = [
  { id: "report", label: "Report" },
  { id: "predictions", label: "Predictions" },
  { id: "routing", label: "Module routing" },
  { id: "identity", label: "Data and execution identity" },
  { id: "evidence", label: "Evidence" },
  { id: "trace", label: "Execution trace" },
  { id: "provenance", label: "Provenance" },
];

function pretty(v: unknown): string {
  return JSON.stringify(v, null, 2);
}

function download(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function copy(text: string) {
  void navigator.clipboard?.writeText(text).catch(() => {});
}

export default function ResultsStage({
  jobId,
  onReset,
}: ResultsStageProps) {
  const [tab, setTab] = useState<Tab>("report");
  const [report, setReport] = useState<ReportResult | null>(null);
  const [trace, setTrace] = useState<TraceResult | null>(null);
  const [prov, setProv] = useState<ProvenanceResult | null>(null);
  const [modulePlan, setModulePlan] = useState<ModulePlan | Record<string, never> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setErr(null);
    setReport(null);
    setTrace(null);
    setProv(null);
    setModulePlan(null);
    Promise.all([getReport(jobId), getTrace(jobId), getProvenance(jobId)])
      .then(([r, t, p]) => {
        if (cancelled) return;
        setReport(r);
        setTrace(t);
        setProv(p);
      })
      .catch((e: unknown) => {
        if (!cancelled) setErr(String(e));
      });
    getModulePlan(jobId)
      .then((d) => {
        if (!cancelled) setModulePlan(d.module_plan ?? {});
      })
      .catch(() => {
        if (!cancelled) setModulePlan({});
      });
    return () => {
      cancelled = true;
    };
  }, [jobId]);

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
        Download report.json
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
        Download narrative.md
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
        Download report.md
      </Button>
      <Button
        variant="ghost"
        size="sm"
        disabled={!report}
        onClick={() => report && copy(pretty(report.structured_report))}
      >
        Copy report
      </Button>
      <Button size="sm" onClick={onReset}>
        ＋ New query
      </Button>
    </>
  );

  return (
    <Card
      title={<>Results · job {jobId}</>}
      actions={toolbar}
      ariaLabel={`Results · job ${jobId}`}
      actionsLabel="Result actions"
    >
      <Tabs
        tabs={TAB_ITEMS}
        active={tab}
        onChange={(id) => setTab(id as Tab)}
      />

      {err ? (
        <EmptyState title="Failed to load results" hint={err} />
      ) : (
        <div style={{ marginTop: "var(--space-3)" }}>
          {tab === "report" &&
            (report ? <ReportTab report={report} /> : <Skeleton lines={6} />)}
          {tab === "predictions" &&
            (report ? <PredictionsTab report={report} /> : <Skeleton lines={6} />)}
          {tab === "routing" && <ModuleRoutingTab plan={modulePlan} />}
          {tab === "identity" && <ExecutionIdentityTab prov={prov} />}
          {tab === "evidence" &&
            (report ? <EvidenceTab report={report} /> : <Skeleton lines={6} />)}
          {tab === "trace" && <TraceTab trace={trace} />}
          {tab === "provenance" && <ProvenanceTab prov={prov} jobId={jobId} />}
        </div>
      )}
    </Card>
  );
}
