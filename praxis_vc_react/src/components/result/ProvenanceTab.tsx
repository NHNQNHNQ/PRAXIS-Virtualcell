import type { CSSProperties, ReactNode } from "react";
import type { ProvenanceResult } from "../../api";
import Card from "../ui/Card";
import Button from "../ui/Button";
import EmptyState from "../ui/EmptyState";
import Skeleton from "../ui/Skeleton";

// Stage 5 · Provenance tab(spec §2 Provenance / §3.5 / §4 ⑥ Provenance summary card)——
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
function asArr(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}

function mapList(v: unknown): string[] {
  const rec = asRecord(v);
  return Object.entries(rec).map(([k, val]) =>
    val != null && val !== "" ? `${k}:${String(val)}` : k,
  );
}

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

const stackStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "var(--space-4)",
};
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
const chipsStyle: CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: "var(--space-2)",
  alignItems: "center",
};
const jsonPreStyle: CSSProperties = {
  margin: 0,
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  lineHeight: 1.5,
  color: "var(--text)",
  background: "var(--code-bg)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  padding: "var(--space-3)",
  maxHeight: 420,
  overflow: "auto",
  whiteSpace: "pre",
};

function Mono({ children }: { children: ReactNode }) {
  return <code style={monoStyle}>{children}</code>;
}

type AuditRow = {
  key: string;
  label: string;
  detail: ReactNode;
};

function AuditTable({ rows }: { rows: AuditRow[] }) {
  return (
    <div className="table-scroll">
      <table className="kv-table module-table">
        <thead>
          <tr>
            <th style={{ width: "28%" }}>Audit item</th>
            <th>Content</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key}>
              <td>{r.label}</td>
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

export default function ProvenanceTab({
  prov,
  jobId,
}: {
  prov: ProvenanceResult | null;
  jobId: string;
}) {
  if (prov == null) {
    return (
      <Card title="Provenance">
        <Skeleton lines={6} />
      </Card>
    );
  }

  const p = asRecord(prov.provenance);
  const llmMeta = asRecord(prov.llm_meta);

  const nMessages = typeof g(p, "n_messages") === "number" ? Number(g(p, "n_messages")) : null;
  const rulesReferenced = asStrArr(g(p, "rules_referenced"));
  const rulesHit = asStrArr(g(p, "rules_hit"));
  const orthologCautions = mapList(g(p, "ortholog_cautions"));
  const rejectionReasons = mapList(g(p, "rejection_reasons"));
  const modelsUsed = asStrArr(g(p, "models_used"));
  const modelsRejected = asStrArr(g(p, "models_rejected"));
  const modelsFailed = asStrArr(g(p, "models_failed"));
  const criticViolations = asStrArr(g(p, "critic_violations"));

  // direct-v2 provenance: execution contract + immutable plan/compatibility report.
  const executionContract =
    g(p, "execution_contract") != null ? String(g(p, "execution_contract")) : "";
  const executionPlan = asRecord(g(p, "execution_plan"));
  const directSteps = Array.isArray(g(executionPlan, "steps"))
    ? (g(executionPlan, "steps") as unknown[]).map(asRecord)
    : [];
  const compatibilityReports = Array.isArray(g(p, "compatibility_reports"))
    ? (g(p, "compatibility_reports") as unknown[]).map(asRecord)
    : [];
  const directReport = compatibilityReports[0] ?? asRecord(asArr(g(executionPlan, "reports"))[0]);
  const directModels = directSteps.map((step) => {
    const name = String(g(step, "model_name") ?? "—");
    const version = String(g(step, "model_version") ?? "—");
    return `${name}@${version}`;
  });
  const directScope = String(g(directReport, "research_execution_scope") ?? "—");

  const modulePlan = asRecord(g(p, "module_plan"));
  const mpPrimary = modulePlan.primary != null ? String(modulePlan.primary) : "";
  const mpSecondary = asStrArr(g(modulePlan, "secondary"));
  const mpVerdict = modulePlan.overall_verdict != null ? String(modulePlan.overall_verdict) : "";
  const mpEntries = Array.isArray(modulePlan.entries) ? modulePlan.entries.length : 0;

  const evLevel = asRecord(g(p, "evidence_level"));
  const evLevelText = evLevel.level != null ? String(evLevel.level) : "";
  const evRationale = asStrArr(g(evLevel, "rationale"));
  const evOod = evLevel.ood_signal != null ? String(evLevel.ood_signal) : "";

  const learningQueue = asRecord(g(p, "learning_queue"));
  const lqItems = Array.isArray(learningQueue.items) ? learningQueue.items.length : 0;

  const hasModulePlan = mpPrimary !== "" || mpVerdict !== "" || mpEntries > 0;
  const allEmpty =
    nMessages == null &&
    rulesReferenced.length === 0 &&
    rulesHit.length === 0 &&
    orthologCautions.length === 0 &&
    rejectionReasons.length === 0 &&
    modelsUsed.length === 0 &&
    modelsRejected.length === 0 &&
    modelsFailed.length === 0 &&
    criticViolations.length === 0 &&
    !hasModulePlan &&
    evLevelText === "" &&
    evRationale.length === 0 &&
    evOod === "" &&
    lqItems === 0 &&
    executionContract === "";

  const provSummary = pretty({ provenance: prov.provenance, llm_meta: prov.llm_meta });

  const actions = (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={() =>
          download(`${jobId}_provenance.json`, pretty(prov.provenance), "application/json")
        }
      >
        Download provenance JSON
      </Button>
      <Button variant="ghost" size="sm" onClick={() => copy(provSummary)}>
        Copy provenance summary
      </Button>
    </>
  );

  if (allEmpty) {
    return (
      <Card title="Provenance" actions={actions}>
        <EmptyState
          title="No provenance available"
          hint="This run recorded no rules, model sources, or audit evidence to display. Review the full payload in the JSON below."
        />
        <div style={{ marginTop: "var(--space-4)" }}>
          <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: "var(--space-2)" }}>
            Full provenance JSON
          </div>
          <pre style={jsonPreStyle}>{pretty(prov.provenance)}</pre>
        </div>
      </Card>
    );
  }

  const idRows: AuditRow[] = [
    { key: "job_id", label: "Job ID", detail: <Mono>{jobId}</Mono> },
  ];

  const directRows: AuditRow[] = [];
  if (executionContract !== "") {
    directRows.push(
      {
        key: "execution_contract",
        label: "Execution contract",
        detail: <Mono>{executionContract}</Mono>,
      },
      {
        key: "execution_plan",
        label: "Execution plan",
        detail: (
          <span style={chipsStyle}>
            <Mono>{String(g(executionPlan, "schema_version") ?? "—")}</Mono>
            <Mono>{String(g(executionPlan, "plan_id") ?? "—")}</Mono>
          </span>
        ),
      },
      {
        key: "pack",
        label: "Omics Pack",
        detail: (
          <Mono>
            {String(g(executionPlan, "pack_id") ?? "—")}@
            {String(g(executionPlan, "pack_version") ?? "—")}
          </Mono>
        ),
      },
      {
        key: "direct_models",
        label: "Execution models",
        detail: <Chips items={directModels} empty="No execution models" />,
      },
      {
        key: "research_scope",
        label: "Research execution scope",
        detail: (
          <span style={chipsStyle}>
            <Mono>{directScope}</Mono>
            <Mono>
              research_authorized=
              {String(g(directReport, "research_execution_authorized") ?? "—")}
            </Mono>
          </span>
        ),
      },
      {
        key: "science_policy",
        label: "Scientific / production status",
        detail: (
          <span style={chipsStyle}>
            <Mono>
              scientifically_validated=
              {String(g(directReport, "scientifically_validated") ?? "—")}
            </Mono>
            <Mono>
              benchmark_passed={String(g(directReport, "benchmark_passed") ?? "—")}
            </Mono>
            <Mono>
              production_promoted={String(g(directReport, "production_promoted") ?? "—")}
            </Mono>
          </span>
        ),
      },
    );
  }
  if (nMessages != null) {
    idRows.push({
      key: "n_messages",
      label: "Message steps",
      detail: <Mono>{nMessages}</Mono>,
    });
  }

  const ruleRows: AuditRow[] = [
    {
      key: "rules_referenced",
      label: "Rules referenced",
      detail: <Chips items={rulesReferenced} empty="No rules referenced" />,
    },
    {
      key: "rules_hit",
      label: "Rules triggered",
      detail: <Chips items={rulesHit} empty="No rules triggered" />,
    },
  ];

  const modelRows: AuditRow[] = [
    {
      key: "models_used",
      label: "Models used",
      detail: <Chips items={modelsUsed} empty="No models used" />,
    },
    {
      key: "models_rejected",
      label: "Models rejected",
      detail: <Chips items={modelsRejected} empty="No models rejected" />,
    },
    {
      key: "models_failed",
      label: "Models failed",
      detail: <Chips items={modelsFailed} empty="No models failed" />,
    },
  ];
  if (rejectionReasons.length > 0) {
    modelRows.push({
      key: "rejection_reasons",
      label: "Rejection reasons",
      detail: <Chips items={rejectionReasons} />,
    });
  }
  if (orthologCautions.length > 0) {
    modelRows.push({
      key: "ortholog_cautions",
      label: "Orthology hints",
      detail: <Chips items={orthologCautions} />,
    });
  }

  const govRows: AuditRow[] = [
    {
      key: "critic_violations",
      label: "Review violations",
      detail: <Chips items={criticViolations} empty="No review violations" />,
    },
  ];
  if (evLevelText !== "" || evRationale.length > 0 || evOod !== "") {
    govRows.push({
      key: "evidence_level",
      label: "Evidence level",
      detail: (
        <span
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-1)",
            color: "var(--text-muted)",
            fontSize: 13,
          }}
        >
          <span>
            Level: <Mono>{evLevelText !== "" ? evLevelText : "—"}</Mono>
            {evOod !== "" && (
              <>
                {"  "}Out-of-distribution signal: <Mono>{evOod}</Mono>
              </>
            )}
          </span>
          {evRationale.length > 0 && <Chips items={evRationale} />}
        </span>
      ),
    });
  }

  const moduleRows: AuditRow[] = [];
  if (hasModulePlan) {
    moduleRows.push({
      key: "module_plan",
      label: "Modules involved",
      detail: (
        <span style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
          <span>
            Primary module:<Mono>{mpPrimary !== "" ? mpPrimary : "—"}</Mono>
            {"  "}Overall decision: <Mono>{mpVerdict !== "" ? mpVerdict : "—"}</Mono>
          </span>
          <span style={{ color: "var(--text-muted)", fontSize: 13 }}>
            Secondary modules: <Chips items={mpSecondary} empty="None" />
            {"  "}Module entries: {mpEntries} entries
          </span>
        </span>
      ),
    });
  }
  if (lqItems > 0) {
    moduleRows.push({
      key: "learning_queue",
      label: "Learning items",
      detail: <span style={{ color: "var(--text-muted)" }}>{lqItems} items (see the full JSON for details)</span>,
    });
  }

  return (
    <Card title="Provenance" actions={actions}>
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
          <strong style={{ fontSize: 14, color: "var(--text)" }}>Provenance and audit records for this run</strong>
          <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
            Review the run identity, rules referenced or triggered, model sources, reviews, evidence levels, and modules involved. Download the full payload below or copy the summary for your records.
          </span>
        </div>

        <Card title="Run identity">
          <AuditTable rows={idRows} />
        </Card>

        {directRows.length > 0 && (
          <Card title="Direct-v2 execution scope">
            <AuditTable rows={directRows} />
          </Card>
        )}

        <Card title="Rule sources">
          <AuditTable rows={ruleRows} />
        </Card>

        <Card title="Model sources">
          <AuditTable rows={modelRows} />
        </Card>

        <Card title="Reviews and evidence levels">
          <AuditTable rows={govRows} />
        </Card>

        {moduleRows.length > 0 && (
          <Card title="Modules involved and learning items">
            <AuditTable rows={moduleRows} />
          </Card>
        )}

        <Card title="Full provenance JSON">
          <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: "var(--space-2)" }}>
            Review the full provenance payload for this run. Use the buttons above to download it or copy a summary.
          </div>
          <pre style={jsonPreStyle}>{pretty(prov.provenance)}</pre>
          {Object.keys(llmMeta).length > 0 && (
            <>
              <div
                style={{
                  fontSize: 13,
                  color: "var(--text-muted)",
                  margin: "var(--space-3) 0 var(--space-2)",
                }}
              >
                Language model metadata (llm_meta)
              </div>
              <pre style={jsonPreStyle}>{pretty(prov.llm_meta)}</pre>
            </>
          )}
        </Card>
      </div>
    </Card>
  );
}
