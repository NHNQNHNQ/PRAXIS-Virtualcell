
export type ReliabilityMeterProps = {
  score: number | null;
  mode?: string;
  reliability?: string;
};

function scoreLabel(score: number): string {
  if (score >= 0.7) return "High";
  if (score >= 0.4) return "Medium";
  return "Low";
}

export default function ReliabilityMeter({ score, mode, reliability }: ReliabilityMeterProps) {
  if (score == null || Number.isNaN(score)) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
        <div style={{ fontSize: 13, color: "var(--text-muted)" }}>Result reliability</div>
        <div style={{ fontSize: 14, color: "var(--text-muted)" }}>Not provided</div>
      </div>
    );
  }

  const clamped = Math.max(0, Math.min(1, score));
  const pct = clamped * 100;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "var(--space-3)" }}>
        <span style={{ fontSize: 13, color: "var(--text-muted)" }}>Result reliability</span>
        <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text)" }}>
          {clamped.toFixed(2)}
          <span style={{ marginLeft: "var(--space-2)", fontWeight: 500, color: "var(--text-muted)" }}>
            {scoreLabel(clamped)}
          </span>
        </span>
      </div>

      <svg viewBox="0 0 100 8" preserveAspectRatio="none" style={{ width: "100%", height: 8, display: "block" }} role="img" aria-label={`Reliability ${clamped.toFixed(2)}`}>
        <rect x="0" y="0" width="40" height="8" rx="1.5" fill="var(--danger)" opacity="0.28" />
        <rect x="40" y="0" width="30" height="8" fill="var(--warn)" opacity="0.28" />
        <rect x="70" y="0" width="30" height="8" rx="1.5" fill="var(--accent)" opacity="0.28" />
        <rect
          x={Math.max(0, Math.min(99, pct - 0.6))}
          y="-1"
          width="1.2"
          height="10"
          fill={clamped >= 0.7 ? "var(--accent)" : clamped >= 0.4 ? "var(--warn)" : "var(--danger)"}
        />
      </svg>

      {(mode != null && mode !== "") || (reliability != null && reliability !== "") ? (
        <div style={{ display: "flex", gap: "var(--space-4)", fontSize: 12, color: "var(--text-muted)" }}>
          {mode != null && mode !== "" && <span>Execution mode: {mode}</span>}
          {reliability != null && reliability !== "" && <span>Reliability decision: {reliability}</span>}
        </div>
      ) : null}
    </div>
  );
}
