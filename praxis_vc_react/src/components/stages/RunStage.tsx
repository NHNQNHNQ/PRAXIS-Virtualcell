import { useEffect, useRef, useState } from "react";
import {
  createJob,
  type Mode,
  type ModulePlan,
  type RunStatus,
} from "../../api";
import Card from "../ui/Card";
import Button from "../ui/Button";
import Badge from "../ui/Badge";
function fmt(v: unknown): string {
  if (v == null || v === "") return "—";
  if (Array.isArray(v)) return v.length ? v.map(String).join(", ") : "—";
  return String(v);
}

// These steps illustrate the synchronous API; actual execution details appear in the trace.
const RUN_STEPS = [
  "Check input and data identity",
  "Determine species context",
  "Match validated models",
  "Predict or explicitly abstain",
  "Check safety and reliability",
  "Summarize results",
  "Save the execution record",
] as const;

const STEP_INTERVAL_MS = 450;

export default function RunStage({
  request,
  mode,
  onRan,
  onBack,
  setRunStatus,
  modulePlan,
}: {
  request: Record<string, unknown>;
  mode: Mode;
  onRan: (jobId: string) => void;
  onBack: () => void;
  setRunStatus: (s: RunStatus) => void;
  modulePlan?: ModulePlan | null;
}) {
  const [enableLlmReport, setEnableLlmReport] = useState(false);
  const [running, setRunning] = useState(false);
  const [activeStep, setActiveStep] = useState(-1);
  const [err, setErr] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (timerRef.current != null) window.clearInterval(timerRef.current);
    };
  }, []);

  const expectedModules = modulePlan
    ? [modulePlan.primary, ...modulePlan.secondary].filter((c) => c && c.trim())
    : [];

  async function run() {
    setRunning(true);
    setErr(null);
    setRunStatus("running");
    setActiveStep(0);

    if (timerRef.current != null) window.clearInterval(timerRef.current);
    timerRef.current = window.setInterval(() => {
      setActiveStep((s) => (s < RUN_STEPS.length - 2 ? s + 1 : s));
    }, STEP_INTERVAL_MS);

    try {
      const ref = await createJob(request, mode, enableLlmReport);
      if (!mountedRef.current) return;
      if (timerRef.current != null) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setActiveStep(RUN_STEPS.length - 1);
      setRunStatus("succeeded");
      onRan(ref.job_id);
    } catch (e: unknown) {
      if (!mountedRef.current) return;
      if (timerRef.current != null) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setRunStatus("failed");
      setErr(e instanceof Error ? e.message : String(e));
      setRunning(false);
      setActiveStep(-1);
    }
  }

  const summary: [string, string][] = [
    ["Species", fmt(request.species)],
    ["Cell type", fmt(request.cell_type)],
    ["Perturbation type", fmt(request.perturbation_type)],
    ["Perturbation targets", fmt(request.perturbation_targets)],
    ["Task type", fmt(request.task_type)],
  ];

  return (
    <section style={{ maxWidth: "880px" }}>
      <div style={{ marginBottom: "var(--space-4)" }}>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "28px",
            fontWeight: 500,
            lineHeight: 1.15,
            letterSpacing: "-0.01em",
            color: "var(--text)",
            margin: 0,
          }}
        >
          Confirm before execution
        </h1>
        <p
          style={{
            marginTop: "var(--space-3)",
            fontSize: "14px",
            lineHeight: 1.55,
            color: "var(--text-muted)",
            maxWidth: "64ch",
          }}
        >
          Review the experiment settings. Predictions require a matching, executable model approved by validation;
          unbound data Pack requests explicitly abstain. Language models do not alter numerical results or decisions.
        </p>
      </div>

      <Card title="Experiment to run">
        <table className="kv-table">
          <tbody>
            {summary.map(([k, v]) => (
              <tr key={k}>
                <th>{k}</th>
                <td>{v}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {expectedModules.length > 0 && (
          <div style={{ marginTop: "var(--space-3)" }}>
            <div
              style={{
                fontSize: "13px",
                color: "var(--text-muted)",
                marginBottom: "var(--space-2)",
                lineHeight: 1.5,
              }}
            >
              Expected modules (actual routing appears in the results):
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
              {expectedModules.map((code) => (
                <span
                  key={code}
                  style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
                >
                  <code
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "12.5px",
                      background: "var(--code-bg)",
                      border: "1px solid var(--border)",
                      borderRadius: "var(--radius-sm)",
                      padding: "2px 6px",
                    }}
                  >
                    {code}
                  </code>
                  <Badge tone="neutral">Expected</Badge>
                </span>
              ))}
            </div>
          </div>
        )}

        <details style={{ marginTop: "var(--space-3)" }}>
          <summary
            style={{
              cursor: "pointer",
              fontSize: "13px",
              color: "var(--text-muted)",
            }}
          >
            View all execution parameters
          </summary>
          <pre className="pretty" style={{ fontFamily: "var(--font-mono)" }}>
            {JSON.stringify(request, null, 2)}
          </pre>
        </details>

        <label
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "var(--space-2)",
            marginTop: "var(--space-3)",
            fontSize: "13.5px",
            lineHeight: 1.5,
            cursor: running ? "default" : "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={enableLlmReport}
            disabled={running}
            onChange={(e) => setEnableLlmReport(e.target.checked)}
            style={{ marginTop: "2px" }}
          />
          <span>
            Generate a language-assisted narrative (optional)
            <span style={{ color: "var(--text-muted)" }}>
              {" "}
              Only rewrites wording for readability; does not affect predictions or reliability decisions.
            </span>
          </span>
        </label>
      </Card>

      {activeStep >= 0 && (
        <Card title="Execution progress">
          <p
            style={{
              margin: "0 0 var(--space-3)",
              fontSize: "12.5px",
              color: "var(--text-muted)",
              lineHeight: 1.5,
            }}
          >
            These standard steps are an illustration, not a live execution stream. View the full execution trace after the run completes.
          </p>
          <ol
            style={{
              listStyle: "none",
              margin: 0,
              padding: 0,
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-2)",
            }}
          >
            {RUN_STEPS.map((label, i) => {
              const done = i < activeStep;
              const current = i === activeStep && running;
              const reached = i <= activeStep;
              return (
                <li
                  key={label}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--space-3)",
                    fontSize: "13.5px",
                    color: reached ? "var(--text)" : "var(--text-muted)",
                    opacity: reached ? 1 : 0.5,
                  }}
                >
                  <span
                    aria-hidden
                    style={{
                      flex: "0 0 auto",
                      width: "18px",
                      height: "18px",
                      borderRadius: "50%",
                      border: `1px solid ${
                        reached ? "var(--accent)" : "var(--border)"
                      }`,
                      background: done
                        ? "var(--accent)"
                        : current
                          ? "color-mix(in srgb, var(--accent) 22%, transparent)"
                          : "transparent",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "11px",
                      color: "var(--on-accent)",
                      lineHeight: 1,
                    }}
                  >
                    {done ? "✓" : ""}
                  </span>
                  <span>
                    {label}
                    {current ? " …" : ""}
                  </span>
                </li>
              );
            })}
          </ol>
        </Card>
      )}

      {err && (
        <div className="err" style={{ marginTop: "var(--space-4)" }}>
          Execution did not complete: {err}
          <div style={{ marginTop: "var(--space-1)", color: "var(--text-muted)" }}>
            Go back to review the settings or try running again.
          </div>
        </div>
      )}

      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          gap: "var(--space-2)",
          marginTop: "var(--space-4)",
        }}
      >
        <Button variant="ghost" onClick={onBack} disabled={running}>
          ← Back
        </Button>
        <Button onClick={run} disabled={running}>
          {running ? "Running…" : "Start run →"}
        </Button>
      </div>
    </section>
  );
}
