import { type Stage } from "../../api";
const STAGES: { key: Stage; label: string; hint: string }[] = [
  { key: "ask", label: "Ask", hint: "Describe the perturbation experiment" },
  { key: "review", label: "Review", hint: "Review and confirm the parsed request" },
  { key: "route", label: "Route", hint: "Review modules and species compatibility" },
  { key: "run", label: "Run", hint: "Confirm parameters and run prediction" },
  { key: "results", label: "Results", hint: "Review the prediction report and provenance" },
];

type NodeState = "done" | "current" | "enabled" | "disabled";

export default function StepperRail({
  stage,
  canEnter,
  onJump,
  locked,
}: {
  stage: Stage;
  canEnter: (s: Stage) => boolean;
  onJump: (s: Stage) => void;
  locked: boolean;
}) {
  const currentIdx = STAGES.findIndex((s) => s.key === stage);

  function nodeState(idx: number): NodeState {
    if (locked && idx !== currentIdx) return "disabled";
    if (idx < currentIdx) return "done";
    if (idx === currentIdx) return "current";
    if (idx === currentIdx + 1 && canEnter(STAGES[idx].key)) return "enabled";
    return "disabled";
  }

  return (
    <nav className="sr-rail" aria-label="Stage progress">
      <ol className="sr-list">
        {STAGES.map((s, idx) => {
          const state = nodeState(idx);
          const clickable = state === "done" || state === "enabled";
          const isLast = idx === STAGES.length - 1;
          return (
            <li key={s.key} className="sr-item">
              <button
                type="button"
                className={`sr-node sr-${state}`}
                disabled={state === "disabled"}
                aria-current={state === "current" ? "step" : undefined}
                title={s.hint}
                onClick={() => {
                  if (clickable) onJump(s.key);
                }}
              >
                <span className="sr-marker" aria-hidden="true">
                  {state === "done" ? "✓" : idx + 1}
                </span>
                <span className="sr-text">
                  <span className="sr-label">{s.label}</span>
                  <span className="sr-hint">{s.hint}</span>
                </span>
              </button>
              {!isLast && (
                <span
                  className={`sr-connector ${idx < currentIdx ? "sr-connector-done" : ""}`}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
