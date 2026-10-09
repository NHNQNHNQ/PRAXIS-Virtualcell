import type { CSSProperties } from "react";
import type { ModulePlan, ModulePlanEntry } from "../../api";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import EmptyState from "../ui/EmptyState";
import Skeleton from "../ui/Skeleton";
import { ModuleRoutingGraph } from "../visualization";
function isEmptyPlan(
  plan: ModulePlan | Record<string, never> | null,
): plan is null | Record<string, never> {
  if (plan == null) return true;
  const p = plan as Partial<ModulePlan>;
  const noPrimary = p.primary == null || p.primary === "";
  const noEntries = !Array.isArray(p.entries) || p.entries.length === 0;
  const noSecondary = !Array.isArray(p.secondary) || p.secondary.length === 0;
  return noPrimary && noEntries && noSecondary;
}

function verdictTone(verdict: string): "confirmed" | "warn" | "danger" | "neutral" {
  const v = verdict.toLowerCase();
  if (v === "ok" || v === "accept" || v === "accepted") return "confirmed";
  if (v === "caution") return "warn";
  if (v === "mismatch") return "danger";
  return "neutral";
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
const rowStyle: CSSProperties = {
  display: "flex",
  gap: "var(--space-3)",
  alignItems: "baseline",
  flexWrap: "wrap",
  fontSize: 13,
  color: "var(--text-muted)",
};
const labelStyle: CSSProperties = { minWidth: 96, color: "var(--text-muted)" };
const stackStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "var(--space-4)",
};

function Mono({ children }: { children: string }) {
  return <code style={codeStyle}>{children}</code>;
}

function EntriesTable({ entries }: { entries: ModulePlanEntry[] }) {
  if (entries.length === 0) {
    return (
      <p style={{ color: "var(--text-muted)", fontSize: 13, margin: 0 }}>No module entries.</p>
    );
  }
  return (
    <div className="table-scroll">
      <table className="kv-table module-table">
        <thead>
          <tr>
            <th>Module</th>
            <th>Role</th>
            <th>Decision</th>
            <th>Mismatch</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e, i) => {
            const verdict = e.verdict || "";
            return (
              <tr key={e.module ?? i}>
                <td>
                  <code style={codeStyle}>{e.module || "—"}</code>
                </td>
                <td>{e.role || "—"}</td>
                <td>
                  {verdict ? (
                    <Badge tone={verdictTone(verdict)}>{verdict}</Badge>
                  ) : (
                    "—"
                  )}
                </td>
                <td>{e.mismatch ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function ModuleRoutingTab({
  plan,
}: {
  plan: ModulePlan | Record<string, never> | null;
}) {
  if (plan === null) {
    return <Skeleton lines={6} />;
  }

  const header = (
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
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
        <Badge tone="confirmed">Actual routing (execution result)</Badge>
        <strong style={{ fontSize: 14, color: "var(--text)" }}>Actual module routing for this run</strong>
      </div>
      <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
        This view shows actual routing and decisions from the run rather than the expected modules preview.
      </span>
    </div>
  );

  if (isEmptyPlan(plan)) {
    return (
      <div style={stackStyle}>
        {header}
        <EmptyState
          title="No module routing produced"
          hint="No legacy module routing is available. The run may have abstained or used direct-v2 execution; consult Data and execution identity and Provenance."
        />
      </div>
    );
  }

  const full = plan as ModulePlan;
  const secondary = Array.isArray(full.secondary) ? full.secondary : [];
  const entries = Array.isArray(full.entries) ? full.entries : [];

  return (
    <div style={stackStyle}>
      {header}

      <Card title="Module routing graph">
        <ModuleRoutingGraph plan={full} />
      </Card>

      <Card title="Routing summary">
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          <div style={rowStyle}>
            <span style={labelStyle}>Primary module</span>
            <span style={{ color: "var(--text)", flex: 1 }}>
              <Mono>{full.primary || "—"}</Mono>
            </span>
          </div>
          <div style={rowStyle}>
            <span style={labelStyle}>Secondary modules</span>
            <span style={{ color: "var(--text)", flex: 1 }}>
              <Mono>{secondary.length ? secondary.join(", ") : "—"}</Mono>
            </span>
          </div>
          <div style={rowStyle}>
            <span style={labelStyle}>Overall decision</span>
            <span style={{ color: "var(--text)", flex: 1 }}>
              {full.overall_verdict ? (
                <Badge tone={verdictTone(full.overall_verdict)}>{full.overall_verdict}</Badge>
              ) : (
                "—"
              )}
            </span>
          </div>
        </div>
      </Card>

      <Card title="Module details">
        <EntriesTable entries={entries} />
      </Card>
    </div>
  );
}
