import type { CSSProperties, ReactNode } from "react";
import type { ReportResult } from "../../api";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import StatusPill from "../ui/StatusPill";
import EmptyState from "../ui/EmptyState";
function g(obj: Record<string, unknown>, key: string): unknown {
  return obj?.[key];
}
function asArr(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}
function asRecord(v: unknown): Record<string, unknown> {
  return v != null && typeof v === "object" && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : {};
}
function joinArr(v: unknown, sep = ", "): string {
  const arr = asArr(v);
  return arr.length ? arr.map((x) => String(x)).join(sep) : "—";
}
function pretty(v: unknown): string {
  return JSON.stringify(v, null, 2);
}

const codeStyle: CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  background: "var(--code-bg)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  padding: "1px 6px",
  color: "var(--text)",
  wordBreak: "break-word",
};
const rowsStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "var(--space-2)",
};
const rowStyle: CSSProperties = {
  display: "flex",
  gap: "var(--space-3)",
  alignItems: "baseline",
  flexWrap: "wrap",
  fontSize: 13,
  color: "var(--text-muted)",
};
const labelStyle: CSSProperties = { minWidth: 132, color: "var(--text-muted)" };
const stackStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "var(--space-4)",
};

function KV({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div style={rowStyle}>
      <span style={labelStyle}>{label}</span>
      <span style={{ color: "var(--text)", flex: 1 }}>{children}</span>
    </div>
  );
}
function Mono({ children }: { children: ReactNode }) {
  return <code style={codeStyle}>{children}</code>;
}

export default function ReportTab({
  report,
}: {
  report: ReportResult;
}) {
  const sr = report.structured_report ?? {};
  const disagreement = (g(sr, "model_disagreement") ?? {}) as Record<string, unknown>;
  const learned = (g(sr, "learned_reliability") ?? {}) as Record<string, unknown>;
  const srProv = (g(sr, "provenance") ?? {}) as Record<string, unknown>;

  const prediction = g(sr, "prediction");
  const predictionRecord = asRecord(prediction);
  const predictionValues = asArr(g(predictionRecord, "values"));
  const projectionMetadata = asRecord(g(predictionRecord, "projection_metadata"));
  const executionScope = g(sr, "execution_scope");
  const scientificallyValidated = g(sr, "scientifically_validated");
  const abstainFlag = Boolean(g(sr, "abstain"));
  const abstainDecision = String(g(learned, "abstain_decision") ?? "");
  const abstained = abstainFlag || abstainDecision === "abstain";
  const abstainReasons = asArr(g(sr, "abstain_reasons")).map((x) => String(x));
  const downgradeReasons = asArr(g(sr, "downgrade_reasons")).map((x) => String(x));

  return (
    <div style={stackStyle}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-2)",
          fontSize: 13,
          color: "var(--text-muted)",
        }}
      >
        <Badge tone="neutral">
          Prediction or abstention is determined by the runtime; language models do not alter it
        </Badge>
        <span>
          llm_used_for_prediction:<Mono>{String(report.llm_used_for_prediction)}</Mono>
        </span>
      </div>

      {executionScope != null && (
        <div
          role="note"
          style={{
            padding: "var(--space-3) var(--space-4)",
            borderRadius: "var(--radius)",
            border: "1px solid color-mix(in srgb, var(--warn) 34%, transparent)",
            background: "color-mix(in srgb, var(--warn) 8%, var(--surface))",
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-1)",
            fontSize: 13,
          }}
        >
          <strong>
            Execution scope: <Mono>{String(executionScope)}</Mono>
          </strong>
          <span style={{ color: "var(--text-muted)" }}>
            scientifically_validated=
            <Mono>{String(scientificallyValidated ?? "—")}</Mono>
            ; research execution does not imply scientific validation or production promotion.
          </span>
        </div>
      )}

      {abstained && (
        <div
          style={{
            padding: "var(--space-3) var(--space-4)",
            borderRadius: "var(--radius)",
            border: "1px solid color-mix(in srgb, var(--danger) 30%, transparent)",
            background: "color-mix(in srgb, var(--danger) 8%, var(--surface))",
            color: "var(--danger)",
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-2)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <strong style={{ fontSize: 14 }}>No prediction was produced</strong>
          </div>
          {abstainReasons.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: "var(--space-5)", fontSize: 13 }}>
              {abstainReasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          ) : (
            <span style={{ fontSize: 13 }}>No specific reason was recorded.</span>
          )}
        </div>
      )}

      <Card title="Summary">
        <div style={rowsStyle}>
          <KV label="request_id">
            <Mono>{String(g(sr, "request_id") ?? "—")}</Mono>
          </KV>
          <KV label="Models used">
            <Mono>{joinArr(g(sr, "models_used"))}</Mono>
          </KV>
          <KV label="Models rejected">
            <Mono>{joinArr(g(sr, "models_rejected"))}</Mono>
          </KV>
          <KV label="Models failed">
            <Mono>{joinArr(g(sr, "models_failed"))}</Mono>
          </KV>
        </div>
      </Card>

      <Card
        title="Predictions"
        actions={
          abstained ? (
            <Badge tone="danger">No prediction produced</Badge>
          ) : (
            <Badge tone="confirmed">Prediction produced</Badge>
          )
        }
      >
        {abstained ? (
          <p style={{ color: "var(--text-muted)", fontSize: 13, margin: 0 }}>
            No prediction was produced (see the reasons above).
          </p>
        ) : predictionValues.length > 0 ? (
          <div style={rowsStyle}>
            <KV label="output">
              <Mono>{String(g(predictionRecord, "output") ?? "—")}</Mono>
            </KV>
            <KV label="shape">
              <Mono>{joinArr(g(predictionRecord, "shape"), " × ")}</Mono>
            </KV>
            <KV label="Full vector">
              {predictionValues.length.toLocaleString("en-US")} values (download the report JSON for the full vector)
            </KV>
            <KV label="baseline">
              <Mono>{String(g(projectionMetadata, "baseline") ?? "—")}</Mono>
            </KV>
            <KV label="feature identity">
              <Mono>{String(g(projectionMetadata, "feature_ids_sha256") ?? "—")}</Mono>
            </KV>
          </div>
        ) : (
          <pre className="json">{pretty(prediction)}</pre>
        )}
        <div style={{ ...rowStyle, marginTop: "var(--space-3)" }}>
          <span style={labelStyle}>Inter-model disagreement</span>
          <span style={{ color: "var(--text)" }}>
            score=<Mono>{String(g(disagreement, "score") ?? "—")}</Mono>
            {" · "}metric=<Mono>{String(g(disagreement, "metric") ?? "—")}</Mono>
            {" · "}triggered=<Mono>{String(g(disagreement, "triggered") ?? "—")}</Mono>
          </span>
        </div>
      </Card>

      <Card title="Reliability decision">
        <div style={rowsStyle}>
          <KV label="reliability">
            <Mono>{String(g(sr, "reliability") ?? "—")}</Mono>
          </KV>
          <KV label="mode">
            <Mono>{String(g(learned, "reliability_mode") ?? "—")}</Mono>
          </KV>
          <KV label="reliability_score">
            <Mono>{String(g(learned, "reliability_score") ?? "—")}</Mono>
          </KV>
          <KV label="abstain_decision">
            <Mono>{abstainDecision || "—"}</Mono>
          </KV>
          <KV label="model_version">
            <Mono>{String(g(learned, "model_version") ?? "—")}</Mono>
          </KV>
          <KV label="artifact_sha256">
            <code style={{ ...codeStyle, fontSize: 10 }}>
              {String(g(learned, "artifact_sha256") ?? "—")}
            </code>
          </KV>
        </div>
        {downgradeReasons.length > 0 && (
          <div className="warn" style={{ marginTop: "var(--space-3)" }}>
            Downgrade reasons: {downgradeReasons.join("; ")}
          </div>
        )}
      </Card>

      <Card title="Boundaries and rules">
        <div style={rowsStyle}>
          <KV label="failed_checks">
            <Mono>{joinArr(g(sr, "failed_checks"))}</Mono>
          </KV>
          <KV label="critic_violations">
            <Mono>{joinArr(g(sr, "critic_violations"))}</Mono>
          </KV>
          <KV label="caution_flags">
            <code style={codeStyle}>{pretty(g(sr, "caution_flags"))}</code>
          </KV>
          <KV label="rules_referenced">
            <Mono>{joinArr(g(srProv, "rules_referenced"), "; ")}</Mono>
          </KV>
          <KV label="rules_hit">
            <Mono>{joinArr(g(srProv, "rules_hit"), "; ")}</Mono>
          </KV>
        </div>
      </Card>

      <Card
        title="Narrative"
        actions={
          report.narrative_report ? <StatusPill status="confirmed" /> : undefined
        }
      >
        {report.narrative_report ? (
          <>
            <div className="note">
              Generated from structured results; language models did not alter predictions or governance decisions.
            </div>
            <pre className="narrative">{report.narrative_report}</pre>
          </>
        ) : (
          <EmptyState
            title="No narrative generated"
            hint="This run did not generate a narrative."
          />
        )}
      </Card>
    </div>
  );
}
