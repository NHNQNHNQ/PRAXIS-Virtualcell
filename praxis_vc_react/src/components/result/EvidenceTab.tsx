import type { CSSProperties, ReactNode } from "react";
import type { ReportResult } from "../../api";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import type { BadgeTone } from "../ui/Badge";
import EmptyState from "../ui/EmptyState";
import { EvidenceDistributionChart } from "../visualization";
function g(obj: Record<string, unknown>, key: string): unknown {
  return obj?.[key];
}
function asRecord(v: unknown): Record<string, unknown> {
  return v != null && typeof v === "object" && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : {};
}
function asStrArr(v: unknown): string[] {
  return Array.isArray(v) ? v.map((x) => String(x)) : [];
}

function cautionList(v: unknown): string[] {
  if (Array.isArray(v)) return v.map((x) => String(x));
  const rec = asRecord(v);
  return Object.entries(rec).map(([k, val]) =>
    val != null && val !== "" ? `${k}:${String(val)}` : k,
  );
}

const monoStyle: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  background: "var(--code-bg)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  padding: "1px 6px",
  color: "var(--text)",
  wordBreak: "break-word",
};
const stackStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "var(--space-4)",
};
const chipsStyle: CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "var(--space-2)",
  alignItems: "center",
};

function Mono({ children }: { children: ReactNode }) {
  return <code style={monoStyle}>{children}</code>;
}

type EvidenceRow = {
  key: string;
  label: string;
  tone: BadgeTone;
  status: string;
  detail: ReactNode;
};

function EvidenceTable({ rows }: { rows: EvidenceRow[] }) {
  return (
    <div className="table-scroll">
      <table className="kv-table module-table">
        <thead>
          <tr>
            <th style={{ width: "22%" }}>Evidence item</th>
            <th style={{ width: "18%" }}>Status</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key}>
              <td>{r.label}</td>
              <td>
                <Badge tone={r.tone}>{r.status}</Badge>
              </td>
              <td>{r.detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Chips({ items, empty = "—" }: { items: string[]; empty?: string }) {
  if (items.length === 0) {
    return <span style={{ color: "var(--text-muted)" }}>{empty}</span>;
  }
  return (
    <span style={chipsStyle}>
      {items.map((it, i) => (
        <Mono key={`${it}-${i}`}>{it}</Mono>
      ))}
    </span>
  );
}

export default function EvidenceTab({ report }: { report: ReportResult }) {
  const sr = report.structured_report ?? {};
  const prov = asRecord(g(sr, "provenance"));

  const rulesReferenced = asStrArr(g(prov, "rules_referenced"));
  const rulesHit = asStrArr(g(prov, "rules_hit"));

  const modelsUsed = asStrArr(g(sr, "models_used"));
  const modelsRejected = asStrArr(g(sr, "models_rejected"));
  const modelsFailed = asStrArr(g(sr, "models_failed"));

  const failedChecks = asStrArr(g(sr, "failed_checks"));
  const criticViolations = asStrArr(g(sr, "critic_violations"));
  const cautionFlags = cautionList(g(sr, "caution_flags"));

  const evLevel = asRecord(g(prov, "evidence_level"));
  const evLevelText = evLevel.level != null ? String(evLevel.level) : "";
  const evRationale = asStrArr(g(evLevel, "rationale"));
  const evOod = evLevel.ood_signal != null ? String(evLevel.ood_signal) : "";

  const allEmpty =
    rulesReferenced.length === 0 &&
    rulesHit.length === 0 &&
    modelsUsed.length === 0 &&
    modelsRejected.length === 0 &&
    modelsFailed.length === 0 &&
    failedChecks.length === 0 &&
    criticViolations.length === 0 &&
    cautionFlags.length === 0 &&
    evLevelText === "";

  if (allEmpty) {
    return (
      <EmptyState
        title="No evidence details available"
        hint="This run recorded no rules, model sources, or audit evidence to display."
      />
    );
  }

  const dis = asRecord(g(sr, "model_disagreement"));
  const disagreement = {
    score: typeof dis.score === "number" ? dis.score : undefined,
    metric: dis.metric != null ? String(dis.metric) : undefined,
    triggered: typeof dis.triggered === "boolean" ? dis.triggered : undefined,
  };
  const models = { used: modelsUsed, rejected: modelsRejected, failed: modelsFailed };

  const rows: EvidenceRow[] = [];

  rows.push({
    key: "rules_referenced",
    label: "Rules referenced",
    tone: "neutral",
    status: rulesReferenced.length > 0 ? `${rulesReferenced.length} rules` : "None",
    detail: <Chips items={rulesReferenced} empty="No rules referenced" />,
  });

  rows.push({
    key: "rules_hit",
    label: "Rules triggered",
    tone: rulesHit.length > 0 ? "confirmed" : "neutral",
    status: rulesHit.length > 0 ? `${rulesHit.length} rules` : "None",
    detail: <Chips items={rulesHit} empty="No rules triggered" />,
  });

  rows.push({
    key: "models_used",
    label: "Models used",
    tone: modelsUsed.length > 0 ? "confirmed" : "warn",
    status: modelsUsed.length > 0 ? `${modelsUsed.length} models` : "None",
    detail: <Chips items={modelsUsed} empty="No models used" />,
  });

  rows.push({
    key: "models_rejected",
    label: "Models rejected",
    tone: modelsRejected.length > 0 ? "warn" : "neutral",
    status: modelsRejected.length > 0 ? `${modelsRejected.length} models` : "None",
    detail: <Chips items={modelsRejected} empty="No models rejected" />,
  });

  rows.push({
    key: "models_failed",
    label: "Models failed",
    tone: modelsFailed.length > 0 ? "danger" : "neutral",
    status: modelsFailed.length > 0 ? `${modelsFailed.length} models` : "None",
    detail: <Chips items={modelsFailed} empty="No models failed" />,
  });

  rows.push({
    key: "failed_checks",
    label: "Failed checks",
    tone: failedChecks.length > 0 ? "danger" : "confirmed",
    status: failedChecks.length > 0 ? `${failedChecks.length} items` : "All passed",
    detail: <Chips items={failedChecks} empty="No failed checks" />,
  });

  rows.push({
    key: "critic_violations",
    label: "Review violations",
    tone: criticViolations.length > 0 ? "danger" : "confirmed",
    status: criticViolations.length > 0 ? `${criticViolations.length} items` : "No violations",
    detail: <Chips items={criticViolations} empty="No review violations" />,
  });

  rows.push({
    key: "caution_flags",
    label: "Cautions",
    tone: cautionFlags.length > 0 ? "warn" : "neutral",
    status: cautionFlags.length > 0 ? `${cautionFlags.length} items` : "None",
    detail: <Chips items={cautionFlags} empty="No additional cautions" />,
  });

  if (evLevelText !== "" || evRationale.length > 0 || evOod !== "") {
    rows.push({
      key: "evidence_level",
      label: "Evidence level",
      tone: "neutral",
      status: evLevelText !== "" ? evLevelText : "—",
      detail:
        evRationale.length > 0 || evOod !== "" ? (
          <span
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-1)",
              color: "var(--text-muted)",
              fontSize: 13,
            }}
          >
            {evRationale.length > 0 && <Chips items={evRationale} />}
            {evOod !== "" && (
              <span>
                Out-of-distribution signal: <Mono>{evOod}</Mono>
              </span>
            )}
          </span>
        ) : (
          <span style={{ color: "var(--text-muted)" }}>—</span>
        ),
    });
  }

  return (
    <div style={stackStyle}>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "var(--space-1)",
          padding: "var(--space-3) var(--space-4)",
          borderRadius: "var(--radius)",
          border: "1px solid var(--border)",
          background: "color-mix(in srgb, var(--primary) 6%, var(--surface))",
        }}
      >
        <strong style={{ fontSize: 14, color: "var(--text)" }}>Evidence and sources for this result</strong>
        <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
          Review the rules referenced or triggered, participating models, failed checks, and cautions for this run.
        </span>
      </div>

      <Card title="Evidence and audit">
        <EvidenceTable rows={rows} />
      </Card>

      <Card title="Evidence distribution">
        <EvidenceDistributionChart disagreement={disagreement} models={models} />
      </Card>
    </div>
  );
}
